from ultralytics import YOLO
import os
import shutil

# Load YOLO model
model = YOLO('yolov8n.pt')

# Set project directory
project_dir = 'train_run'
os.makedirs(project_dir, exist_ok=True)

# Find existing run numbers
existing_runs = [
    int(d.replace('run', ''))
    for d in os.listdir(project_dir)
    if os.path.isdir(os.path.join(project_dir, d)) and d.startswith('run') and d.replace('run', '').isdigit()
]

# Determine next run number
next_run_num = max(existing_runs, default=0) + 1
run_name = f'run{next_run_num}'

# Train model — will create train_run/run1/, run2/, etc.
model.train(
    data='subset.yaml',
    epochs=10,
    batch=4,
    imgsz=640,
    project=project_dir,
    name=run_name
)

# Path setup
weights_dir = os.path.join(project_dir, run_name, 'weights')
model_save_path = 'model/baseline.pt'

# Check for best.pt or last.pt
best_model_path = os.path.join(weights_dir, 'best.pt')
last_model_path = os.path.join(weights_dir, 'last.pt')

if os.path.exists(best_model_path):
    source_model_path = best_model_path
elif os.path.exists(last_model_path):
    source_model_path = last_model_path
    print("⚠️ No best.pt found. Using last.pt instead.")
else:
    print(f"❌ No weights found in {weights_dir}.")
    exit()

# Ensure model directory exists
os.makedirs(os.path.dirname(model_save_path), exist_ok=True)

# Copy selected model to baseline.pt
shutil.copy(source_model_path, model_save_path)
print(f"✅ Updated baseline.pt from {source_model_path}")
