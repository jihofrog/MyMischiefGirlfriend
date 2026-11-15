"""ToonTest_01 step 34 (see-through venv python: numpy + Pillow): v6c lid / lash numbers and comparison sheets.

usage: <venv python> t34_eye_v6c_compare.py
Reads renders/<tag>_lid_<case>_front.png (t30), <tag>_eye_*.png (t26), unity_<tag>_eye_*.png (u05),
r30/eye_tex_lash_v6c_L.png (expected lash area). Writes spec/eye_v6c_compare.json and renders/compare_eye_v6c_*.png.
  holes       light pixels inside the r30 lash silhouette (left upper lid, front x4): skin / lid showing through the band
  crumbs      dark pixels outside the lash silhouette (+2 r30 px) and outside the eyeball: smudge / broken pieces
  shimmer     Unity, native size, 8 frames moved 1/8 px: lash coverage change between frames and isolated dark specks
  IoU         front id vs r30 classes (as t28)
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
TGT = json.load(open(os.path.join(EXP, "spec", "r30_eye_targets.json")))
FONT = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 26)
FS = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 19)
BOX, SC = (1070, 405, 1270, 525), 4


def load(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.float32) / 255


def white_bg(p):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return bg.convert("RGB")


def lum(a):
    return a[..., :3] @ np.array([0.2126, 0.7152, 0.0722])


def grow(m, r):
    return np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(r))) > 0


def shrink(m, r):
    return np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(r))) > 0


# expected lash silhouette (upper band, clean v6c alpha) in the lid crop, crease excluded (it is not a lash)
tex = load(os.path.join(EXP, "r30", "eye_tex_lash_v6c_L.png"))
tb = TGT["tex_box"]["L"]
H, W = (BOX[3] - BOX[1]) * SC, (BOX[2] - BOX[0]) * SC
yy, xx = np.mgrid[0:H, 0:W]
px, py = BOX[0] + (xx + 0.5) / SC, BOX[1] + (yy + 0.5) / SC
u = ((px - tb[0]) / (tb[2] - tb[0]) * 1024).astype(int).clip(0, 1023)
v = ((py - tb[1]) / (tb[3] - tb[1]) * 1024).astype(int).clip(0, 1023)
lash_exp = tex[v, u, 3] > 0.9
crease = json.load(open(os.path.join(EXP, "spec", "eye_v6c_crease.json")))["L"]["centre"]
cy_by_x = np.interp(px[0], [c[0] for c in crease], [c[1] for c in crease], left=np.nan, right=np.nan)
near_crease = np.abs(py - cy_by_x[None, :]) < 4
lash_exp &= ~near_crease
inner = shrink(lash_exp, 9)
outer = grow(lash_exp, 2 * SC * 2 + 1)
ball = None
idp = os.path.join(R, "v6b_lid_id_front.png")
if os.path.exists(idp):
    a = load(idp)
    ball = grow((a[..., 1] > 0.8) & (a[..., 0] < 0.3) & (a[..., 2] < 0.3), 5)
out = {"diag": {}}


def lid_numbers(path):
    a = load(path)
    L = lum(a)
    holes = int((inner & (L > 0.45)).sum())
    dark = (L < 0.25) & ~outer & ~near_crease
    if ball is not None:
        dark &= ~ball
    return dict(holes_px=holes, smudge_px=int(dark.sum()))


cases = ["full", "no_lash", "no_skirt", "no_lids", "no_outline", "lash_flat", "lash_blend", "ball_flat", "lash_fwd"]
for t in ("v6b", "v6c"):
    for c in cases:
        p = os.path.join(R, f"{t}_lid_{c}_front.png")
        if os.path.exists(p):
            out["diag"][f"{t}_{c}"] = lid_numbers(p)
for t in ("v6a", "v6b", "v6c"):
    out["diag"][f"{t}_with_hair"] = lid_numbers(os.path.join(R, f"{t}_eye_lid_front.png"))
for t in ("v6b", "v6c"):
    out["diag"][f"unity_{t}"] = lid_numbers(os.path.join(R, f"unity_{t}_eye_lid_front.png"))

# shimmer (Unity, native size)
expn = np.asarray(Image.fromarray(lash_exp.astype(np.uint8) * 255).resize((BOX[2] - BOX[0], BOX[3] - BOX[1]), Image.BOX)) > 0
region = grow(expn, 7)
sh = {}
for t in ("v6b", "v6c"):
    frames = [load(os.path.join(R, f"unity_{t}_eye_jit{f}.png")) for f in range(8)]
    cov = [float((1 - lum(fr))[region].sum()) for fr in frames]
    specks = []
    for fr in frames:
        d = lum(fr) < 0.3
        iso = d & ~grow(d & shrink(grow(d, 3), 3) & ~d, 1)
        n = d & region
        # isolated dark pixels: dark with no dark 4-neighbour
        nb = np.zeros_like(d)
        nb[1:] |= d[:-1]; nb[:-1] |= d[1:]; nb[:, 1:] |= d[:, :-1]; nb[:, :-1] |= d[:, 1:]
        specks.append(int((n & ~nb).sum()))
    dif = [float(np.abs(lum(frames[k + 1]) - lum(frames[k]))[region].mean()) for k in range(7)]
    sh[t] = dict(coverage_cv=round(float(np.std(cov) / np.mean(cov)), 4), isolated_dark_px_per_frame=round(float(np.mean(specks)), 1),
                 mean_frame_change=round(float(np.mean(dif)), 4))
out["shimmer_unity"] = sh

# front IoU vs r30
FACE = (700, 0, 1360, 860)


def classes(a):
    c = np.zeros(a.shape[:2], np.uint8)
    on = a[..., 3] > 0.5
    c[on & (a[..., 1] > 0.6) & (a[..., 0] < 0.4) & (a[..., 2] < 0.4)] = 1
    c[on & (a[..., 2] > 0.6) & (a[..., 0] < 0.4) & (a[..., 1] < 0.4)] = 2
    c[on & (a[..., 0] > 0.6) & (a[..., 1] < 0.4) & (a[..., 2] < 0.4)] = 3
    return c


r30c = (np.asarray(Image.open(os.path.join(EXP, "r30", "r30_eye_classes.png"))) // 80).astype(np.uint8)[FACE[1]:FACE[3], FACE[0]:FACE[2]]
iou = {}
for t in ("v6b", "v6c"):
    c = classes(load(os.path.join(R, f"{t}_eye_id_front.png")))
    res = {}
    for s, sl in (("R", slice(0, 330)), ("L", slice(330, None))):
        for k, vals in (("opening", [1, 2]), ("iris", [2]), ("lash", [3])):
            a_, b_ = np.isin(c[:, sl], vals), np.isin(r30c[:, sl], vals)
            res[f"{s}_{k}"] = round(float((a_ & b_).sum() / max(1, (a_ | b_).sum())), 3)
    iou[t] = res
out["iou"] = iou
out["v6c_stats"] = json.load(open(os.path.join(EXP, "spec", "eye_v6c_stats.json")))
json.dump(out, open(os.path.join(EXP, "spec", "eye_v6c_compare.json"), "w"), indent=1)
print(json.dumps({k: out[k] for k in ("diag", "shimmer_unity", "iou")}, indent=0))


# ------------------------------------------------------------------ sheets
def sheet(rows, path, h=300, gap=14, title=None):
    fit = lambda im: im.resize((max(1, int(im.width * h / im.height)), h))
    Wd = max(sum(fit(i).width for i, _ in ims) + gap * (len(ims) - 1) for _, ims in rows) + 2 * gap
    top = 46 if title else 0
    S = Image.new("RGB", (Wd, top + len(rows) * (h + 70) + gap), "white")
    d = ImageDraw.Draw(S)
    if title:
        d.text((gap, 8), title, fill=(20, 20, 20), font=FONT)
    for k, (lab, ims) in enumerate(rows):
        y = top + gap + k * (h + 70)
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
up = lambda t, n: white_bg(os.path.join(R, f"unity_{t}_eye_{n}.png"))
r30 = Image.open(os.path.join(EXP, "r30", "r30_clothed_full.png")).convert("RGB")
dg = out["diag"]
sheet([("윗눈꺼풀 확대 (정면, 같은 카메라·조명)", [(r30.crop(BOX).resize((800, 480), Image.LANCZOS), "1 r30 원화"),
                                         (rp("v6a", "lid_front"), "2 A안"), (rp("v6b", "lid_front"), "3 B안 수정 전"),
                                         (rp("v6c", "lid_front"), "4 v6c 수정 후")]),
       ("윗눈꺼풀 확대 (3/4)", [(rp("v6a", "lid_34"), "A안"), (rp("v6b", "lid_34"), "B안 수정 전"), (rp("v6c", "lid_34"), "v6c")])],
      os.path.join(R, "compare_eye_v6c_lid.png"), h=330, title="윗눈꺼풀·속눈썹·쌍꺼풀 (머리카락 포함)")
sheet([("v6c 얼굴: 5 정면 · 6 3/4 · 7 60° · 측면", [(rp("v6c", "face_front"), "정면"), (rp("v6c", "face_34"), "3/4"),
                                                (rp("v6c", "face_60"), "60°"), (rp("v6c", "face_side"), "측면")]),
       ("v6c 눈 확대: 정면 · 3/4 · 60°", [(rp("v6c", "zoom_front"), ""), (rp("v6c", "zoom_34"), ""), (rp("v6c", "zoom_60"), "")])],
      os.path.join(R, "compare_eye_v6c_faces.png"), h=380, title="v6c 얼굴 전체")
poses = [("neutral", "Neutral"), ("Blink50", "Blink 50%"), ("Blink", "Blink 100%"), ("EyeSmile", "EyeSmile"),
         ("SmileEyeSmile", "Smile + EyeSmile"), ("Surprise", "Surprise")]
sheet([("B안 수정 전", [(rp("v6b", f"expr_{p}"), lab) for p, lab in poses]),
       ("v6c", [(rp("v6c", f"expr_{p}"), lab) for p, lab in poses]),
       ("v6c 윗눈꺼풀 확대", [(rp("v6c", f"exprlid_{p}"), lab) for p, lab in poses]),
       ("v6c 3/4", [(rp("v6c", f"expr34_{p}"), lab) for p, lab in poses])],
      os.path.join(R, "compare_eye_v6c_expr.png"), h=240, title="표정 (B안 수정 전 / v6c, 같은 카메라)")
cap = lambda k: f"구멍 {dg[k]['holes_px']} px"
sheet([("B안 원인 분리 (머리카락 없이, 한 요소씩 변경)", [(white_bg(os.path.join(R, f"v6b_lid_{c}_front.png")), f"{c}: {cap('v6b_' + c)}")
                                              for c in ("full", "no_lids", "no_skirt", "no_outline", "lash_fwd")]),
       ("", [(white_bg(os.path.join(R, f"v6b_lid_{c}_front.png")), f"{c}: {cap('v6b_' + c)}") for c in ("lash_flat", "lash_blend", "ball_flat", "no_lash")]
        + [(white_bg(os.path.join(R, "v6b_lid_id_front.png")), "id: 빨강 속눈썹, 파랑 눈꺼풀, 회색 피부")]),
       ("v6c (같은 분리)", [(white_bg(os.path.join(R, f"v6c_lid_{c}_front.png")), f"{c}: {cap('v6c_' + c)}") for c in ("full", "no_lids", "lash_flat")]
        + [(white_bg(os.path.join(R, "v6c_lid_id_front.png")), "id")])],
      os.path.join(R, "compare_eye_v6c_diag.png"), h=200, title="윗눈꺼풀 뭉개짐 원인 (구멍 = r30 속눈썹 자리 안에서 밝게 비치는 px, x4 확대)")
sheet([(f"{t} Blender / Unity", [(rp(t, "lid_front"), "Blender 정면"), (up(t, "lid_front"), "Unity 정면"),
                                 (rp(t, "exprlid_Blink50"), "Blender Blink 50%"), (up(t, "exprlid_Blink50"), "Unity Blink 50%"),
                                 (rp(t, "exprlid_EyeSmile"), "Blender EyeSmile"), (up(t, "exprlid_EyeSmile"), "Unity EyeSmile")])
       for t in ("v6b", "v6c")] +
      [("v6c 3/4·얼굴 Blender / Unity", [(rp("v6c", "face_34"), "Blender 3/4"), (up("v6c", "face_34"), "Unity 3/4"),
                                        (rp("v6c", "face_60"), "Blender 60°"), (up("v6c", "face_60"), "Unity 60°")])],
      os.path.join(R, "compare_eye_v6c_unity.png"), h=230, title="Blender / Unity URP (같은 구도)")
print("SHEETS_OK")
