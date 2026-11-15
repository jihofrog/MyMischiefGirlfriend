"""ToonTest_01 step 1: measure the r30 Live2D master (read only) and write the face style spec numbers.

usage: <see-through venv python> t01_r30_face_spec.py
Reads Live2DSource/MainGirlfriend/06_PSD/MainGirlfriend_Front_v30.psd through scripts/s22_outfit_prep.py (runtime
default expression: closed mouth, eye clipping). Writes ../r30/*.png and ../spec/r30_face_spec.json.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
PROJ = os.path.abspath(os.path.join(EXP, "..", "..", "..", "..", ".."))
L2D = os.path.join(PROJ, "Live2DSource", "MainGirlfriend")
sys.path.insert(0, os.path.join(L2D, "scripts"))
import s22_outfit_prep as s22  # noqa: E402
import s23_outfit_qa as q  # noqa: E402

GROUND = 3040


def pct(px, ps=(10, 50, 90)):
    return [np.percentile(px, p, axis=0).round(1).tolist() for p in ps]


def main():
    layers = s22.load_layers()
    by = {n: np.asarray(im).astype(float) for n, _, im in layers}
    # images: clothed (r30 as drawn, runtime expression) and body base
    clothing = s22.CLOTHING
    s22.CLOTHING = set()
    clothed = s22.body_base(layers)
    s22.CLOTHING = clothing
    bare = s22.body_base(layers)
    for name, im in (("r30_clothed", clothed), ("r30_body", bare)):
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
        bg.convert("RGB").save(os.path.join(EXP, "r30", name + "_full.png"))
    face_box = (700, 0, 1360, 860)
    bg = Image.new("RGBA", clothed.size, (255, 255, 255, 255)); bg.alpha_composite(clothed)
    bg.crop(face_box).save(os.path.join(EXP, "r30", "r30_face_front.png"))

    def bbox(n, thr=128):
        a = by[n][..., 3] > thr; ys, xs = np.nonzero(a)
        return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    hs = by["Head_Skin"]
    hair_top = min(bbox(n)[1] for n in ("Hair_Back", "Bangs", "Hair_Back_AI"))
    chin = bbox("Head_Skin")[3]
    head_h = chin - hair_top
    total = GROUND - hair_top
    # face width per row (largest skin run, no ears)
    def run(y):
        op = np.concatenate([[0], (hs[y, :, 3] > 128).astype(int), [0]])
        st = np.nonzero(np.diff(op) == 1)[0]; en = np.nonzero(np.diff(op) == -1)[0]
        i = int(np.argmax(en - st)); return int(st[i]), int(en[i])
    widths = {y: run(y) for y in (420, 480, 520, 560, 600, 640, 680, 720, 740)}
    eyeR, eyeL = bbox("EyeWhite_Clean_R"), bbox("EyeWhite_Clean_L")
    irisR, irisL = bbox("Iris_R"), bbox("Iris_L")
    nose, mouth = bbox("Nose", 40), bbox("Mouth_Closed", 40)
    browR, browL = bbox("Brow_R_AI", 60), bbox("Brow_L_AI", 60)
    earR, earL = bbox("Ear_R"), bbox("Ear_L")
    clip = bbox("HairClip_X")
    fw = widths[560][1] - widths[560][0]
    cx = (widths[560][0] + widths[560][1]) / 2
    # colours
    core = hs[..., 3] == 255
    skin = hs[..., :3][core]
    Ls = q.lab(skin)[:, 0]
    lo, mid, hi = np.percentile(Ls, [10, 50, 90])
    shade = skin[Ls < np.percentile(Ls, 12)].mean(0); base = skin[np.abs(Ls - mid) < 2].mean(0); light = skin[Ls > np.percentile(Ls, 95)].mean(0)
    hair = np.concatenate([by[n][..., :3][by[n][..., 3] == 255] for n in ("Bangs", "HairSide_R", "HairSide_L", "Hair_Back")])
    Lh = q.lab(hair)[:, 0]
    hair_cols = dict(shadow=hair[Lh < np.percentile(Lh, 15)].mean(0).round(1).tolist(),
                     base=hair[np.abs(Lh - np.median(Lh)) < 2].mean(0).round(1).tolist(),
                     highlight=hair[Lh > np.percentile(Lh, 97)].mean(0).round(1).tolist())
    def outline(n, rows):
        lp = q.line_pixels(by[n].astype(np.uint8), rows)
        return lp.mean(0).round(1).tolist()
    # line thickness: run of pixels darker than the skin shadow on the face outline (left side), rows 600-720
    thick = []
    for y in range(600, 720, 4):
        x0 = int(np.nonzero(hs[y, :, 3] > 0)[0].min())
        seg = hs[y, x0:x0 + 12]
        dark = (seg[:, 3] > 60) & (seg[:, :3].mean(1) < shade.mean() - 25)
        thick.append(int(dark.sum()))
    clip_px = by["HairClip_X"][..., :3][by["HairClip_X"][..., 3] == 255]
    spec = dict(
        canvas=[2048, 3072], ground_y=GROUND, hair_top_y=hair_top, chin_y=chin,
        head_height_px=head_h, total_height_px=total, heads_tall=round(total / head_h, 2),
        face_centre_x=cx, face_width_px={str(k): v[1] - v[0] for k, v in widths.items()},
        face_width_at_eye_bottom_560=fw,
        face_height_brow_to_chin_px=chin - min(browR[1], browL[1]),
        eye_white={"R": eyeR, "L": eyeL}, iris={"R": irisR, "L": irisL},
        eye_width_over_face_width=round(((eyeR[2] - eyeR[0]) + (eyeL[2] - eyeL[0])) / 2 / fw, 3),
        eye_height_over_head_height=round(((eyeR[3] - eyeR[1]) + (eyeL[3] - eyeL[1])) / 2 / head_h, 3),
        eye_gap_px=eyeL[0] - eyeR[2], eye_gap_over_eye_width=round((eyeL[0] - eyeR[2]) / ((eyeR[2] - eyeR[0] + eyeL[2] - eyeL[0]) / 2), 3),
        eye_centre_y=round((eyeR[1] + eyeR[3] + eyeL[1] + eyeL[3]) / 4, 1),
        eye_centre_from_chin_over_head=round((chin - (eyeR[1] + eyeR[3] + eyeL[1] + eyeL[3]) / 4) / head_h, 3),
        nose=nose, mouth_closed=mouth, brow={"R": browR, "L": browL}, ear={"R": earR, "L": earL}, hairclip=clip,
        nose_from_chin_over_head=round((chin - (nose[1] + nose[3]) / 2) / head_h, 3),
        mouth_from_chin_over_head=round((chin - (mouth[1] + mouth[3]) / 2) / head_h, 3),
        skin=dict(base=base.round(1).tolist(), shadow=shade.round(1).tolist(), light=light.round(1).tolist(), L_p10_p50_p90=[round(lo, 1), round(mid, 1), round(hi, 1)]),
        hair=hair_cols,
        outline=dict(face=outline("Head_Skin", range(600, 740)), hair_bangs=outline("Bangs", range(200, 560)),
                     hair_side=outline("HairSide_R", range(500, 880)), thickness_px_face_p50=float(np.median(thick))),
        hairclip_colour=dict(base=np.percentile(clip_px, 50, axis=0).round(1).tolist(), dark=np.percentile(clip_px, 8, axis=0).round(1).tolist()),
        iris_colours=pct(by["Iris_R"][..., :3][by["Iris_R"][..., 3] == 255]),
    )
    json.dump(spec, open(os.path.join(EXP, "spec", "r30_face_spec.json"), "w"), indent=1)
    # iris texture for the 3D eye: R iris + pupil + highlight composited on its own, square crop
    ir = Image.new("RGBA", (2048, 3072))
    for n in ("Iris_Rim_R", "Iris_R", "Pupil_R"):
        ir.alpha_composite(Image.fromarray(by[n].astype(np.uint8)))
    ir.crop((850, 445, 970, 565)).save(os.path.join(EXP, "r30", "tex_iris_R.png"))
    hl = Image.fromarray(by["EyeHighlight_R"].astype(np.uint8)).crop((850, 445, 970, 565))
    hl.save(os.path.join(EXP, "r30", "tex_eye_highlight_R.png"))
    print(json.dumps(spec, indent=1))


if __name__ == "__main__":
    main()
