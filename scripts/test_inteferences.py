from ultralytics import YOLO
import os

# Load your trained model
model = YOLO('model/baseline.pt')

# Path to test images
test_dir = 'datasets/test_subset'

# Run inference on test images
for img_name in os.listdir(test_dir):
    img_path = os.path.join(test_dir, img_name)
    
    # Run inference
    results = model.predict(source=img_path, save=True, conf=0.2)
    
    # Print results
    print(f"\nResults for {img_name}:")
    for result in results:
        print(result)

print("Inference test completed.")
