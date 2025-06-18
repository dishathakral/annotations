import streamlit as st
import os
import json
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import datetime
import yaml
import random
from functools import lru_cache

# Cache resized images to avoid recomputation on every rerun
@st.cache_data(show_spinner=False)
def get_resized_image(image_path, max_w=640, max_h=480):
    image = Image.open(image_path)
    scale = min(max_w / image.width, max_h / image.height, 1.0)
    img_width, img_height = int(image.width * scale), int(image.height * scale)
    image = image.resize((img_width, img_height))
    return image, img_width, img_height

st.set_page_config(page_title="Manual Annotation", layout="wide")

st.title("📝 Manual Annotation Page")

# Get project name from session_state
project_name = st.session_state.get('project_name', None)
if not project_name:
    st.error("No project selected. Please return to the New Project page and select a project.")
    st.stop()

images_dir = os.path.join("projects", project_name, "images")
if not os.path.exists(images_dir):
    st.error(f"No images found in projects/{project_name}/images. Please upload images first.")
    st.stop()

SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.bmp')
image_files = [os.path.join(images_dir, f) for f in os.listdir(images_dir) if f.lower().endswith(SUPPORTED_EXTS)]

if len(image_files) == 0:
    st.error("No valid images found for annotation in this project.")
    st.stop()

# --- LABELS ---
label_colors = ["#FF0000", "#00FF00", "#0000FF", "#FFA500", "#800080", "#00FFFF", "#FFC0CB", "#A52A2A"]
if 'label_options' not in st.session_state:
    st.session_state['label_options'] = ["Animal", "Human", "Vehicle"]
if 'label_color_map' not in st.session_state:
    st.session_state['label_color_map'] = {label: label_colors[i % len(label_colors)] for i, label in enumerate(st.session_state['label_options'])}
if 'selected_label' not in st.session_state:
    st.session_state['selected_label'] = st.session_state['label_options'][0]
label_options = st.session_state['label_options']

# --- PAGINATION FOR IMAGES ---
IMAGES_PER_PAGE = 8
if 'img_page' not in st.session_state:
    st.session_state['img_page'] = 0
num_pages = (len(image_files) - 1) // IMAGES_PER_PAGE + 1

# --- LAYOUT ---
# Increase width of column 1, add padding column, reduce size of columns 3 and 4
col1, pad, col2, col3, col4 = st.columns([2, 0.2, 3, 1, 1])

# --- COLUMN 1: PAGINATED IMAGES WITH THUMBNAILS ---
with col1:
    st.subheader("Images")
    # Pagination controls
    prev, next = st.columns(2)
    with prev:
        if st.button("⬅️ Prev", key="prev_page"):
            st.session_state['img_page'] = max(0, st.session_state['img_page'] - 1)
    with next:
        if st.button("Next ➡️", key="next_page"):
            st.session_state['img_page'] = min(num_pages - 1, st.session_state['img_page'] + 1)
    start_idx = st.session_state['img_page'] * IMAGES_PER_PAGE
    end_idx = min(start_idx + IMAGES_PER_PAGE, len(image_files))
    img_cols = st.columns(2)
    for idx, i in enumerate(range(start_idx, end_idx)):
        img_path = image_files[i]
        try:
            img = Image.open(img_path)
            scale = min(1.0, 180 / max(img.size))  # Increased thumbnail size
            thumb = img.resize((int(img.size[0] * scale), int(img.size[1] * scale)))
            with img_cols[idx % 2]:
                st.image(thumb, width=180)  # Increased width
                if st.button("Select", key=f"btn_{i}"):
                    st.session_state.current_idx = i
                    st.experimental_rerun()
        except Exception as e:
            st.error(f"Error loading image {img_path}: {str(e)}")
    st.markdown(f"Page {st.session_state['img_page']+1} of {num_pages}")

# --- COLUMN 2: ANNOTATION CANVAS + SAVE BUTTON ---
with col2:
    if 'current_idx' not in st.session_state:
        st.session_state.current_idx = 0
    selected_image_path = image_files[st.session_state.current_idx]
    selected_image_name = os.path.basename(selected_image_path)
    try:
        # Use cached resized image
        image, img_width, img_height = get_resized_image(selected_image_path)
        st.session_state.img_width = img_width
        st.session_state.img_height = img_height

        # --- PERSIST CANVAS STATE ---
        canvas_key = f"canvas_{selected_image_name}"
        if 'canvas_states' not in st.session_state:
            st.session_state['canvas_states'] = {}
        if canvas_key not in st.session_state['canvas_states']:
            st.session_state['canvas_states'][canvas_key] = {"objects": []}

        drawing_mode = st.radio(
            "Drawing Mode:",
            ["Transform", "Draw New Box"],
            horizontal=True,
            key="drawing_mode"
        )
        canvas_result = st_canvas(
            fill_color="rgba(0, 255, 0, 0)",
            stroke_width=2,
            stroke_color=st.session_state['label_color_map'][st.session_state['selected_label']],
            background_image=image,
            height=img_height,
            width=img_width,
            drawing_mode="rect" if drawing_mode == "Draw New Box" else "transform",
            initial_drawing=st.session_state['canvas_states'][canvas_key],
            key=canvas_key
        )
        # Save the current canvas state after drawing
        if canvas_result.json_data and 'objects' in canvas_result.json_data:
            for idx, obj in enumerate(canvas_result.json_data['objects']):
                if obj['type'] == 'rect' and 'box_id' not in obj:
                    obj['box_id'] = idx
            st.session_state['canvas_states'][canvas_key] = canvas_result.json_data
        st.session_state.canvas_result = canvas_result
        # Single Save Annotations button at the bottom of column 2
        annotation_dir = os.path.join("projects", project_name, "labels")
        os.makedirs(annotation_dir, exist_ok=True)
        if st.button("💾 Save Annotations", key="save_annotations_btn_col2"):
            objects = st.session_state['canvas_states'][canvas_key]['objects']
            yolo_lines = []
            yaml_annots = []
            image, img_width, img_height = get_resized_image(os.path.join("projects", project_name, "images", selected_image_name))
            for i, obj in enumerate(objects):
                if obj['type'] == 'rect':
                    left, top = obj['left'], obj['top']
                    width, height = obj['width'], obj['height']
                    x_center = (left + width / 2) / img_width
                    y_center = (top + height / 2) / img_height
                    w_norm = width / img_width
                    h_norm = height / img_height
                    label = obj.get('label', label_options[0])
                    class_id = label_options.index(label)
                    yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}\n")
                    yaml_annots.append({
                        'label': label,
                        'bbox': [x_center, y_center, w_norm, h_norm]
                    })
            # Save YOLO format
            label_path = os.path.join(annotation_dir, selected_image_name.rsplit('.', 1)[0] + '.txt')
            with open(label_path, 'w') as f:
                f.writelines(yolo_lines)
            # Save YAML format (optional, for richer info)
            yaml_path = os.path.join(annotation_dir, selected_image_name.rsplit('.', 1)[0] + '.yaml')
            yaml_data = {
                'image': os.path.join("projects", project_name, "images", selected_image_name),
                'annotations': yaml_annots,
                'timestamp': str(datetime.datetime.now())
            }
            with open(yaml_path, 'w') as f:
                yaml.dump(yaml_data, f)
            st.success("✅ Annotations saved successfully!")

    except Exception as e:
        st.error(f"Error loading image {selected_image_path}: {str(e)}")
        st.stop()

# --- COLUMN 3: LABEL SELECTION FOR DRAWING + PER-BOX LABELS IF NEW LABELS EXIST ---
with col3:
    st.subheader("Assign Label to Each Box")
    if 'label_options' not in st.session_state:
        st.session_state['label_options'] = ["Animal", "Human", "Vehicle"]
    label_options = st.session_state['label_options']
    if 'label_color_map' not in st.session_state:
        st.session_state['label_color_map'] = {label: ["#FF0000", "#00FF00", "#0000FF"][i % 3] for i, label in enumerate(label_options)}
    selected_image_name = os.path.basename(image_files[st.session_state.get('current_idx', 0)])
    canvas_key = f"canvas_{selected_image_name}"
    box_objects = st.session_state.get('canvas_states', {}).get(canvas_key, {}).get('objects', [])
    if not box_objects or all(obj['type'] != 'rect' for obj in box_objects):
        st.info("Draw bounding boxes on the image to assign labels.")
    else:
        for idx, obj in enumerate(box_objects):
            if obj['type'] != 'rect':
                continue
            box_label_key = f"box_label_{canvas_key}_{idx}"
            current_label = obj.get('label', label_options[0])
            selected_label = st.selectbox(
                f"Box {idx+1}",
                label_options,
                index=label_options.index(current_label) if current_label in label_options else 0,
                key=box_label_key
            )
            obj['label'] = selected_label

# --- COLUMN 4: ADD LABEL ---
with col4:
    st.subheader("Add New Label")
    new_label = st.text_input("Label Name", "", key="new_label_input")
    if st.button("Add Label", key="add_label_btn"):
        if new_label and (new_label not in label_options):
            label_options.append(new_label)
            rand_color = "#" + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])
            st.session_state['label_color_map'][new_label] = rand_color
            st.success(f"Label '{new_label}' added!")
        elif new_label:
            st.warning(f"Label '{new_label}' already exists.")

if st.button("⬅️ Back to New Project"):
    st.switch_page("pages/new_project.py")
