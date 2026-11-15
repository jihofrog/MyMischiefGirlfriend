"""ToonTest_01 step 38 (see-through venv python: numpy + Pillow): v6d candidate numbers and comparison sheets.

usage: <venv python> t38_eye_v6d_compare.py <tag> [<tag> ...]      (first tag = reference, e.g. v6c)
Reads renders/<tag>_eye_*.png (t26), spec/eye_v6d_checks_<tag>.json (t37). Writes spec/eye_v6d_compare.json and, with
--sheets, renders/compare_eye_v6d_*.png.
  front     IoU of the front id vs r30 classes (opening / iris / lash), mean abs difference of the front eye close up to
            the reference (0..1)
  views     eyeball (white + iris) pixels and their mean luminance against the skin ring, front / 3/4 / 60 / side (no hair)
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
FONT = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 26)
FS = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 19)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
SHEETS = "--sheets" in sys.argv
FACE = (700, 0, 1360, 860)


def load(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.float64) / 255


def white_bg(p):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return bg.convert("RGB")


def classes(a):
    c = np.zeros(a.shape[:2], np.uint8)
    on = a[..., 3] > 0.5
    c[on & (a[..., 1] > 0.6) & (a[..., 0] < 0.4) & (a[..., 2] < 0.4)] = 1
    c[on & (a[..., 2] > 0.6) & (a[..., 0] < 0.4) & (a[..., 1] < 0.4)] = 2
    c[on & (a[..., 0] > 0.6) & (a[..., 1] < 0.4) & (a[..., 2] < 0.4)] = 3
    return c


lum = lambda a: a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722
r30c = (np.asarray(Image.open(os.path.join(EXP, "r30", "r30_eye_classes.png"))) // 80).astype(np.uint8)[FACE[1]:FACE[3], FACE[0]:FACE[2]]
ref = args[0]
out = {}
for t in args:
    res = {}
    c = classes(load(os.path.join(R, f"{t}_eye_id_front.png")))
    for s, sl in (("R", slice(0, 330)), ("L", slice(330, None))):
        for k, vals in (("opening", [1, 2]), ("iris", [2]), ("lash", [3])):
            a_, b_ = np.isin(c[:, sl], vals), np.isin(r30c[:, sl], vals)
            res[f"iou_{s}_{k}"] = round(float((a_ & b_).sum() / max(1, (a_ | b_).sum())), 3)
    zf = load(os.path.join(R, f"{t}_eye_zoom_front.png"))[..., :3]
    z0 = load(os.path.join(R, f"{ref}_eye_zoom_front.png"))[..., :3]
    res["front_zoom_diff_vs_ref"] = round(float(np.abs(zf - z0).mean()), 4)
    views = {}
    for v in ("front", "34_L", "60_L", "side_L"):
        col = load(os.path.join(R, f"{t}_eye_nohair_{v}.png"))
        idm = load(os.path.join(R, f"{t}_eye_prot_{v}.png"))
        eye = (idm[..., 3] > 0.5) & (idm[..., 0] > 0.6) & (idm[..., 1] > 0.6) & (idm[..., 2] < 0.4)
        head = (idm[..., 3] > 0.5) & (idm[..., 2] > 0.6) & (idm[..., 0] < 0.4)
        L = lum(col)
        W = col.shape[1]
        sl = slice(W // 2, None) if v != "front" else slice(W // 2, None)   # the left eye (near eye in the turned views)
        e = np.zeros_like(eye)
        e[:, sl] = eye[:, sl]
        if v != "front":                                     # turned views: both eyes (the far one is mostly hidden)
            e = eye.copy()
        white = e & (L > 0.6)
        ring = np.asarray(Image.fromarray((e * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(31))) > 0
        ring &= ~(np.asarray(Image.fromarray((e * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))) > 0)
        ring &= head
        views[v] = dict(eye_px=int(e.sum()), white_lum=round(float(L[white].mean()), 3) if white.any() else None,
                        white_vs_skin=round(float(L[white].mean() / L[ring].mean()), 3) if white.any() and ring.any() else None)
    res["views"] = views
    ck = os.path.join(EXP, "spec", f"eye_v6d_checks_{t}.json")
    if os.path.exists(ck):
        c2 = json.load(open(ck))
        res["dome_L"] = c2["L"]["dome_mm"]
        res["dome_R"] = c2["R"]["dome_mm"]
        res["below_ring"] = [c2["L"]["below_ring_mm_med"], c2["R"]["below_ring_mm_med"]]
        res["curv_L"] = c2["L"]["apex_curvature_per_m"]
        res["penetration"] = {s: c2[s]["lid_or_skirt_behind_eyeball"] for s in "LR"}
        res["eyeball_pokes"] = [c2["L"]["eyeball_in_front_of_skin_outside_socket"], c2["R"]["eyeball_in_front_of_skin_outside_socket"]]
    out[t] = res
    print(t, json.dumps({k: v for k, v in res.items() if k not in ("penetration",)}))
old = json.load(open(os.path.join(EXP, "spec", "eye_v6d_compare.json"))) if os.path.exists(os.path.join(EXP, "spec", "eye_v6d_compare.json")) else {}
old.update(out)
json.dump(old, open(os.path.join(EXP, "spec", "eye_v6d_compare.json"), "w"), indent=1)

if SHEETS:
    LAB = {"v6c": "v6c 기준", "v6d_1_b08": "v6d_1 위치만 (뒤로 0.8 mm)", "v6d_2_f10": "v6d_2 위치 + 곡률 -10 %",
           "v6d_3": "v6d_3 위치 + 곡률 + 눈꺼풀 + 재질"}

    def sheet(rows, path, h=280, gap=14, title=None):
        fit = lambda im: im.resize((max(1, int(im.width * h / im.height)), h))
        Wd = max(sum(fit(i).width for i, _ in ims) + gap * (len(ims) - 1) for _, ims in rows) + 2 * gap
        top = 46 if title else 0
        S = Image.new("RGB", (Wd, top + len(rows) * (h + 66) + gap), "white")
        d = ImageDraw.Draw(S)
        if title:
            d.text((gap, 8), title, fill=(20, 20, 20), font=FONT)
        for k, (lab, ims) in enumerate(rows):
            y = top + gap + k * (h + 66)
            d.text((gap, y), lab, fill=(30, 30, 30), font=FONT)
            x = gap
            for im, cap in ims:
                im = fit(im)
                S.paste(im, (x, y + 34))
                if cap:
                    d.text((x + 4, y + 36 + h), cap, fill=(60, 60, 60), font=FS)
                x += im.width + gap
        S.save(path)

    rp = lambda t, n: white_bg(os.path.join(R, f"{t}_eye_{n}.png"))
    tags = args
    sheet([(LAB.get(t, t), [(rp(t, "face_front"), "1 정면"), (rp(t, "face_34"), "2 3/4"), (rp(t, "face_60"), "3 60°"), (rp(t, "face_side"), "4 측면")])
           for t in tags], os.path.join(R, "compare_eye_v6d_faces.png"), h=300, title="얼굴 (같은 카메라·조명, 머리카락 포함)")
    sheet([(LAB.get(t, t), [(rp(t, "zoom_front"), "5 정면"), (rp(t, "zoom_34"), "6 3/4"), (rp(t, "zoom_60"), "7 60°"), (rp(t, "zoom_side"), "8 측면")])
           for t in tags], os.path.join(R, "compare_eye_v6d_zoom.png"), h=260, title="눈 확대 (머리카락 포함)")
    sheet([(LAB.get(t, t), [(white_bg(os.path.join(R, f"{t}_eye_nohair_{v}.png")).crop(b), cap) for v, b, cap in
                            (("front", (410, 215, 650, 395), "정면"), ("34_L", (240, 215, 480, 395), "3/4"),
                             ("60_L", (110, 215, 350, 395), "60°"), ("side_L", (50, 215, 290, 395), "측면"))])
           for t in tags], os.path.join(R, "compare_eye_v6d_nohair.png"), h=240, title="머리카락 없이 왼눈 (정면·3/4·60°·측면)")
    poses = [("neutral", "Neutral"), ("Blink50", "Blink 50%"), ("Blink", "Blink 100%"), ("EyeSmile", "EyeSmile"),
             ("SmileEyeSmile", "Smile + EyeSmile"), ("Surprise", "Surprise")]
    sheet([(LAB.get(t, t) + " 정면", [(rp(t, f"expr_{p}"), lab) for p, lab in poses]) for t in (tags[0], tags[-1])] +
          [(LAB.get(t, t) + " 3/4", [(rp(t, f"expr34_{p}"), lab) for p, lab in poses]) for t in (tags[0], tags[-1])],
          os.path.join(R, "compare_eye_v6d_expr.png"), h=220, title="표정 (기준 / 추천 후보)")
    print("SHEETS_OK")
