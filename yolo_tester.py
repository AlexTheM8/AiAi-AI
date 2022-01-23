import torch
from PIL import Image
import os

# Model
model = torch.hub.load('../yolov5', 'custom', '../yolov5/runs/train/exp/weights/best.pt', source='local')

# Images
imgs = [Image.open(f'test_images/{f}') for f in os.listdir('test_images')]

# Inference
results = model(imgs, size=640)  # includes NMS

# Results
results.print()
results.save()  # or .show()
