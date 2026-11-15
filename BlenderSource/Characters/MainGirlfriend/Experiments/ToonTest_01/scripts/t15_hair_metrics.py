"""ToonTest_01 step 15: compare front hair renders with r30 (system python + Pillow, read only).

usage: python3 t15_hair_metrics.py <tag> [<tag> ...]
Needs ../renders/<tag>_hair_front.png and <tag>_hair_mask_front.png (t03_render.py -- <tag> hair), and the r30 crops
from t11_r30_hair_targets.py. Everything is in the HAIRBOX crop (480, 0)-(1580, 1000) at the r30 pixel scale.
  outer IoU        hair-only silhouette, each row filled between its outermost hair pixels (r30: all hair layers)
  widths           outermost hair pixels per row (screen x), and the widest row
  tip y            lowest hair row on the screen-left / screen-right half
  forehead         share of the r30 forehead (skin above the brows) not covered by hair or the clip
                   (r30: from the layers; 3D: <tag>_hair_id_front.png, hair and clip rendered flat red)
Writes ../spec/hair_metrics_<tag>.json and prints a table.
"""
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
BOX = (480, 0, 1580, 1000)
CX = 1030 - BOX[0]
ROWS = (100, 200, 300, 400, 500, 600, 700, 800, 880)


def mask_rows(img, test):
    w, h = img.size
    px = img.load()
    rows = []
    for y in range(h):
        xs = [x for x in range(w) if test(px[x, y])]
        rows.append((min(xs), max(xs)) if xs else None)
    return rows


def filled_iou(ra, rb):
    inter = union = 0
    for a, b in zip(ra, rb):
        la = (a[1] - a[0] + 1) if a else 0
        lb = (b[1] - b[0] + 1) if b else 0
        if a and b:
            i = max(0, min(a[1], b[1]) - max(a[0], b[0]) + 1)
        else:
            i = 0
        inter += i; union += la + lb - i
    return inter / union


def tips(rows):
    left = max((y for y, r in enumerate(rows) if r and r[0] < CX), default=None)
    right = max((y for y, r in enumerate(rows) if r and r[1] > CX), default=None)
    return left, right


def not_hair(p):
    r, g, b = p[:3]
    return not (r > 200 and g < 60 and b < 60)          # not the flat red of hair / clip in the id render


def forehead_share(img, fmask):
    px, fm = img.load(), fmask.load()
    w, h = img.size
    tot = skin = 0
    for y in range(h):
        for x in range(w):
            if fm[x, y] > 128:
                tot += 1; skin += not_hair(px[x, y])
    return skin / tot


def main():
    r30_rows = mask_rows(Image.open(os.path.join(EXP, "r30", "r30_hair_union_mask.png")).convert("L"), lambda v: v > 128)
    fmask = Image.open(os.path.join(EXP, "r30", "r30_forehead_mask.png")).convert("L")
    tg = json.load(open(os.path.join(EXP, "spec", "r30_hair_targets.json")))
    ref = dict(widths={y: r30_rows[y] for y in ROWS}, max_width=max((r[1] - r[0] + 1, y) for y, r in enumerate(r30_rows) if r),
               tips=tips(r30_rows), forehead=tg["forehead_exposed"])
    out = {"r30": ref}
    for tag in sys.argv[1:]:
        m = Image.open(os.path.join(EXP, "renders", f"{tag}_hair_mask_front.png")).convert("RGBA")
        rows = mask_rows(m, lambda p: p[3] > 128)
        idr = Image.open(os.path.join(EXP, "renders", f"{tag}_hair_id_front.png")).convert("RGBA")
        out[tag] = dict(outer_iou=round(filled_iou(r30_rows, rows), 3), widths={y: rows[y] for y in ROWS},
                        max_width=max((r[1] - r[0] + 1, y) for y, r in enumerate(rows) if r), tips=tips(rows),
                        forehead=round(forehead_share(idr, fmask), 3))
        json.dump(out[tag], open(os.path.join(EXP, "spec", f"hair_metrics_{tag}.json"), "w"), indent=1)
    names = ["r30"] + sys.argv[1:]
    print("metric".ljust(16) + "".join(n.rjust(18) for n in names))
    print("outer IoU".ljust(16) + "".join(str(out[n].get("outer_iou", "-")).rjust(18) for n in names))
    for y in ROWS:
        cells = []
        for n in names:
            r = out[n]["widths"][y]
            cells.append(f"{r[1] - r[0] + 1} ({r[0] + BOX[0]}-{r[1] + BOX[0]})" if r else "-")
        print(f"width y{y}".ljust(16) + "".join(c.rjust(18) for c in cells))
    print("max width".ljust(16) + "".join(f"{out[n]['max_width'][0]} @y{out[n]['max_width'][1]}".rjust(18) for n in names))
    print("tip y L/R".ljust(16) + "".join(f"{out[n]['tips'][0]}/{out[n]['tips'][1]}".rjust(18) for n in names))
    print("forehead skin".ljust(16) + "".join(f"{out[n]['forehead']:.3f}".rjust(18) for n in names))


if __name__ == "__main__":
    main()
