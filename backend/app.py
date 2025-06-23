from flask import Flask, request, jsonify, send_from_directory
import os
import zipfile
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, 'projects')
os.makedirs(PROJECTS_DIR, exist_ok=True)

@app.route('/api/projects', methods=['GET'])
def list_projects():
    projects = os.listdir(PROJECTS_DIR)
    return jsonify(projects)

@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.json
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

if __name__ == '__main__':
    app.run(debug=True)
