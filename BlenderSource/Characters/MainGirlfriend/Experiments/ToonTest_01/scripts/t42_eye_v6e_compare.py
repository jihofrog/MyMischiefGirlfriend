"""ToonTest_01 step 42 (see-through venv python: numpy + Pillow): v6e numbers and comparison sheets.

usage: <venv python> t42_eye_v6e_compare.py <ref tag> <tag> ...   (e.g. v6d_3 v6e_A v6e_B v6e_C)
Reads renders/<tag>_e6_*.png (t41), <tag>_eye_id_*.png (t26), spec/eye_v6e_analysis_<tag>.json (t39),
spec/eye_v6d_checks_<tag>.json (t37), spec/eye_<tag>_stats.json (t40 / t51). Writes spec/eye_<OUTTAG>_compare.json and
renders/compare_eye_<OUTTAG>_*.png (env OUTTAG, default v6e).
  front        IoU vs r30 classes, mean difference of the front eye close up to the reference
  per angle    left eye (no hair): visible eyeball px and bright white px (struct / eyeL renders); 35-90: eyeball px
               outside the face outline (the candidate's own head and the reference head)
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
SP = os.path.join(EXP, "spec")
FONT = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 26)
FS = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 19)
TAGS = sys.argv[1:]
REF = TAGS[0]
ANG = (0, 35, 45, 60, 90)
LAB = {"v6d_3": "v6d_3 (기준)", "v6e_A": "후보 A 얼굴 곡면", "v6e_B": "후보 B 눈 바깥쪽", "v6e_C": "후보 C A+B",
       "v6f_A": "v6f A 눈꺼풀 경계", "v6f_B": "v6f B 바깥 감싸기"}
OUTTAG = os.environ.get("OUTTAG", "v6e")          # v6f: writes eye_v6f_compare.json / compare_eye_v6f_*.png
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


r30c = (np.asarray(Image.open(os.path.join(EXP, "r30", "r30_eye_classes.png"))) // 80).astype(np.uint8)[FACE[1]:FACE[3], FACE[0]:FACE[2]]
out = {}
for t in TAGS:
    res = {}
    c = classes(load(os.path.join(R, f"{t}_eye_id_front.png")))
    for s, sl in (("R", slice(0, 330)), ("L", slice(330, None))):
        for k, vals in (("opening", [1, 2]), ("iris", [2]), ("lash", [3])):
            a_, b_ = np.isin(c[:, sl], vals), np.isin(r30c[:, sl], vals)
            res[f"iou_{s}_{k}"] = round(float((a_ & b_).sum() / max(1, (a_ | b_).sum())), 3)
    z = load(os.path.join(R, f"{t}_eye_zoom_front.png"))
    z0 = load(os.path.join(R, f"{REF}_eye_zoom_front.png"))
    comp = lambda a: a[..., :3] * a[..., 3:] + (1 - a[..., 3:])
    res["front_zoom_diff_vs_ref"] = round(float(np.abs(comp(z) - comp(z0)).mean()), 4)
    ang = {}
    for a in ANG:
        st = load(os.path.join(R, f"{t}_e6_struct_{a}.png"))
        ball = (st[..., 3] > 0.5) & (st[..., 1] > st[..., 0] + 0.2) & (st[..., 1] > st[..., 2] + 0.2)
        col = comp(load(os.path.join(R, f"{t}_e6_eyeL_{a}.png")))
        L = col @ np.array([0.2126, 0.7152, 0.0722])
        sat = col.max(-1) - col.min(-1)
        white = ball & (L > 0.62) & (sat < 0.12)
        d = dict(eyeball_px=int(ball.sum()), white_px=int(white.sum()), white_lum=round(float(L[white].mean()), 3) if white.any() else None)
        if a >= 35:
            sil = load(os.path.join(R, f"{t}_e6_sil_{a}.png"))
            eye = (sil[..., 3] > 0.5) & (sil[..., 0] > 0.6) & (sil[..., 1] > 0.6) & (sil[..., 2] < 0.4)
            own = load(os.path.join(R, f"{t}_e6_silhead_{a}.png"))[..., 3] > 0.5
            ref = load(os.path.join(R, f"{REF}_e6_silhead_{a}.png"))[..., 3] > 0.5
            d["eyeball_outside_own_face_px"] = int((eye & ~own).sum())
            d["eyeball_outside_ref_face_px"] = int((eye & ~ref).sum())
            d["face_outline_change_px"] = int((own ^ ref).sum())
        ang[a] = d
    res["angles"] = ang
    an = json.load(open(os.path.join(SP, f"eye_v6e_analysis_{t}.json")))
    res["analysis_L"] = {k: an["L"][k] for k in ("yaw_eyeball_at_iris", "yaw_lid_plane", "yaw_skin_ring", "yaw_skin_outer_corner", "spread_vs_front", "bulge")}
    ck = os.path.join(SP, f"eye_v6d_checks_{t}.json")
    if os.path.exists(ck):
        c2 = json.load(open(ck))
        res["penetration"] = {s: sum(c2[s]["lid_or_skirt_behind_eyeball"].values()) + c2[s]["eyeball_in_front_of_skin_outside_socket"] for s in "LR"}
    stp = os.path.join(SP, f"eye_{t}_stats.json")
    if os.path.exists(stp):
        res["build"] = json.load(open(stp))
    gz = {}
    i0 = (classes(load(os.path.join(R, f"{t}_eye_id_front.png"))) == 2).sum()
    for nm in ("gaze_L", "gaze_R"):
        cg = classes(load(os.path.join(R, f"{t}_eye_id_{nm}.png")))
        gz[nm] = dict(iris_L=int((cg[:, 330:] == 2).sum()), iris_R=int((cg[:, :330] == 2).sum()))
    res["gaze_iris_px"] = gz
    res["blink_visible_eye_px"] = int(np.isin(classes(load(os.path.join(R, f"{t}_eye_id_Blink.png"))), [1, 2]).sum())
    out[t] = res
    print(t, json.dumps({k: v for k, v in res.items() if k not in ("analysis_L", "build")}))
    print("   spread35/45/60", {a: res["analysis_L"]["spread_vs_front"][str(a)] for a in (35, 45, 60)}, "bulge", {a: (res["analysis_L"]["bulge"][str(a)] or {}).get("bulge_over_chord_mm") for a in (35, 45, 60)})
json.dump(out, open(os.path.join(SP, f"eye_{OUTTAG}_compare.json"), "w"), indent=1)


def sheet(rows, path, h=240, gap=12, title=None):
    fit = lambda im: im.resize((max(1, int(im.width * h / im.height)), h))
    W = max(sum(fit(i).width for i, _ in ims) + gap * (len(ims) - 1) for _, ims in rows) + 2 * gap
    top = 46 if title else 0
    S = Image.new("RGB", (W, top + len(rows) * (h + 64) + gap), "white")
    d = ImageDraw.Draw(S)
    if title:
        d.text((gap, 8), title, fill=(20, 20, 20), font=FONT)
    for k, (lab, ims) in enumerate(rows):
        y = top + gap + k * (h + 64)
        d.text((gap, y), lab, fill=(30, 30, 30), font=FONT)
        x = gap
        for im, cap in ims:
            im = fit(im)
            S.paste(im, (x, y + 32))
            if cap:
                d.text((x + 4, y + 34 + h), cap, fill=(60, 60, 60), font=FS)
            x += im.width + gap
    S.save(path)


e6 = lambda t, n: white_bg(os.path.join(R, f"{t}_e6_{n}.png"))
sheet([(LAB.get(t, t), [(e6(t, f"face_{a}"), f"{a}°") for a in ANG]) for t in TAGS],
      os.path.join(R, f"compare_eye_{OUTTAG}_faces.png"), h=260, title="1 머리카락 포함 얼굴 (같은 카메라·조명)")
sheet([(LAB.get(t, t), [(e6(t, f"eyeL_{a}"), f"{a}° 흰자 {out[t]['angles'][a]['white_px']} px") for a in ANG]) for t in TAGS],
      os.path.join(R, f"compare_eye_{OUTTAG}_eyeL.png"), h=210, title="2 머리카락 없이 왼눈 확대 (흰자 px = 밝은 흰자 면적)")
sheet([(LAB.get(t, t), [(e6(t, f"eyes_{a}"), f"{a}°") for a in ANG]) for t in TAGS],
      os.path.join(R, f"compare_eye_{OUTTAG}_eyes.png"), h=170, title="머리카락 없이 두 눈")
sheet([(LAB.get(t, t), [(e6(t, f"struct_{a}"), f"{a}°") for a in ANG]) for t in TAGS],
      os.path.join(R, f"compare_eye_{OUTTAG}_struct.png"), h=210, title="4 구조 진단: 피부 회색, 눈꺼풀 시트 파랑, 안구 초록, 속눈썹 빨강")
poses = ("Neutral", "Blink50", "Blink", "EyeSmile", "SmileEyeSmile", "Surprise", "GazeL", "GazeR")
names = {"Neutral": "Neutral", "Blink50": "Blink 50%", "Blink": "Blink 100%", "EyeSmile": "EyeSmile", "SmileEyeSmile": "Smile+EyeSmile",
         "Surprise": "Surprise", "GazeL": "시선 왼쪽", "GazeR": "시선 오른쪽"}
sheet([(LAB.get(t, t) + " 35°", [(e6(t, f"expr_{p}_35"), names[p]) for p in poses]) for t in TAGS] +
      [(LAB.get(TAGS[-1], TAGS[-1]) + " 정면", [(e6(TAGS[-1], f"expr_{p}_0"), names[p]) for p in poses])],
      os.path.join(R, f"compare_eye_{OUTTAG}_expr.png"), h=170, title="표정·시선 (머리카락 포함)")


def section(t, W=900, H=420, S=7000.0):
    sec = json.load(open(os.path.join(SP, f"eye_e6_section_{t}.json")))
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    cols = {"skin": (200, 140, 120), "lid": (60, 90, 230), "lash": (200, 30, 30), "ball": (40, 170, 60)}
    ys = [y for r in cols for _, y in sec[r] if y is not None]
    y0 = min(ys) - 0.004
    for r, c in cols.items():
        P = [(x, y) for x, y in sec[r] if y is not None]
        for a, b in zip(P, P[1:]):
            if abs(a[1] - b[1]) < 0.003 and abs(a[0] - b[0]) < 0.001:
                d.line([(20 + a[0] * S, 20 + (a[1] - y0) * S), (20 + b[0] * S, 20 + (b[1] - y0) * S)], fill=c, width=4)
    d.line([(20, H - 20), (20 + 0.01 * S, H - 20)], fill=(0, 0, 0), width=3)
    d.text((26 + 0.01 * S, H - 32), "1 cm  (위 = 얼굴 앞, 오른쪽 = 귀 쪽)", fill=(0, 0, 0), font=FS)
    yy = 8
    for r, c in cols.items():
        d.text((W - 170, yy), {"skin": "피부", "lid": "눈꺼풀 시트", "lash": "속눈썹 띠", "ball": "안구"}[r], fill=c, font=FS)
        yy += 24
    return img


sheet([(LAB.get(t, t) + " 위에서 본 단면 (왼눈 홍채 높이)", [(section(t), "")]) for t in TAGS],
      os.path.join(R, f"compare_eye_{OUTTAG}_section.png"), h=300, title="3 눈꺼풀·안구·피부 깊이 관계 (부품별 가장 앞 면)")
print("SHEETS_OK")
