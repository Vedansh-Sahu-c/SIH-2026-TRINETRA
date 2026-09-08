"""Generate a synthetic border-scene clip so you can test with zero hardware.

    python make_demo_video.py

Produces data/demo_border.mp4 -- a walker, a vehicle, a stray dog, and a
person who paces near the fence and abandons a bag. Upload it in the UI.
"""
import cv2
import numpy as np
import math
from pathlib import Path

W, H, FPS, SECS = 960, 540, 25, 40
out_path = Path(__file__).parent / "data" / "demo_border.mp4"
out_path.parent.mkdir(exist_ok=True)
vw = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))


def bg():
    img = np.zeros((H, W, 3), np.uint8)
    img[:H // 2] = (58, 48, 40)            # sky
    img[H // 2:] = (44, 62, 52)            # ground
    cv2.line(img, (0, H // 2), (W, H // 2), (70, 80, 70), 2)
    for x in range(0, W, 80):              # fence posts
        cv2.line(img, (x, 300), (x, 380), (90, 95, 105), 3)
    cv2.line(img, (0, 310), (W, 310), (80, 85, 95), 2)
    return img


def person(img, x, y, s=1.0, color=(190, 175, 160)):
    h = int(70 * s)
    cv2.circle(img, (int(x), int(y - h)), int(9 * s), (170, 150, 130), -1)
    cv2.rectangle(img, (int(x - 11 * s), int(y - h + 8 * s)),
                  (int(x + 11 * s), int(y - 18 * s)), color, -1)
    cv2.line(img, (int(x - 6 * s), int(y - 18 * s)), (int(x - 8 * s), int(y)),
             color, max(2, int(5 * s)))
    cv2.line(img, (int(x + 6 * s), int(y - 18 * s)), (int(x + 8 * s), int(y)),
             color, max(2, int(5 * s)))


def car(img, x, y, s=1.0):
    w, h = int(120 * s), int(45 * s)
    cv2.rectangle(img, (int(x), int(y - h)), (int(x + w), int(y)), (120, 90, 60), -1)
    cv2.rectangle(img, (int(x + w * .22), int(y - h * 1.55)),
                  (int(x + w * .75), int(y - h)), (140, 110, 80), -1)
    cv2.circle(img, (int(x + w * .22), int(y)), int(11 * s), (30, 30, 30), -1)
    cv2.circle(img, (int(x + w * .78), int(y)), int(11 * s), (30, 30, 30), -1)


def dog(img, x, y, s=1.0):
    cv2.ellipse(img, (int(x), int(y - 12 * s)), (int(20 * s), int(9 * s)),
                0, 0, 360, (105, 95, 85), -1)
    cv2.circle(img, (int(x + 20 * s), int(y - 18 * s)), int(7 * s), (105, 95, 85), -1)
    for dx in (-12, -4, 6, 14):
        cv2.line(img, (int(x + dx * s), int(y - 8 * s)),
                 (int(x + dx * s), int(y)), (105, 95, 85), max(2, int(3 * s)))


def bag(img, x, y, s=1.0):
    cv2.rectangle(img, (int(x - 12 * s), int(y - 22 * s)),
                  (int(x + 12 * s), int(y)), (60, 60, 150), -1)
    cv2.rectangle(img, (int(x - 7 * s), int(y - 28 * s)),
                  (int(x + 7 * s), int(y - 22 * s)), (50, 50, 130), -1)


total = FPS * SECS
for f in range(total):
    t = f / FPS
    img = bg().copy()
    img = cv2.add(img, np.random.randint(0, 9, (H, W, 3), dtype=np.uint8))

    # normal traffic: someone walking straight across
    person(img, 60 + (t * 26) % (W + 120), 430, 1.05)

    # a vehicle on the border road
    if 4 < t < 20:
        car(img, -140 + (t - 4) * 68, 350, .95)

    # stray dog wandering (should be suppressed, not alarmed)
    if t > 6:
        dog(img, 300 + math.sin(t * .8) * 190, 470, 1.0)

    # the threat: approaches fence, paces, drops a bag, leaves
    if t > 10:
        if t < 16:
            px = 800 - (t - 10) * 58                 # approach
        elif t < 30:
            px = 452 + math.sin((t - 16) * 1.15) * 105   # pacing
        else:
            px = 452 + (t - 30) * 62                 # departs
        person(img, px, 388, 1.25, (150, 160, 170))
        if 20 < t < 30:
            bag(img, px + 26, 388, .9)               # carried
        if t >= 30:
            bag(img, 505, 388, .9)                   # abandoned

    cv2.putText(img, f"BOP-04 NORTH  T+{t:05.1f}s", (14, 28),
                cv2.FONT_HERSHEY_SIMPLEX, .6, (200, 210, 220), 1)
    vw.write(img)

vw.release()
print(f"Wrote {out_path}  ({SECS}s @ {FPS}fps)")
print("Upload it in the dashboard, draw a fence across the middle, and watch.")
