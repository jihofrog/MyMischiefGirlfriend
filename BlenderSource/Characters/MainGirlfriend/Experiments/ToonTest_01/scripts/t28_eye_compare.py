"""ToonTest_01 step 28 (see-through venv python: numpy + Pillow): v6 eye metrics from the renders and comparison sheets.

usage: <venv python> t28_eye_compare.py
Reads renders/<tag>_eye_*.png (t26), spec/eye_checks_<tag>.json and eye_section_<tag>.json (t27), r30 targets (t23).
Writes spec/eye_compare_v6.json and renders/compare_eye_v6_*.png:
  front IoU     id_front vs r30 classes (white / iris / lashes / opening = white + iris), per eye
  smile shape   lower edge of the visible eye in id_Smile / id_EyeSmile: share of flat columns, arch height (px,
                + = middle higher than the ends)
  gaze          iris centroid shift and visible iris area at gaze L / R (id_gaze_*)
  protrusion    eye-part pixels outside the original (v5g) head-only silhouette (prot_<view> vs v5g prot_<view>_head)
  light         eye white luminance / skin ring luminance, front vs 3/4 (near and far eye), nohair_* colour renders
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
TAGS = ("v5g", "v6a", "v6b")
LABEL = {"v5g": "v5g (현재)", "v6a": "A (최소 수정)", "v6b": "B (안구+눈꺼풀)", "r30": "r30 원화"}
FONT = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 26)
FS = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 20)
FACE = (700, 0, 1360, 860)


def load(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.float32) / 255


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


r30c = (np.asarray(Image.open(os.path.join(EXP, "r30", "r30_eye_classes.png"))) // 80).astype(np.uint8)
r30c = r30c[FACE[1]:FACE[3], FACE[0]:FACE[2]]
half = 1030 - FACE[0]
out = {}


def iou(a, b):
    u = (a | b).sum()
    return round(float((a & b).sum() / u), 3) if u else None


for t in TAGS:
    res = {}
    c = classes(load(os.path.join(R, f"{t}_eye_id_front.png")))
    for s, sl in (("R", slice(0, half)), ("L", slice(half, None))):
        a, b = c[:, sl], r30c[:, sl]
        res[s] = {k: iou(np.isin(a, v), np.isin(b, v)) for k, v in (("white", [1]), ("iris", [2]), ("lash", [3]), ("opening", [1, 2]))}
        ya, xa = np.nonzero(np.isin(a, [1, 2]))
        yb, xb = np.nonzero(np.isin(b, [1, 2]))
        res[s]["opening_bbox_3d"] = [int(xa.min()), int(ya.min()), int(xa.max()), int(ya.max())]
        res[s]["opening_bbox_r30"] = [int(xb.min()), int(yb.min()), int(xb.max()), int(yb.max())]
    # smile shape (L eye = right half)
    for pz in ("neutral", "Smile", "EyeSmile", "Blink"):
        f = os.path.join(R, f"{t}_eye_id_{pz}.png") if pz != "neutral" else os.path.join(R, f"{t}_eye_id_front.png")
        cc = classes(load(f))[:, half:]
        m = np.isin(cc, [1, 2])
        cols = [x for x in range(m.shape[1]) if m[:, x].any()]
        if len(cols) < 10:
            res[f"shape_{pz}"] = dict(visible_px=int(m.sum()))
            continue
        bot = np.array([np.nonzero(m[:, x])[0].max() for x in cols], float)
        n = len(cols)
        core = bot[int(n * 0.15): int(n * 0.85)]
        flat = float(np.mean(np.abs(core - np.median(core)) <= 1.0))
        mid = bot[int(n * 0.4): int(n * 0.6)].mean()
        ends = np.r_[bot[int(n * 0.12): int(n * 0.22)], bot[int(n * 0.78): int(n * 0.88)]].mean()
        res[f"shape_{pz}"] = dict(flat_share=round(flat, 2), arch_px=round(float(ends - mid), 1), visible_px=int(m.sum()))
    # gaze
    c0 = classes(load(os.path.join(R, f"{t}_eye_id_front.png")))[:, half:]
    i0 = np.argwhere(c0 == 2)
    g = {}
    for nm in ("gaze_L", "gaze_R"):
        cg = classes(load(os.path.join(R, f"{t}_eye_id_{nm}.png")))[:, half:]
        ig = np.argwhere(cg == 2)
        g[nm] = dict(shift_px=round(float(ig[:, 1].mean() - i0[:, 1].mean()), 1), iris_area=round(len(ig) / len(i0), 3))
    res["gaze"] = g
    # protrusion
    pr = {}
    for v in ("front", "side_L", "side_R", "60_L", "60_R", "34_L", "34_R"):
        a = load(os.path.join(R, f"{t}_eye_prot_{v}.png"))
        h = load(os.path.join(R, f"v5g_eye_prot_{v}_head.png"))      # the original face outline (B presses a socket in)
        eye = (a[..., 3] > 0.5) & (a[..., 0] > 0.6) & (a[..., 1] > 0.6) & (a[..., 2] < 0.4)
        lash = (a[..., 3] > 0.5) & (a[..., 0] > 0.6) & (a[..., 1] < 0.4) & (a[..., 2] > 0.6)
        pr[v] = dict(eye_px=int(eye.sum()), outside_face_px=int((eye & (h[..., 3] < 0.5)).sum()),
                     lash_outside_face_px=int((lash & (h[..., 3] < 0.5)).sum()))
    res["protrusion"] = pr
    # light: eye white vs skin ring
    li = {}
    for v in ("front", "34_L", "34_R"):
        col = load(os.path.join(R, f"{t}_eye_nohair_{v}.png"))
        a = load(os.path.join(R, f"{t}_eye_prot_{v}.png"))
        eye = (a[..., 3] > 0.5) & (a[..., 0] > 0.6) & (a[..., 1] > 0.6) & (a[..., 2] < 0.4)
        head = (a[..., 3] > 0.5) & (a[..., 2] > 0.6) & (a[..., 0] < 0.4)
        lum = col[..., :3] @ np.array([0.2126, 0.7152, 0.0722])
        sat = col[..., :3].max(-1) - col[..., :3].min(-1)
        W = col.shape[1]
        for side, sl in (("screen_left", slice(0, W // 2)), ("screen_right", slice(W // 2, None))):
            e = np.zeros_like(eye)
            e[:, sl] = eye[:, sl]
            wpx = e & (lum > 0.6) & (sat < 0.12)
            ring = np.asarray(Image.fromarray((e * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(31))) > 0
            ring &= ~np.asarray(Image.fromarray((e * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))) > 0
            ring &= head
            if wpx.sum() > 30 and ring.sum() > 30:
                li[f"{v}_{side}"] = dict(white=round(float(lum[wpx].mean()), 3), skin=round(float(lum[ring].mean()), 3),
                                         ratio=round(float(lum[wpx].mean() / lum[ring].mean()), 3))
    res["light"] = li
    res["checks"] = json.load(open(os.path.join(EXP, "spec", f"eye_checks_{t}.json")))
    out[t] = res
json.dump(out, open(os.path.join(EXP, "spec", "eye_compare_v6.json"), "w"), indent=1)
for t in TAGS:
    r = out[t]
    print(t, "IoU L", r["L"], "R", {k: r["R"][k] for k in ("white", "iris", "lash", "opening")})
    print("   shape", {k: v for k, v in r.items() if k.startswith("shape_")})
    print("   gaze", r["gaze"])
    print("   prot eye/lash", {k: (v["outside_face_px"], v["lash_outside_face_px"]) for k, v in r["protrusion"].items()})
    print("   light", r["light"])


# ------------------------------------------------------------------ sheets
def sheet(rows, path, h=360, gap=14, title=None):
    """rows: [(label, [images])]"""
    fit = lambda im: im.resize((max(1, int(im.width * h / im.height)), h))
    W = max(sum(fit(i).width for i in ims) + gap * (len(ims) - 1) for _, ims in rows) + 2 * gap
    top = 46 if title else 0
    S = Image.new("RGB", (W, top + len(rows) * (h + 44) + gap), "white")
    d = ImageDraw.Draw(S)
    if title:
        d.text((gap, 8), title, fill=(20, 20, 20), font=FONT)
    for k, (lab, ims) in enumerate(rows):
        y = top + gap + k * (h + 44)
        d.text((gap, y), lab, fill=(30, 30, 30), font=FONT)
        x = gap
        for im in ims:
            im = fit(im)
            S.paste(im, (x, y + 36))
            x += im.width + gap
    S.save(path)
    return S


rp = lambda t, n: white_bg(os.path.join(R, f"{t}_eye_{n}.png"))
r30 = Image.open(os.path.join(EXP, "r30", "r30_clothed_full.png")).convert("RGB")
sheet([("1 r30 원화 정면", [r30.crop(FACE), r30.crop((780, 400, 1280, 600))])] +
      [(f"{i + 2} {LABEL[t]} 정면", [rp(t, "face_front"), rp(t, "zoom_front")]) for i, t in enumerate(TAGS)],
      os.path.join(R, "compare_eye_v6_front.png"), h=420, title="정면 (같은 카메라·조명): 얼굴 / 눈 확대")
sheet([(f"{i + 5} {LABEL[t]} 3/4·60°·측면", [rp(t, "face_34"), rp(t, "zoom_34"), rp(t, "zoom_60"), rp(t, "face_side")])
       for i, t in enumerate(TAGS)], os.path.join(R, "compare_eye_v6_34side.png"), h=380,
      title="3/4 (35°)·60°·측면 (90°), 머리카락 포함")
sheet([(f"{LABEL[t]} 머리카락 없이: 정면·3/4·60°·측면", [white_bg(os.path.join(R, f"{t}_eye_nohair_front.png")),
                                                  white_bg(os.path.join(R, f"{t}_eye_nohair_34_L.png")),
                                                  white_bg(os.path.join(R, f"{t}_eye_prot_60_L.png")),
                                                  white_bg(os.path.join(R, f"{t}_eye_prot_side_L.png"))]) for t in TAGS],
      os.path.join(R, "compare_eye_v6_nohair.png"), h=300, title="머리카락 없이 (오른쪽 두 칸: 흰자·안구 노랑, 속눈썹 자홍, 얼굴 파랑)")
sheet([(f"8 {LABEL[t]} Blink · Blink 50% · EyeSmile (정면 / 3/4)",
        [rp(t, "expr_Blink"), rp(t, "expr_Blink50"), rp(t, "expr_EyeSmile" if t != "v5g" else "expr_Smile"),
         rp(t, "expr34_Blink"), rp(t, "expr34_EyeSmile" if t != "v5g" else "expr34_Smile")]) for t in TAGS],
      os.path.join(R, "compare_eye_v6_blink_eyesmile.png"), h=300,
      title="Blink·EyeSmile (v5g 는 EyeSmile 키가 없어 Smile)")
sheet([(f"{LABEL[t]} Neutral · Blink · Smile · EyeSmile · Surprise · MouthOpen",
        [rp(t, f"expr_{p}") for p in ("neutral", "Blink", "Smile", "EyeSmile", "Surprise", "MouthOpen")]) for t in TAGS],
      os.path.join(R, "compare_eye_v6_expressions.png"), h=260, title="표정 6종 (정면)")
sheet([(f"{LABEL[t]} 시선 왼쪽 · 오른쪽 (정면 / 3/4)", [rp(t, "gaze_L"), rp(t, "gaze_R"), rp(t, "gaze_L_34"), rp(t, "gaze_R_34")])
       for t in TAGS], os.path.join(R, "compare_eye_v6_gaze.png"), h=260, title="시선 좌우 0.15 rad")


# section drawing
def section_img(t, key, W=520, H=720, S=8000.0):
    sec = json.load(open(os.path.join(EXP, "spec", f"eye_section_{t}.json")))
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    cols = {"skin": (230, 140, 110), "eye": (80, 80, 230), "iris": (160, 60, 40), "lash": (30, 30, 30)}
    ys = [p[1] for v in sec[key].values() for p in v if p[1] is not None and not (isinstance(p[1], float) and np.isnan(p[1]))]
    y0 = min(ys) - 0.004
    for rn, pts in sec[key].items():
        P = [(p[0], p[1]) for p in pts if p[1] is not None and not np.isnan(p[1])]
        for a, b in zip(P, P[1:]):
            if abs(a[1] - b[1]) > 0.0025 or abs(a[0] - b[0]) > 0.001:
                continue
            if key == "vertical":
                pa = (30 + (a[1] - y0) * S, H / 2 - (a[0] - sec["centre"][1]) * S)
                pb = (30 + (b[1] - y0) * S, H / 2 - (b[0] - sec["centre"][1]) * S)
            else:
                pa = (W / 2 + (a[0] - sec["centre"][0]) * S * 0.9, 30 + (a[1] - y0) * S)
                pb = (W / 2 + (b[0] - sec["centre"][0]) * S * 0.9, 30 + (b[1] - y0) * S)
            d.line([pa, pb], fill=cols[rn], width=4 if rn != "lash" else 5)
    if key == "vertical" and sec.get("orig_skin_vertical") is None and t == "v6b":
        pass
    d.line([(20, H - 22), (20 + 0.01 * S, H - 22)], fill=(0, 0, 0), width=3)
    d.text((26 + 0.01 * S, H - 34), "1 cm", fill=(0, 0, 0), font=FS)
    yy = 8
    for rn, c in cols.items():
        if rn in sec[key]:
            d.text((W - 150, yy), {"skin": "피부·눈꺼풀", "eye": "흰자·안구", "iris": "홍채(메시)", "lash": "속눈썹·눈꺼풀선"}[rn], fill=c, font=FS)
            yy += 24
    return img


sheet([(f"{LABEL[t]} 단면: 세로 (왼쪽 = 보는 쪽) · 가로 (위 = 보는 쪽)", [section_img(t, "vertical"), section_img(t, "horizontal", W=900, H=460)])
       for t in TAGS], os.path.join(R, "compare_eye_v6_section.png"), h=460, title="왼눈 홍채 중심 단면 (부품별 가장 앞 면)")
up = lambda t, n: white_bg(os.path.join(R, f"unity_{t}_eye_{n}.png"))
sheet([(f"{LABEL[t]}  Blender / Unity: 정면 · 3/4 · Blink · {'Smile' if t == 'v5g' else 'EyeSmile'} · 시선 왼쪽",
        [rp(t, "zoom_front"), up(t, "zoom_front"), rp(t, "zoom_34"), up(t, "zoom_34"), rp(t, "expr_Blink"), up(t, "expr_Blink"),
         rp(t, "expr_Smile" if t == "v5g" else "expr_EyeSmile"), up(t, "expr_Smile" if t == "v5g" else "expr_EyeSmile"),
         rp(t, "gaze_L"), up(t, "gaze_L")]) for t in TAGS],
      os.path.join(R, "compare_eye_v6_unity.png"), h=220, title="Blender (왼쪽) / Unity URP FBX (오른쪽), 같은 카메라")
crop34 = white_bg(os.path.join(R, "v5g_eye_nohair_34_L.png")).crop((330, 160, 760, 440))
sheet([("v5g 수정 전: 단면 · 3/4 (머리카락 없이) · 60° 돌출 (노랑 = 눈 부품) · Smile 수평 잘림 · Unity 시선 (홍채 사라짐)",
        [section_img("v5g", "vertical"), crop34, white_bg(os.path.join(R, "v5g_eye_prot_60_L.png")).crop((200, 120, 700, 480)),
         rp("v5g", "expr_Smile"), up("v5g", "gaze_L")])],
      os.path.join(R, "compare_eye_v6_baseline.png"), h=330, title="수정 전 (v5g) 눈 구조 문제")
print("SHEETS_OK")
