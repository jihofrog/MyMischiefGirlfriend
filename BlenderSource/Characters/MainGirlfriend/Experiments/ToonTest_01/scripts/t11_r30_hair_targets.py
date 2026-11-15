"""ToonTest_01 step 11: measure the r30 hair layers (read only) as targets for the hair_bob_01 volume rebuild.

usage: <see-through venv python> t11_r30_hair_targets.py
Reads Live2DSource/MainGirlfriend/06_PSD/MainGirlfriend_Front_v30.psd through scripts/s22_outfit_prep.py.
Writes ../spec/r30_hair_targets.json and, cropped to HAIRBOX, ../r30/r30_hairbox.png (r30 as drawn),
../r30/r30_hair_union_mask.png (all hair layers) and ../r30/r30_forehead_mask.png (skin above the brows).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
PROJ = os.path.abspath(os.path.join(EXP, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "Live2DSource", "MainGirlfriend", "scripts"))
import s22_outfit_prep as s22  # noqa: E402

HAIRBOX = (480, 0, 1580, 1000)
HAIR = ("Hair_Back_AI", "Hair_Back", "HairSide_R", "HairSide_L", "Bangs")


def runs(row, min_len=3):
    out, x = [], 0
    xs = np.nonzero(row)[0]
    if len(xs) == 0:
        return out
    start = prev = xs[0]
    for x in xs[1:]:
        if x != prev + 1:
            if prev - start + 1 >= min_len:
                out.append([int(start), int(prev)])
            start = x
        prev = x
    if prev - start + 1 >= min_len:
        out.append([int(start), int(prev)])
    return out


def main():
    by = {n: np.asarray(im) for n, _, im in s22.load_layers()}
    a = {n: by[n][..., 3] > 128 for n in by}
    union = np.zeros_like(a["Bangs"])
    for n in HAIR:
        union |= a[n]
    spec = json.load(open(os.path.join(EXP, "spec", "r30_face_spec.json")))
    brow_top = min(spec["brow"]["R"][1], spec["brow"]["L"][1])
    forehead = a["Head_Skin"].copy(); forehead[brow_top - 4:] = False
    cover = a["Bangs"] | a["HairSide_R"] | a["HairSide_L"] | a["HairClip_X"]
    exposed = float((forehead & ~cover).sum() / forehead.sum())
    rows, bangs, side_r, side_l = {}, {}, {}, {}
    for y in range(0, 1000, 2):
        xs = np.nonzero(union[y])[0]
        if len(xs):
            rows[y] = [int(xs.min()), int(xs.max())]
        if y % 4 == 0:
            for d, n in ((bangs, "Bangs"), (side_r, "HairSide_R"), (side_l, "HairSide_L")):
                r = runs(a[n][y])
                if r:
                    d[y] = r
    x0, y0, x1, y1 = HAIRBOX
    out = dict(box=HAIRBOX, brow_top_y=brow_top, union_rows=rows, bangs_runs=bangs, side_R_runs=side_r, side_L_runs=side_l,
               forehead_px=int(forehead.sum()), forehead_exposed=round(exposed, 4), union_px_in_box=int(union[y0:y1, x0:x1].sum()))
    json.dump(out, open(os.path.join(EXP, "spec", "r30_hair_targets.json"), "w"))
    Image.fromarray((union[y0:y1, x0:x1] * 255).astype(np.uint8)).save(os.path.join(EXP, "r30", "r30_hair_union_mask.png"))
    Image.fromarray((forehead[y0:y1, x0:x1] * 255).astype(np.uint8)).save(os.path.join(EXP, "r30", "r30_forehead_mask.png"))
    full = Image.open(os.path.join(EXP, "r30", "r30_clothed_full.png")).convert("RGB")
    full.crop(HAIRBOX).save(os.path.join(EXP, "r30", "r30_hairbox.png"))
    print("TARGETS rows", len(rows), "bang rows", len(bangs), "forehead px", out["forehead_px"], "union px", out["union_px_in_box"])


if __name__ == "__main__":
    main()
