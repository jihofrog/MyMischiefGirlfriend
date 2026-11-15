"""Race3D v2 expression mixing rules (pure python): emotion intensities (0..1) -> shape key values per mesh group.

Same rules a Unity driver would follow:
  - Happy is staged on the eyes: 0..0.6 crescent (ExHappyA), 0.6..1 crescent -> closed smile (ExHappyB)
  - eye emotion keys scale by (1 - Blink): Blink always wins and never closes past 100 %
  - view-angle keys scale by (1 - Blink)(1 - EyeSmile)(1 - Happy) (eye_v6_common.view_key_values)
  - mouth: Happy smiles with the line up to 0.35, then the open smile (Face_Mouth_ExSmile) grows out of it; Cry
    replaces the Sad line; Surprise shrinks the line (gone at 0.4) while the open "o" grows
  - brows are drawn over the bangs with alpha 0.8 x the strongest of Angry / Sad / Cry / Surprise / Happy / 2
"""
EYE_MESHES = ("Eye_Lids", "Eye_Lash")
EMO = ("happy", "angry", "sad", "cry", "surprise")


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def compose(st, view_fn, yaw):
    """st: dict with happy, angry, sad, cry, surprise, blink, gaze, eyesmile (old key), smile (old key)"""
    g = {k: float(st.get(k, 0.0)) for k in EMO + ("blink", "gaze", "eyesmile", "smile")}
    h, b = g["happy"], g["blink"]
    hA = h / 0.6 if h <= 0.6 else (1 - h) / 0.4
    hB = 0.0 if h <= 0.6 else (h - 0.6) / 0.4
    eye = dict(ExHappyA=hA * (1 - b), ExHappyB=hB * (1 - b), ExAngry=g["angry"] * (1 - b), ExSad=g["sad"] * (1 - b),
               ExCry=g["cry"] * (1 - b), ExSurprise=g["surprise"] * (1 - b), Blink=b, EyeSmile=g["eyesmile"], Smile=g["smile"])
    es_eff = 1 - (1 - g["eyesmile"]) * (1 - h)
    eye.update(view_fn(yaw, g["gaze"], b, es_eff))
    face = dict(ExHappy=h, ExAngry=g["angry"], ExSad=g["sad"] * (1 - g["cry"]), ExCry=g["cry"], ExSurprise=g["surprise"],
                Blink=b, EyeSmile=g["eyesmile"], Smile=g["smile"])
    mouth_open = smooth((h - 0.35) / 0.55)
    line = dict(ExHappy=min(1.0, h / 0.35), ExAngry=g["angry"], ExSad=g["sad"] * (1 - g["cry"]),
                ExCry=g["cry"], ExSurprise=min(1.0, g["surprise"] * 2.5), Smile=g["smile"])
    tear = dict(ExSad=g["sad"] * (1 - b), ExCry=g["cry"] * (1 - b), ExTearFlow=float(st.get("flow", 0.0)))
    brow_alpha = 0.8 * min(1.0, max(g["angry"], g["sad"], g["cry"], g["surprise"], 0.5 * h))
    return dict(eye=eye, face=face, line=line, tear=tear, mouth_open=mouth_open, o=g["surprise"],
                show_line=mouth_open < 0.25 and g["surprise"] < 0.4,
                show_o=g["surprise"] > 0.02, show_tear=g["cry"] * (1 - b) > 0.02, show_flow=float(st.get("flow", 0.0)) > 0.0,
                brow_alpha=brow_alpha, gaze=g["gaze"])


def lerp_state(a, b, t):
    keys = set(a) | set(b)
    return {k: (1 - t) * a.get(k, 0.0) + t * b.get(k, 0.0) for k in keys}
