"""Put the render on white and crop it to 4:3.

    ~/miniforge3/bin/python compose.py beauty.png matte.png out.png [--shadow 0.8] [--jpg out.jpg]

beauty: objects + floor shadow in alpha (shadow catcher);  matte: objects only.
Per pixel, with c = object coverage and a = beauty alpha:
    shadow density  s = (a - c) / (1 - c)
    result          = beauty_rgb * a  +  (1 - c) * white * (1 - k * s)
so k scales the floor shadow without touching the board.  The crop is the
tightest 4:3 frame round the board and its shadow, plus a margin.
"""
import argparse

import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("beauty")
ap.add_argument("matte")
ap.add_argument("out")
ap.add_argument("--shadow", type=float, default=0.8, help="floor shadow strength, 0..1")
ap.add_argument("--fill", type=float, default=0.90, help="board height / frame height")
ap.add_argument("--fill-w", type=float, default=0.86, help="largest board width / frame width")
ap.add_argument("--top", type=float, default=0.35, help="share of the vertical margin above the board")
ap.add_argument("--jpg", help="also write a 2400 x 1800 JPEG here")
ap.add_argument("--cut", type=float, default=0.06, help="shadow density below this is cut off")
a = ap.parse_args()


def load(p):
    im = Image.open(p)
    arr = np.asarray(im).astype(np.float64)
    top = 65535.0 if arr.max() > 255 else 255.0
    return arr / top


B, Mt = load(a.beauty), load(a.matte)
rgb, al, c = B[..., :3], B[..., 3:4], Mt[..., 3:4]
# beauty_rgb is straight alpha, sRGB-encoded.  Blend in linear light.
lin = lambda x: np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
enc = lambda x: np.where(x <= 0.0031308, x * 12.92, 1.055 * np.clip(x, 0, None) ** (1 / 2.4) - 0.055)
s = np.clip((al - c) / np.maximum(1 - c, 1e-4), 0, 1)
s = np.clip((s - a.cut) / (1 - a.cut), 0, 1)                 # no faint grey haze to the frame edge
out = lin(rgb) * al + (1 - c) * (1 - a.shadow * s)          # premultiplied board + shaded white
img = np.clip(enc(out) * 255 + 0.5, 0, 255).astype(np.uint8)

# Crop: frame the board itself (the matte), not its shadow -- the published
# card's framing: the board spans ~90 % of the height, a little above centre.
ys, xs = np.nonzero(c[..., 0] > 0.5)
x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
w, h = x1 - x0, y1 - y0
H = h / a.fill
W = H * 4 / 3
if w / W > a.fill_w:
    W = w / a.fill_w
    H = W * 3 / 4
cx = (x0 + x1) / 2
top = y0 - (H - h) * a.top
box = [round(cx - W / 2), round(top), round(cx + W / 2), round(top + H)]
if box[0] < 0 or box[1] < 0 or box[2] > img.shape[1] or box[3] > img.shape[0]:
    print("WARNING: the crop runs past the rendered frame; render with a lower fill", box, img.shape)
canvas = Image.new("RGB", (box[2] - box[0], box[3] - box[1]), (255, 255, 255))
canvas.paste(Image.fromarray(img), (-box[0], -box[1]))
canvas.save(a.out)
print("board bbox", (x0, y0, x1, y1), "crop", box, "->", canvas.size)
if a.jpg:
    canvas.resize((2400, 1800), Image.LANCZOS).save(a.jpg, "JPEG", quality=93, subsampling=0, optimize=True)
    print("wrote", a.jpg)
