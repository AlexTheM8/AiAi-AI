from functools import partial

import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab
from skimage.metrics import structural_similarity as compare_ssim

# TODO
"""
 - Understand Image
    - Image States: [in-game, fall-out, time-out, goal]
    - If 'in-game' -> do action (move), fitness change based on goal "distance" (see Fitness Evaluation)
    - If 'fall-out' -> strong negative fitness. add last-known goal "distance". reset
    - If 'time-out' -> negative fitness. add last-known goal "distance" where increased if goal in sight. reset
    - If 'goal' -> strong positive fitness. reset
 - Fitness Evaluation
    - Strong positive on GOAL
    - Strong negative on FALL OUT
    - Negative on TIME OUT
    - Goal Distance
        - To be more granular in fitness, implement functionality on goal "distance"
        - "Distance" will be defined by 1) is goal on screen? 2) If so, how much space does it take up on screen?
        - If not on screen, do not increase/decrease fitness (or insignificantly decrease)
        - In case of FALL OUT, save last known goal "distance"
        - In TIME OUT, increase fitness based on if goal is in sight & how close
        
NOTE: Input is set to 39000 = 3 * (width / 10) * (height / 10), could potentially change to / 20 = 9750 or / 25 = 6240
or / 50 = 1560
"""
# warnings.filterwarnings("ignore", category=UserWarning)
# model = hub.load('yolov5', 'custom', 'yolov5/runs/train/exp/weights/best.pt', source='local')

ImageGrab.grab = partial(ImageGrab.grab, all_screens=True)
x_pad, y_pad = 405, 460

# width, height = 250, 45
# x_pad, y_pad = 850, 270

time_over = cv2.imread('images/time_over.png')
# goal = cv2.imread('images/goal.png')
# fall_out = cv2.imread('fall_out.png')

# Mask range
rgb_low, rgb_up = np.array([0, 10, 0]), np.array([120, 255, 100])
# while True:
# Grab new img
img = pyautogui.screenshot(region=(x_pad, y_pad, time_over.shape[1], time_over.shape[0]))
img = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2RGB)
# cv2.imwrite('time_over.png', img)

# Do masking
mask = cv2.inRange(time_over, rgb_low, rgb_up)
copy = np.copy(time_over)
# img_copy = np.copy(img)
# copy[mask != 0], img[mask != 0] = [0, 0, 0], [0, 0, 0]
copy = cv2.bitwise_and(copy, copy, mask=mask)
# cv2.imshow('copy', copy)
# img_copy = cv2.bitwise_and(img, img, mask=mask)
# cv2.imshow('img', img)

copy = time_over - copy
cv2.imshow('f', copy)

img_copy = img - copy
cv2.imshow('f2', img_copy)

# Convert to gray
# img = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2GRAY)
# copy = cv2.cvtColor(np.array(copy), cv2.COLOR_BGR2GRAY)
# score, _ = compare_ssim(img, copy, full=True)
# if score > 0.75:
#     print(score)
# cv2.imshow('mask', masked_image)
# img.save('fall_out.png')
# img.show()
# cv2.imshow('orig', fall_out)
# img = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2GRAY)
# cv2.imwrite('fall_out.png', img)
# y_lower, x_lower = y_pad - 30, x_pad - 310
# y_upper, x_upper = height + y_lower, width + x_lower
# cv2.imshow('orig', fall_out)
# cv2.imshow('crop', img[y_lower:y_upper, x_lower:x_upper])
# score, _ = compare_ssim(fall_out, img[y_lower:y_upper, x_lower:x_upper], full=True)
# if score > 0.5:
#     print(f"SSIM: {score}")
# results = model(img, size=640).xyxy[0]
# if len(results) > 0:
#     x1, y1, x2, y2, prob, _ = results[0]
#     x1, y1, x2, y2, prob = float(x1), float(y1), float(x2), float(y2), float(prob)
#     percent = (((x2 - x1) * (y2 - y1)) / (width * height)) * 100
#     print(percent)
cv2.waitKey(0)
