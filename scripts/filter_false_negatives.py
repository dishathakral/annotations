from ultralytics import YOLO
import os
import shutil
import yaml

# Load trained model
model = YOLO('model/baseline.pt')

# Define paths
test_subset_dir = 'datasets/test_subset/'
labels_dir = 'datasets/test/labels/'
false_negative_labels_dir = 'annotations/false_negatives/'

# Make sure output folder exists
os.makedirs(false_negative_labels_dir, exist_ok=True)

# Run inference on test subset
results = model.predict(source=test_subset_dir, save=False, conf=0.2)

# User-defined threshold
user_threshold = 0.4

# Metadata to save
potential_false_negatives = []

# Process results
for result in results:
    image_path = result.path
    image_name = os.path.basename(image_path).replace('.jpg', '.txt')

    # Extract confidence scores
    if result.boxes is not None:
        confs = result.boxes.conf.cpu().numpy()
    else:
        confs = []

    # If no detection ≥ threshold — flag as potential false negative
    if len(confs) == 0 or all(c < user_threshold for c in confs):
        print(f"Potential false negative: {image_name}")

        # Copy corresponding label file (if exists) to false_negative_labels_dir
        label_path = os.path.join(labels_dir, image_name)
        if os.path.exists(label_path):
            shutil.copy(label_path, os.path.join(false_negative_labels_dir, image_name))
        else:
            print(f"No label found for {image_name}")

        # Store metadata for YAML
        potential_false_negatives.append({
            'image_path': image_path,
            'detections': [
                {
                    'bbox': box.tolist(),
                    'confidence': float(conf),
                    'label': result.names[int(cls)]
                }
                for box, conf, cls in zip(
                    result.boxes.xyxy.cpu().numpy(),
                    confs,
                    result.boxes.cls.cpu().numpy()
                )
            ]
        })

# Save metadata to YAML
with open('annotations/potential_false_negatives.yaml', 'w') as f:
    yaml.dump(potential_false_negatives, f)

print("False negative filtering complete.")
