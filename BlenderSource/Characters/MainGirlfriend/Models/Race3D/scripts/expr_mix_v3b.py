"""Race3D v3b expression mixing rules (v3 + Happy stage C at 0.85, the Angry 2 candidate "angry2", the sparkle as an
eyeball texture layer "Sparkle" instead of meshes).

Race3D v3 expression mixing rules (pure python): emotion intensities (0..1) -> shape key values and material values.

v3 additions to the v2 rules (expr_mix.py):
  - material values: iris scale 1 - 0.08 Surprise (eyeball projection about the iris centre), gaze pitch +0.8 mm x Angry
    (the eyeball texture moves up a little), sparkle key = Surprise, tear stream reveal "Flow" (default 0.5 x Cry)
  - tears show from Sad (thin wet line) and Cry (bead + stream); hidden while Blink closes the eye
  - brow cards (over the bangs) instead of the plain brows for the over-hair pass

Same rules a Unity driver would follow:
  - Happy is staged on the eyes: 0..0.6 crescent (ExHappyA), 0.6..1 crescent -> closed smile (ExHappyB)
  - eye emotion keys scale by (1 - Blink): Blink always wins and never closes past 100 %
  - view-angle keys scale by (1 - Blink)(1 - EyeSmile)(1 - Happy) (eye_v6_common.view_key_values)
  - mouth: Happy smiles with the line up to 0.35, then the open smile (Face_Mouth_ExSmile) grows out of it; Cry
    replaces the Sad line; Surprise shrinks the line (gone at 0.4) while the open "o" grows
  - brows are drawn over the bangs with alpha 0.8 x the strongest of Angry / Sad / Cry / Surprise / Happy / 2
"""
EYE_MESHES = ("Eye_Lids", "Eye_Lash")
EMO = ("happy", "angry", "angry2", "sad", "cry", "surprise")


def happy_stages(h):
    """Happy -> (A, C, B): 0..0.6 A, 0.6..0.85 A -> C, 0.85..1 C -> B"""
    if h <= 0.6:
        return h / 0.6, 0.0, 0.0
    if h <= 0.85:
        t = (h - 0.6) / 0.25
        return 1 - t, t, 0.0
    t = (h - 0.85) / 0.15
    return 0.0, 1 - t, t


def smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def compose(st, view_fn, yaw):
    """st: dict with happy, angry, sad, cry, surprise, blink, gaze, eyesmile (old key), smile (old key)"""
    g = {k: float(st.get(k, 0.0)) for k in EMO + ("blink", "gaze", "eyesmile", "smile")}
    h, b = g["happy"], g["blink"]
    hA, hC, hB = happy_stages(h)
    eye = dict(ExHappyA=hA * (1 - b), ExHappyC=hC * (1 - b), ExHappyB=hB * (1 - b), ExAngry=g["angry"] * (1 - b),
               ExAngry2=g["angry2"] * (1 - b), ExSad=g["sad"] * (1 - b),
               ExCry=g["cry"] * (1 - b), ExSurprise=g["surprise"] * (1 - b), Blink=b, EyeSmile=g["eyesmile"], Smile=g["smile"])
    es_eff = 1 - (1 - g["eyesmile"]) * (1 - h)
    eye.update(view_fn(yaw, g["gaze"], b, es_eff))
    face = dict(ExHappy=h, ExAngry=g["angry"], ExAngry2=g["angry2"], ExSad=g["sad"] * (1 - g["cry"]), ExCry=g["cry"], ExSurprise=g["surprise"],
                Blink=b, EyeSmile=g["eyesmile"], Smile=g["smile"])
    mouth_open = smooth((h - 0.35) / 0.55)
    line = dict(ExHappy=min(1.0, h / 0.35), ExAngry=g["angry"] + g["angry2"], ExSad=g["sad"] * (1 - g["cry"]),
                ExCry=g["cry"], ExSurprise=min(1.0, g["surprise"] * 2.5), Smile=g["smile"])
    tear = dict(ExSad=g["sad"] * (1 - b), ExCry=g["cry"] * (1 - b))
    flow = float(st.get("flow", 0.5 * g["cry"]))
    brow_alpha = 0.8 * min(1.0, max(g["angry"], g["angry2"], g["sad"], g["cry"], g["surprise"], 0.5 * h))
    return dict(eye=eye, face=face, line=line, tear=tear, mouth_open=mouth_open, o=g["surprise"],
                show_line=mouth_open < 0.25 and g["surprise"] < 0.4,
                show_o=g["surprise"] > 0.02, show_tear=max(g["sad"], g["cry"]) * (1 - b) > 0.05,
                show_flow=flow * (1 - b) > 0.02 and g["cry"] > 0.05, flow=flow,
                sparkle=g["surprise"] * (1 - b), iris_scale=1.0 - 0.08 * g["surprise"], gaze_pitch=0.0008 * g["angry"] + 0.0010 * g["angry2"],
                brow_alpha=brow_alpha, gaze=g["gaze"])


def lerp_state(a, b, t):
    keys = set(a) | set(b)
    return {k: (1 - t) * a.get(k, 0.0) + t * b.get(k, 0.0) for k in keys}
