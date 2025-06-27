import os
import urllib.request

# List of (family, version, url) tuples
weights = [
    ("yolov8", "yolov8n.pt", "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt"),
    ("yolov8", "yolov8s.pt", "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt"),
    # Add more YOLOv8 weights as needed
    # Example for SAM (update the URL to the correct checkpoint for your use case):
    ("sam", "sam_vit_h.pth", "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"),
    # Add more SAM weights as needed
]

for family, version, url in weights:
    out_dir = os.path.join("models", family)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, version)
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        print(f"Downloading {version} to {out_path} ...")
        urllib.request.urlretrieve(url, out_path)
        print("Done.")
    else:
        print(f"{out_path} already exists and is not empty.")
