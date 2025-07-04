from flask import Flask, request, jsonify, send_from_directory, stream_with_context, Response
import os
import zipfile
from flask_cors import CORS
import random
import json
import yaml
import time

try:
    from ultralytics import YOLO
    import cv2
except ImportError:
    YOLO = None
    cv2 = None

app = Flask(__name__)
CORS(app)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, 'projects')
os.makedirs(PROJECTS_DIR, exist_ok=True)

# In-memory store for auto-annotate requests
AUTO_ANNOTATE_REQUESTS = {}

MODELS_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'models'))
CONFIG_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'config'))
MODELS_YAML = os.path.join(CONFIG_DIR, 'models.yaml')
LABELS_FILE = os.path.join(CONFIG_DIR, 'labels.txt')


# Serve the main frontend page
from flask import render_template

@app.route('/')
def home():
    return render_template('index.html')
@app.route('/api/projects/<project_name>/delete_subset', methods=['POST'])
def delete_subset(project_name):
    """Delete a subset folder and its JSON for a project."""
    data = request.get_json() or {}
    subset_name = data.get('subset_name')
    if not subset_name:
        return jsonify({'error': 'No subset_name provided'}), 400
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    subset_dir = os.path.join(project_dir, subset_name)
    if not os.path.exists(subset_dir):
        return jsonify({'error': 'Subset not found'}), 404
    try:
        # Remove all files in the subset directory, then the directory itself
        for root, dirs, files in os.walk(subset_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(subset_dir)
        return jsonify({'message': f'Subset {subset_name} deleted.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['GET'])
def list_projects():
    projects = os.listdir(PROJECTS_DIR)
    return jsonify(projects)

@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.get_json() or {}
    project_name = data.get('project_name')
    if not project_name:
        return jsonify({'error': 'No project name provided'}), 400
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    images_dir = os.path.join(project_dir, 'images')
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
        return jsonify({'message': f"Project '{project_name}' created!"})
    else:
        return jsonify({'error': f"Project '{project_name}' already exists."}), 400

@app.route('/api/projects/<project_name>/upload', methods=['POST'])
def upload_zip(project_name):
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    images_dir = os.path.join(project_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    SUPPORTED_EXTS = (".jpg", ".jpeg", ".png", ".bmp")
    with zipfile.ZipFile(file.stream) as z:
        valid_files = [f for f in z.namelist() if f.lower().endswith(SUPPORTED_EXTS)]
        for f in valid_files:
            filename = os.path.basename(f)
            if filename:
                with z.open(f) as source, open(os.path.join(images_dir, filename), "wb") as target:
                    target.write(source.read())
    return jsonify({'message': f"Uploaded {len(valid_files)} image(s)!"})

@app.route('/projects/<project_name>/images/<filename>')
def serve_image(project_name, filename):
    images_dir = os.path.join(PROJECTS_DIR, project_name, 'images')
    return send_from_directory(images_dir, filename)

@app.route('/projects/<project_name>/images/', methods=['GET'])
def list_images(project_name):
    images_dir = os.path.join(PROJECTS_DIR, project_name, 'images')
    if not os.path.exists(images_dir):
        return jsonify([])
    files = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]
    return jsonify(files)

@app.route('/api/projects/<project_name>/save_annotations', methods=['POST'])
def save_annotations(project_name):
    data = request.get_json()
    if not data or 'images' not in data:
        return jsonify({'error': 'Invalid annotation data'}), 400
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.exists(project_dir):
        return jsonify({'error': 'Project does not exist'}), 404
    out_path = os.path.join(project_dir, 'manual_annotations.json')
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return jsonify({'message': 'Annotations saved successfully!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_name>/save_annotation', methods=['POST'])
def save_single_annotation(project_name):
    data = request.get_json()
    if not data or 'file_name' not in data or 'width' not in data or 'height' not in data or 'annotations' not in data:
        return jsonify({'error': 'Invalid annotation data'}), 400
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.exists(project_dir):
        return jsonify({'error': 'Project does not exist'}), 404
    out_path = os.path.join(project_dir, 'manual_annotations.json')
    # Load existing annotations.json or create new structure
    if os.path.exists(out_path):
        with open(out_path, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
    else:
        all_data = {"images": {}, "categories": []}
    # Update or add the image annotation
    all_data["images"][data['file_name']] = {
        "width": data['width'],
        "height": data['height'],
        "annotations": data['annotations']
    }
    # Update categories if new labels are present
    for ann in data['annotations']:
        label = ann.get('label') or ann.get('category')
        if label and label not in all_data['categories']:
            all_data['categories'].append(label)
    # Save back
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2)
    return jsonify({'message': f"Annotation for {data['file_name']} saved!"})

@app.route('/api/projects/<project_name>/images', methods=['GET'])
def get_project_images(project_name):
    images_dir = os.path.join(PROJECTS_DIR, project_name, 'images')
    if not os.path.exists(images_dir):
        return jsonify([])
    files = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]
    return jsonify(files)

# API: Get images in project
@app.route('/api/projects/<project_name>/images', methods=['GET'])
def get_images(project_name):
    images_dir = os.path.join(PROJECTS_DIR, project_name, 'images')
    if not os.path.exists(images_dir):
        return jsonify([])

    files = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]
    return jsonify(files)

@app.route('/api/projects/<project_name>/auto_annotate_request', methods=['POST'])
def save_auto_annotate_request(project_name):
    data = request.get_json() or {}
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.exists(project_dir):
        return jsonify({'error': 'Project does not exist'}), 404
    images_dir = os.path.join(project_dir, 'images')
    if not os.path.exists(images_dir):
        return jsonify({'error': 'Images directory does not exist'}), 404
    all_images = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]
    if not all_images:
        return jsonify({'error': 'No images found'}), 404
    # Find next available subset_N folder
    n = 1
    while os.path.exists(os.path.join(project_dir, f'subset_{n}')):
        n += 1
    subset_dir = os.path.join(project_dir, f'subset_{n}')
    os.makedirs(subset_dir, exist_ok=True)
    subset_json_path = os.path.join(subset_dir, f'subset_{n}.json')
    try:
        with open(subset_json_path, 'w', encoding='utf-8') as f:
            json.dump({'images': all_images}, f, indent=2)
        return jsonify({'message': f'Complete dataset subset created as subset_{n}/{f"subset_{n}.json"} with {len(all_images)} images.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_name>/create_manual_subset', methods=['POST'])
def create_manual_subset(project_name):
    data = request.get_json() or {}
    images = data.get('images', [])
    if not images:
        return jsonify({'error': 'No images provided'}), 400
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.exists(project_dir):
        return jsonify({'error': 'Project does not exist'}), 404
    # Find next available subset_N folder
    n = 1
    while os.path.exists(os.path.join(project_dir, f'subset_{n}')):
        n += 1
    subset_dir = os.path.join(project_dir, f'subset_{n}')
    os.makedirs(subset_dir, exist_ok=True)
    subset_json_path = os.path.join(subset_dir, f'subset_{n}.json')
    try:
        with open(subset_json_path, 'w', encoding='utf-8') as f:
            json.dump({'images': images}, f, indent=2)
        return jsonify({'message': f'Manual subset created as subset_{n}/{f"subset_{n}.json"} with {len(images)} images.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_name>/create_random_subset', methods=['POST'])
def create_random_subset(project_name):
    data = request.get_json() or {}
    percent = data.get('percent')
    if percent is None:
        return jsonify({'error': 'No percent provided'}), 400
    try:
        percent = float(percent)
        if percent <= 0 or percent > 100:
            raise ValueError
    except Exception:
        return jsonify({'error': 'Invalid percent value'}), 400
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    images_dir = os.path.join(project_dir, 'images')
    if not os.path.exists(images_dir):
        return jsonify({'error': 'Images directory does not exist'}), 404
    all_images = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]
    if not all_images:
        return jsonify({'error': 'No images found'}), 404
    k = max(1, int(len(all_images) * percent / 100.0))
    selected = random.sample(all_images, k)
    # Find next available subset_N folder
    n = 1
    while os.path.exists(os.path.join(project_dir, f'subset_{n}')):
        n += 1
    subset_dir = os.path.join(project_dir, f'subset_{n}')
    os.makedirs(subset_dir, exist_ok=True)
    subset_json_path = os.path.join(subset_dir, f'subset_{n}.json')
    try:
        with open(subset_json_path, 'w', encoding='utf-8') as f:
            json.dump({'images': selected}, f, indent=2)
        return jsonify({'message': f'Random subset created as subset_{n}/{f"subset_{n}.json"} with {len(selected)} images.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/models/list', methods=['GET'])
def list_models():
    result = {}
    allowed_exts = ('.pt', '.pth', '.onnx', '.ckpt', '.bin', '.h5', '.tflite')
    if not os.path.exists(MODELS_DIR):
        print(f"MODELS_DIR does not exist: {MODELS_DIR}")
        return jsonify(result)
    for family in os.listdir(MODELS_DIR):
        fam_path = os.path.join(MODELS_DIR, family)
        if os.path.isdir(fam_path):
            versions = [f for f in os.listdir(fam_path)
                        if os.path.isfile(os.path.join(fam_path, f)) and f.lower().endswith(allowed_exts)]
            if versions:
                result[family] = versions
    print(f"/api/models/list result: {result}")  # Debug print
    return jsonify(result)

@app.route('/api/models/families', methods=['GET'])
def get_model_families():
    if not os.path.exists(MODELS_DIR):
        return jsonify([])
    families = [f for f in os.listdir(MODELS_DIR) if os.path.isdir(os.path.join(MODELS_DIR, f))]
    return jsonify(families)

@app.route('/api/models/versions', methods=['GET'])
def get_model_versions():
    family = request.args.get('family')
    if not family:
        return jsonify([])
    fam_path = os.path.join(MODELS_DIR, family)
    allowed_exts = ('.pt', '.pth', '.onnx', '.ckpt', '.bin', '.h5', '.tflite')
    if not os.path.isdir(fam_path):
        return jsonify([])
    versions = [f for f in os.listdir(fam_path) if os.path.isfile(os.path.join(fam_path, f)) and f.lower().endswith(allowed_exts)]
    return jsonify(versions)

@app.route('/api/models/descriptions', methods=['GET'])
def get_model_descriptions():
    if not os.path.exists(MODELS_YAML):
        return jsonify({})
    with open(MODELS_YAML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return jsonify(data.get('models', {}))

@app.route('/api/labels', methods=['GET', 'POST'])
def manage_labels():
    project_name = request.args.get('project')
    if not project_name:
        return jsonify({'error': 'Project name required'}), 400
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.exists(project_dir):
        return jsonify({'error': 'Project does not exist'}), 404
    labels_file = os.path.join(project_dir, 'labels.txt')
    if request.method == 'POST':
        data = request.get_json() or {}
        label = data.get('label', '').strip()
        if not label:
            return jsonify({'error': 'No label provided'}), 400
        # Append label to file if not already present
        labels = []
        if os.path.exists(labels_file):
            with open(labels_file, 'r', encoding='utf-8') as f:
                labels = [l.strip() for l in f if l.strip()]
        if label in labels:
            return jsonify({'error': 'Label already exists'}), 400
        with open(labels_file, 'a', encoding='utf-8') as f:
            f.write(label + '\n')
        return jsonify({'message': f'Label "{label}" added.'})
    else:
        labels = []
        if os.path.exists(labels_file):
            with open(labels_file, 'r', encoding='utf-8') as f:
                labels = [l.strip() for l in f if l.strip()]
        return jsonify({'labels': labels})

@app.route('/api/projects/<project_name>/subsets', methods=['GET'])
def list_subsets(project_name):
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.exists(project_dir):
        return jsonify([])
    subsets = []
    for name in os.listdir(project_dir):
        if name.startswith('subset_') and os.path.isdir(os.path.join(project_dir, name)):
            subset_json = os.path.join(project_dir, name, f'{name}.json')
            if os.path.exists(subset_json):
                subsets.append({'name': name, 'json': f'{name}/{name}.json'})
    return jsonify(subsets)

@app.route('/projects/<project_name>/<subset_folder>/<subset_json>')
def serve_subset_json(project_name, subset_folder, subset_json):
    subset_dir = os.path.join(PROJECTS_DIR, project_name, subset_folder)
    if not os.path.exists(subset_dir):
        return jsonify({'error': 'Subset not found'}), 404
    return send_from_directory(subset_dir, subset_json)

@app.route('/api/projects/<project_name>/save_auto_annotate_config', methods=['POST'])
def save_auto_annotate_config(project_name):
    data = request.get_json() or {}
    model_family = data.get('model_family')
    model_version = data.get('model_version')
    subset = data.get('subset')
    if not (model_family and model_version and subset):
        return jsonify({'error': 'model_family, model_version, and subset are required'}), 400
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    if not os.path.exists(project_dir):
        return jsonify({'error': 'Project does not exist'}), 404
    config_path = os.path.join(project_dir, 'auto_annotate_config.json')
    config = {
        'model_family': model_family,
        'model_version': model_version,
        'subset': subset
    }
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return jsonify({'message': 'Auto-annotate config saved successfully!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_name>/get_auto_annotate_config', methods=['GET'])
def get_auto_annotate_config(project_name):
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    config_path = os.path.join(project_dir, 'auto_annotate_config.json')
    if not os.path.exists(config_path):
        return jsonify({'error': 'Config not found'}), 404
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return jsonify(config)

@app.route('/api/projects/<project_name>/run_auto_label', methods=['POST'])
def run_auto_label(project_name):
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    config_path = os.path.join(project_dir, 'auto_annotate_config.json')
    if not os.path.exists(config_path):
        return jsonify({'error': 'Auto-annotate config not found'}), 404
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    model_family = config.get('model_family')
    model_version = config.get('model_version')
    subset = config.get('subset')
    if not (model_family and model_version and subset):
        return jsonify({'error': 'Incomplete config'}), 400
    # Model path
    model_path = os.path.join(MODELS_DIR, model_family, model_version)
    if not os.path.exists(model_path):
        return jsonify({'error': f'Model file not found: {model_path}'}), 404
    # Subset path
    subset_path = os.path.join(project_dir, subset)
    if not os.path.exists(subset_path):
        return jsonify({'error': f'Subset file not found: {subset_path}'}), 404
    with open(subset_path, 'r', encoding='utf-8') as f:
        subset_data = json.load(f)
    images = subset_data.get('images', [])
    images_dir = os.path.join(project_dir, 'images')
    results = {}
    if YOLO is None:
        return jsonify({'error': 'ultralytics not installed on server'}), 500
    try:
        model = YOLO(model_path)
        for img_name in images:
            img_path = os.path.join(images_dir, img_name)
            if not os.path.exists(img_path):
                continue
            pred = model(img_path)
            # Convert prediction to serializable format (e.g., boxes, scores, classes)
            pred_data = []
            for r in pred:
                boxes = r.boxes.xyxy.cpu().numpy().tolist() if hasattr(r, 'boxes') and hasattr(r.boxes, 'xyxy') else []
                scores = r.boxes.conf.cpu().numpy().tolist() if hasattr(r, 'boxes') and hasattr(r.boxes, 'conf') else []
                classes = r.boxes.cls.cpu().numpy().tolist() if hasattr(r, 'boxes') and hasattr(r.boxes, 'cls') else []
                pred_data.append({'boxes': boxes, 'scores': scores, 'classes': classes})
            results[img_name] = pred_data
        # Save results
        out_path = os.path.join(project_dir, 'auto_annotate_results.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        return jsonify({'message': f'Auto-labeling complete! Results saved to auto_annotate_results.json', 'num_images': len(results)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/projects/<project_name>/auto_annotate_results.json')
def serve_auto_annotate_results(project_name):
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    results_path = os.path.join(project_dir, 'auto_annotate_results.json')
    if not os.path.exists(results_path):
        return jsonify({'error': 'Results file not found'}), 404
    return send_from_directory(project_dir, 'auto_annotate_results.json')

@app.route('/project.html')
def serve_project_html():
    return render_template('project.html')

@app.route('/auto_annotate_dataset.html')
def serve_auto_annotate_dataset_html():
    return render_template('auto_annotate_dataset.html')

@app.route('/manual_annotate.html')
def serve_manual_annotate_html():
    return render_template('manual_annotate.html')

@app.route('/view_predictions.html')
def serve_view_predictions_html():
    return render_template('view_predictions.html')

@app.route('/projects')
def serve_projects_html():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0')
