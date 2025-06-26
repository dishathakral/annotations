import json
import os
from ultralytics import YOLO

# Load your JSON file
with open('backend\projects\gg\subset_1\subset_1.json') as f:
    data = json.load(f)

image_names = data['images']

# Path to your images folder
images_dir = 'backend/projects/gg/images/'

# Build full image paths
image_paths = [os.path.join(images_dir, name) for name in image_names]

# Load pretrained YOLO model
model = YOLO('yolov8n.pt')

# Run predictions on each image
for img_path in image_paths:
    if os.path.exists(img_path):  # check if image exists
        model.predict(source=img_path, save=True, conf=0.3)
    else:
        print(f"Image not found: {img_path}")
