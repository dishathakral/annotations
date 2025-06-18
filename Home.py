import streamlit as st
import os

st.set_page_config(page_title="Home", layout="wide")

st.title("📡 Infrared Object Detection - Home")

if st.button("➕ Create New Project"):
    st.switch_page("pages/new_project.py")

st.markdown("---")

# Show existing projects
project_dir = "projects"
os.makedirs(project_dir, exist_ok=True)
projects = os.listdir(project_dir)

st.subheader("📂 Existing Projects")
if not projects:
    st.write("No projects yet.")
else:
    for project in projects:
        st.write(f"- {project}")
