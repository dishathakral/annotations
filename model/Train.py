from ultralytics import YOLO

# Load YOLO model
model = YOLO('yolov8n.pt')  # or 'yolov8s.pt' if available

# Train the model
model.train(
    data='/Users/disha/Downloads/automate_annotation/subset.yaml',       # path to your dataset yaml
    epochs=10,                   # adjust as needed
    batch=4,                     # adjust batch size based on your Mac memory
    imgsz=640,                   # image size
    project='.',                 # output in current folder (model/)
    name='train_run'             # creates model/train_run/ folder
)

# After training, move best.pt to baseline.pt
import shutil
shutil.copy('train_run/weights/best.pt', 'baseline.pt')

print("Training completed! New weights saved as 'baseline.pt'")
