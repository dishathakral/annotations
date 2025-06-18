import streamlit as st
import os
import zipfile
import io
import importlib.util

st.set_page_config(page_title="Create New Project", layout="wide")

st.title("📦 Create New Project")

# Project name input
st.subheader("Step 1: Enter Project Name")
project_name = st.text_input("Project Name", "")

if st.button("Create Project"):
    if project_name:
        project_dir = os.path.join("projects", project_name)
        images_dir = os.path.join(project_dir, "images")
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
            st.success(f"Project '{project_name}' created!")
        else:
            st.warning(f"Project '{project_name}' already exists.")
    else:
        st.error("Please enter a project name.")

st.markdown("---")

# Folder upload via zip file
st.subheader("Step 2: Import Data (Upload Folder as .zip)")
zip_file = st.file_uploader(
    "Upload a folder as a .zip file containing only images (.jpg, .jpeg, .png, .bmp)",
    type=["zip"],
    accept_multiple_files=False
)

SUPPORTED_EXTS = (".jpg", ".jpeg", ".png", ".bmp")

if zip_file and project_name:
    project_dir = os.path.join("projects", project_name)
    images_dir = os.path.join(project_dir, "images")
    if not os.path.exists(images_dir):
        st.error("Please create the project first.")
    else:
        with zipfile.ZipFile(io.BytesIO(zip_file.read())) as z:
            valid_files = [f for f in z.namelist() if f.lower().endswith(SUPPORTED_EXTS)]
            if not valid_files:
                st.error("No supported image files found in the uploaded zip.")
            else:
                for file in valid_files:
                    filename = os.path.basename(file)
                    if filename:
                        with z.open(file) as source, open(os.path.join(images_dir, filename), "wb") as target:
                            target.write(source.read())
                st.success(f"Uploaded {len(valid_files)} image(s) to '{project_name}/images'!")

st.markdown("---")

# Step 3: Annotation options
st.subheader("Step 3: Annotate Data")
col1, col2 = st.columns(2)

with col1:
    if st.button("📝 Manually Annotate Data"):
        if project_name:
            st.session_state['project_name'] = project_name
            st.switch_page("pages/manually_annotate.py")
        else:
            st.warning("Please enter a project name first.")

with col2:
    st.button("⚡ Automatic Annotation")

if st.button("⬅️ Back to Home"):
    st.switch_page("Home.py")
