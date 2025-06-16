import streamlit as st
import os
import yaml
import json
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import datetime

# Configure Streamlit page
st.set_page_config(page_title="Infrared Annotation Tool", layout="wide")

# Custom CSS
st.markdown("""
    <style>
        .main > div { padding: 0rem !important; }
        .stButton>button { width: 100%; }
        h1 { padding-top: 1rem !important; margin-top: 1rem !important; margin-bottom: 1rem !important; }
        .canvas-container { background-color: transparent !important; }
        .canvas-container canvas { background-color: transparent !important; }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("📸 Infrared Object Detection - Manual Annotation Tool")

# Directory paths
false_neg_labels_dir = 'annotations/false_negatives/'
corrected_ann_dir = 'annotations/corrected_yaml/'
metadata_file = 'annotations/potential_false_negatives.yaml'
json_tracking_file = 'annotations/box_changes.json'

os.makedirs(false_neg_labels_dir, exist_ok=True)
os.makedirs(corrected_ann_dir, exist_ok=True)
os.makedirs(os.path.dirname(json_tracking_file), exist_ok=True)

def create_box(x1, y1, x2, y2, box_id, is_original=True):
    return {
        'type': 'rect',
        'left': x1,
        'top': y1,
        'width': x2 - x1,
        'height': y2 - y1,
        'stroke': '#00FF00',
        'fill': 'rgba(0, 255, 0, 0)',
        'strokeWidth': 2,
        'box_id': box_id,
        'is_original': is_original
    }

def create_text_label(x, y, text):
    return {
        'type': 'text',
        'left': x,
        'top': y,
        'text': text,
        'fontSize': 12,
        'fontFamily': 'Arial',
        'fill': '#00FF00',
        'box_id': text,
        'editable': False,
        'lockScalingX': True,
        'lockScalingY': True,
        'hasControls': False,
        'selectable': False
    }

def save_to_json(image_path, objects, labels):
    try:
        if os.path.exists(json_tracking_file):
            with open(json_tracking_file, 'r') as f:
                tracking_data = json.load(f)
        else:
            tracking_data = {}
        image_entry = {
            'image_path': image_path,
            'boxes': [],
            'timestamp': str(datetime.datetime.now())
        }
        for i, obj in enumerate(objects):
            if obj["type"] == "rect":
                box_data = {
                    'box_id': obj.get('box_id', f'Box {i+1}'),
                    'coordinates': {
                        'left': obj['left'],
                        'top': obj['top'],
                        'width': obj['width'],
                        'height': obj['height']
                    },
                    'label': labels[i] if i < len(labels) else 'Unknown',
                    'is_original': obj.get('is_original', False)
                }
                image_entry['boxes'].append(box_data)
        tracking_data[image_path] = image_entry
        with open(json_tracking_file, 'w') as f:
            json.dump(tracking_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving to JSON: {str(e)}")
        return False

# Load metadata YAML
if not os.path.exists(metadata_file):
    st.error("No potential_false_negatives.yaml found.")
    st.stop()

with open(metadata_file, 'r') as f:
    annotations_data = yaml.safe_load(f)

# Filter out images that don't exist and store full paths
image_files = []
for item in annotations_data:
    img_path = item['image_path']
    if os.path.exists(img_path):
        image_files.append(img_path)
    else:
        st.warning(f"Image not found: {img_path}")

if len(image_files) == 0:
    st.error("No valid images found for annotation. Please check the image directory.")
    st.stop()

# Layout: sidebar for thumbnails, main canvas, label controls
col1, col2, col3 = st.columns([1, 3, 1])

# Column 1: Image thumbnails
with col1:
    st.subheader("Images")
    if 'current_idx' not in st.session_state:
        st.session_state.current_idx = 0
    for i, img_path in enumerate(image_files):
        try:
            img = Image.open(img_path)
            scale = min(1.0, 100 / img.size[0])
            thumb = img.resize((int(img.size[0] * scale), int(img.size[1] * scale)))
            st.image(thumb, use_column_width=True)
            if st.button(f"Select Image {i+1}", key=f"btn_{i}"):
                st.session_state.current_idx = i
                st.rerun()
        except Exception as e:
            st.error(f"Error loading image {img_path}: {str(e)}")

# Column 2: Annotation canvas
with col2:
    selected_image_path = image_files[st.session_state.current_idx]
    selected_image_name = os.path.basename(selected_image_path)
    try:
        image = Image.open(selected_image_path)
        img_width, img_height = image.size
        st.session_state.img_width = img_width
        st.session_state.img_height = img_height
        canvas_objects = []
        label_path = os.path.join(false_neg_labels_dir, selected_image_name.replace('.jpg', '.txt'))
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                for i, line in enumerate(f.readlines()):
                    parts = line.strip().split()
                    if len(parts) == 5:
                        cls, x_center, y_center, w, h = map(float, parts)
                        x1 = (x_center - w / 2) * img_width
                        y1 = (y_center - h / 2) * img_height
                        x2 = (x_center + w / 2) * img_width
                        y2 = (y_center + h / 2) * img_height
                        box_id = f"Box {i+1}"
                        canvas_objects.append(create_box(x1, y1, x2, y2, box_id, is_original=True))
                        canvas_objects.append(create_text_label(x1 + 4, max(2, y1 - 14), box_id))
        if 'canvas_objects' not in st.session_state or st.session_state.get('current_image_idx', -1) != st.session_state.current_idx:
            st.session_state['canvas_objects'] = canvas_objects
            st.session_state['current_image_idx'] = st.session_state.current_idx
        if 'canvas_key' not in st.session_state:
            st.session_state['canvas_key'] = 0
        drawing_mode = st.radio(
            "Drawing Mode:",
            ["Transform", "Draw New Box"],
            horizontal=True,
            key="drawing_mode"
        )
        canvas_result = st_canvas(
            fill_color="rgba(0, 255, 0, 0)",
            stroke_width=2,
            stroke_color="#00ff00",
            background_image=image,
            height=img_height,
            width=img_width,
            drawing_mode="rect" if drawing_mode == "Draw New Box" else "transform",
            initial_drawing={"objects": st.session_state['canvas_objects']},
            key=f"canvas_{st.session_state['canvas_key']}"
        )
        st.session_state.canvas_result = canvas_result
    except Exception as e:
        st.error(f"Error loading image {selected_image_path}: {str(e)}")
        st.stop()

# Column 3: Label controls + Save
with col3:
    st.subheader("Labels")
    label_options = ['Person', 'Car']
    selected_box_id = None
    if (
        st.session_state.canvas_result is not None and
        hasattr(st.session_state.canvas_result, 'json_data') and
        st.session_state.canvas_result.json_data is not None
    ):
        selected_idx = st.session_state.canvas_result.json_data.get("selectedObjectIndex", None)
        objects = st.session_state.canvas_result.json_data.get("objects", [])
        if (
            selected_idx is not None
            and selected_idx >= 0
            and len(objects) > selected_idx
            and objects[selected_idx]["type"] == "rect"
        ):
            selected_box_id = objects[selected_idx].get("box_id")
        updated_objects = []
        labels_per_box = []
        box_counter = 1
        for i, obj in enumerate(objects):
            if obj["type"] == "rect":
                if "box_id" not in obj:
                    obj["box_id"] = f"Box {box_counter}"
                    box_counter += 1
                box_id = obj["box_id"]
                st.markdown(f"**🟩 {box_id}**")
                selected_label = st.selectbox(
                    f"Label for {box_id}",
                    label_options,
                    key=f"label_{i}"
                )
                labels_per_box.append(selected_label)
                updated_objects.append(obj)
        st.session_state.canvas_result.json_data["objects"] = updated_objects
        if len(updated_objects) > 0:
            save_to_json(selected_image_path, updated_objects, labels_per_box)
        if len(updated_objects) > 0 and st.button("💾 Save Annotations"):
            try:
                new_annotations = []
                yolo_lines = []
                for i, obj in enumerate(updated_objects):
                    if obj["type"] == "rect":
                        left, top = obj["left"], obj["top"]
                        width, height = obj["width"], obj["height"]
                        x_center = (left + width / 2) / st.session_state.img_width
                        y_center = (top + height / 2) / st.session_state.img_height
                        w_norm = width / st.session_state.img_width
                        h_norm = height / st.session_state.img_height
                        class_id = label_options.index(st.session_state.get(f"label_{i}", "Person"))
                        yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}\n")
                        new_annotations.append({
                            'label': st.session_state.get(f"label_{i}", "Person"),
                            'bbox': [x_center, y_center, w_norm, h_norm]
                        })
                with open(label_path, 'w') as f:
                    f.writelines(yolo_lines)
                corrected_file = os.path.join(corrected_ann_dir, selected_image_name.replace('.jpg', '.yaml'))
                yaml_data = {
                    'image': selected_image_path,
                    'annotations': new_annotations
                }
                with open(corrected_file, 'w') as f:
                    yaml.dump(yaml_data, f)
                save_to_json(selected_image_path, updated_objects, labels_per_box)
                st.success("✅ Annotations saved successfully!")
            except Exception as e:
                st.error(f"Error saving annotations: {str(e)}")

    # Add delete button in column 3
    st.markdown(f"<div style='text-align:center; margin-top: 10px;'><b>Delete a box:</b></div>", unsafe_allow_html=True)
    if st.button("🗑️ Delete Selected Box", key="delete_selected_box_col3", help="Delete the selected bounding box"):
        if (
            st.session_state.get('drawing_mode', 'Transform') == "Transform"
            and selected_box_id is not None
        ):
            # Remove from canvas (both rect and text label)
            if delete_box_from_canvas(st.session_state.canvas_result, selected_box_id):
                delete_box_from_json(selected_image_path, selected_box_id)
                st.rerun()
        else:
            st.warning("Please select a box in Transform mode to delete.")

def delete_box_from_canvas(canvas_result, box_id):
    try:
        if canvas_result is not None and hasattr(canvas_result, 'json_data') and canvas_result.json_data is not None:
            objects = canvas_result.json_data.get("objects", [])
            new_objects = [
                o for o in objects
                if o.get("box_id") != box_id
            ]
            canvas_result.json_data["objects"] = new_objects
            st.success(f"Successfully deleted box {box_id} from canvas")
            return True
    except Exception as e:
        st.error(f"Error deleting box from canvas: {str(e)}")
    return False
