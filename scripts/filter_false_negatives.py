from ultralytics import YOLO
import os
import yaml

# Load trained model
model = YOLO('model/baseline.pt')

# Define paths
project_root = os.getcwd()
test_subset_dir = 'datasets/test_subset/'
false_negative_labels_dir = 'annotations/false_negatives/'

# Make sure output folder exists
os.makedirs(false_negative_labels_dir, exist_ok=True)

# Run inference on test subset
results = model.predict(source=test_subset_dir, save=False, conf=0.2)

# User-defined threshold
user_threshold = 0.5

# Metadata to save
potential_false_negatives = []

# Process results
for result in results:
    image_path = result.path
    image_name = os.path.basename(image_path).replace('.jpg', '.txt')

    # Extract confidence scores
    if result.boxes is not None and len(result.boxes) > 0:
        confs = result.boxes.conf.cpu().numpy()
    else:
        confs = []

    # If no detection ≥ threshold — flag as potential false negative
    if len(confs) == 0 or all(c < user_threshold for c in confs):
        print(f"Potential false negative: {image_name}")

        # Save model predictions (if any) as YOLO format to false_negative_labels_dir
        pred_label_path = os.path.join(false_negative_labels_dir, image_name)
        with open(pred_label_path, 'w') as f:
            if result.boxes is not None and len(result.boxes) > 0:
                for box, conf, cls in zip(
                    result.boxes.xywhn.cpu().numpy(),  # normalized xywh format
                    confs,
                    result.boxes.cls.cpu().numpy()
                ):
                    line = f"{int(cls)} {box[0]:.6f} {box[1]:.6f} {box[2]:.6f} {box[3]:.6f}\n"
                    f.write(line)
            else:
                # No predictions — leave file empty or optionally skip creating it
                pass

        # Store metadata for YAML
        detections = []
        if result.boxes is not None and len(result.boxes) > 0:
            for box, conf, cls in zip(
                result.boxes.xyxy.cpu().numpy(),  # absolute xyxy for YAML
                confs,
                result.boxes.cls.cpu().numpy()
            ):
                detections.append({
                    'bbox': box.tolist(),
                    'confidence': float(conf),
                    'label': result.names[int(cls)]
                })

        potential_false_negatives.append({
            'image_path': os.path.relpath(image_path, project_root),
            'detections': detections
        })

# Save metadata to YAML
with open('annotations/potential_false_negatives.yaml', 'w') as f:
    yaml.dump(potential_false_negatives, f)

print("False negative filtering complete.")
