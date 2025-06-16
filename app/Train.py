# Perfect — let’s lock this down into a clean Train module implementation plan and code structure.

# 📌 ✅ Final Train Module (Basic Training on yolov8n only)
# 📖 Features:
# Function	Action
# Upload .yaml config	Save to subset.yaml
# Hardcoded model	yolov8n.pt
# Train button	Trigger Train.py with subprocess
# Show training status	While subprocess runs, display “Training in progress...”, then “Training completed successfully!” after it finishes

# 📁 Folder Structure:
# Copy
# Edit
# project/
# │
# ├── model/
# │   └── Train.py
# │
# ├── datasets/
# │   └── subset.yaml  ← gets overwritten
# │
# ├── train_run/
# │
# ├── model/
# │   └── yolov8n.pt
# │
# ├── app.py  ← (Streamlit UI)
# │
# └── requirements.txt
# ✅ 📖 Train.py
# Assumption: It takes no CLI params since it always uses yolov8n.pt and subset.yaml
# (If needed, I can help you add argument parsing later)

# ✅ 📖 app.py (Train module code)
# python
# Copy
# Edit
import streamlit as st
import os
import subprocess
import shutil

# Page config
st.set_page_config(page_title="Train YOLOv8 Model", layout="wide")

st.title("🚀 Train a New YOLOv8 Model")

# Upload YAML file
uploaded_yaml = st.file_uploader("Upload your dataset configuration (.yaml)", type=["yaml"])

# Handle YAML upload
if uploaded_yaml is not None:
    with open("subset.yaml", "wb") as f:
        f.write(uploaded_yaml.read())
    st.success("✅ Configuration file uploaded successfully as subset.yaml!")

# Train button (disabled until YAML is uploaded)
if uploaded_yaml is not None:
    if st.button("Start Training"):
        with st.status("Training in progress...", expanded=True) as status:
            # Trigger Train.py via subprocess
            process = subprocess.run(["python", "model/Train.py"], capture_output=True, text=True)

            # Show training logs if you want
            st.code(process.stdout)

            if process.returncode == 0:
                status.update(label="✅ Training completed successfully!", state="complete")
            else:
                status.update(label="❌ Training failed. Check logs.", state="error")
                st.error(process.stderr)
else:
    st.warning("📄 Please upload a .yaml configuration file first.")

# ✅ 📖 Explanation
# file_uploader — lets user upload a .yaml

# Saved as subset.yaml — overwriting existing

# Train button — enabled only after upload

# subprocess.run() — runs Train.py

# st.status() — clean status message with dynamic state update

# Training logs shown inside Streamlit — if needed