import os
import shutil

# Paths
project_dir = r"c:\Users\CSIO\Desktop\disha\automate_annotation\projects\hit_uav"
images_dir = os.path.join(project_dir, "images")

# Get all files in project_dir (excluding folders)
all_files = [f for f in os.listdir(project_dir) if os.path.isfile(os.path.join(project_dir, f))]

# Get all files in images_dir
image_files = set(os.listdir(images_dir))

# Move misplaced images to images_dir
moved = []
for f in all_files:
    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff')):
        if f not in image_files:
            src = os.path.join(project_dir, f)
            dst = os.path.join(images_dir, f)
            shutil.move(src, dst)
            moved.append(f)

if moved:
    print(f"Moved {len(moved)} images to 'images/':", moved)
else:
    print("No misplaced images found.")
