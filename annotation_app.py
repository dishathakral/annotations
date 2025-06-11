import streamlit as st
import os
import yaml
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import cv2
import numpy as np

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
image_dir = 'datasets/test_subset/'

# Ensure directories exist
os.makedirs(false_neg_labels_dir, exist_ok=True)
os.makedirs(corrected_ann_dir, exist_ok=True)

def create_box(x1, y1, x2, y2, box_id, is_original=True):
    """Create a transparent box with green outline and ID"""
    return {
        'type': 'rect',
        'left': x1,
        'top': y1,
        'width': x2 - x1,
        'height': y2 - y1,
        'stroke': '#00FF00',  # Explicit stroke property for outline
        'fill': 'rgba(0, 255, 0, 0)',  # Explicit fill property for transparent fill
        'strokeWidth': 2,
        'box_id': box_id,
        'is_original': is_original
    }

# Load metadata YAML
if not os.path.exists(metadata_file):
    st.error("No potential_false_negatives.yaml found.")
    st.stop()

with open(metadata_file, 'r') as f:
    annotations_data = yaml.safe_load(f)

image_files = [os.path.basename(item['image_path']) for item in annotations_data]

if len(image_files) == 0:
    st.info("No images found for annotation.")
    st.stop()

# Layout: sidebar for thumbnails, main canvas, label controls
col1, col2, col3 = st.columns([1, 3, 1])

# Column 1: Image thumbnails
with col1:
    st.subheader("Images")
    if 'current_idx' not in st.session_state:
        st.session_state.current_idx = 0

    for i, img_file in enumerate(image_files):
        img_path = os.path.join(image_dir, img_file)
        if os.path.exists(img_path):
            img = Image.open(img_path)
            scale = min(1.0, 100 / img.size[0])
            thumb = img.resize((int(img.size[0] * scale), int(img.size[1] * scale)))
            st.image(thumb, use_column_width=True)
            if st.button(f"Select Image {i+1}", key=f"btn_{i}"):
                st.session_state.current_idx = i
                st.experimental_rerun()

# Column 2: Annotation canvas
with col2:
    selected_image = image_files[st.session_state.current_idx]
    selected_image_path = os.path.join(image_dir, selected_image)

    # Load and prepare image
    image = Image.open(selected_image_path)
    img_width, img_height = image.size
    st.session_state.img_width = img_width
    st.session_state.img_height = img_height

    # Load existing annotations
    existing_boxes = []
    box_labels = []
    label_path = os.path.join(false_neg_labels_dir, selected_image.replace('.jpg', '.txt'))
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
                    existing_boxes.append(create_box(x1, y1, x2, y2, f"Box {i+1}", is_original=True))
                    box_labels.append('Person' if int(cls) == 0 else 'Car')

    # Drawing mode selector
    drawing_mode = st.radio(
        "Drawing Mode:",
        ["Transform", "Draw New Box"],
        horizontal=True,
        key="drawing_mode"
    )

    # Canvas
    canvas_result = st_canvas(
        fill_color="rgba(0, 255, 0, 0)",  # Completely transparent
        stroke_width=2,
        stroke_color="#00ff00",  # Green outline
        background_image=image,
        height=img_height,
        width=img_width,
        drawing_mode="rect" if drawing_mode == "Draw New Box" else "transform",
        initial_drawing={"objects": existing_boxes},
        key="canvas",
    )

    st.session_state.canvas_result = canvas_result

# Column 3: Label controls + Save
with col3:
    st.subheader("Labels")
    label_options = ['Person', 'Car']

    labels_per_box = []
    if 'canvas_result' in st.session_state and st.session_state.canvas_result.json_data is not None:
        objects = st.session_state.canvas_result.json_data.get("objects", [])
        for i, obj in enumerate(objects):
            if obj["type"] == "rect":
                box_id = obj.get("box_id", f"Box {i+1}")
                st.write(f"**{box_id}**")
                
                # Create columns for label and delete button
                label_col, delete_col = st.columns([3, 1])
                
                with label_col:
                    selected_label = st.selectbox(
                        f"Label for {box_id}",
                        label_options,
                        key=f"label_{i}"
                    )
                    labels_per_box.append(selected_label)
                
                # Show delete button only for non-original boxes
                if not obj.get("is_original", False):
                    with delete_col:
                        if st.button("🗑️", key=f"delete_{i}"):
                            # Remove the box from the canvas
                            objects.pop(i)
                            st.experimental_rerun()

        if len(objects) > 0 and st.button("💾 Save Annotations"):
            new_annotations = []
            yolo_lines = []

            for i, obj in enumerate(objects):
                if obj["type"] == "rect":
                    left, top = obj["left"], obj["top"]
                    width, height = obj["width"], obj["height"]

                    x_center = (left + width / 2) / st.session_state.img_width
                    y_center = (top + height / 2) / st.session_state.img_height
                    w_norm = width / st.session_state.img_width
                    h_norm = height / st.session_state.img_height

                    class_id = label_options.index(st.session_state[f"label_{i}"])
                    yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}\n")

                    new_annotations.append({
                        'label': st.session_state[f"label_{i}"],
                        'bbox': [x_center, y_center, w_norm, h_norm]
                    })

            # Save to YOLO txt
            with open(label_path, 'w') as f:
                f.writelines(yolo_lines)

            # Save to YAML
            corrected_file = os.path.join(corrected_ann_dir, selected_image.replace('.jpg', '.yaml'))
            with open(corrected_file, 'w') as f:
                yaml.dump(new_annotations, f)

            st.success("✅ Annotations saved successfully!")

