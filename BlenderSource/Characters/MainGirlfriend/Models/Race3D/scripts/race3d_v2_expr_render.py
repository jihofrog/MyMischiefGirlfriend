"""Race3D v2 expressions (Blender, background, the .blend is not saved): renders of the prototype expressions.

usage: Blender -b Models/Race3D/experiments/MainGirlfriend_Race3D_v2_Expressions.blend --python race3d_v2_expr_render.py
       -- <job> [job ...]
jobs:  compare     current EyeSmile vs the new Happy eyes (same cameras), both eyes x1.5, 0 / +-35 / +-45
       express     every preset: face x1, eyes + brows x1.5, mouth x4 at 0 / +-35 / +-45
       transition  Neutral -> Happy -> Angry -> Sad -> Surprise, 8 steps each, face at 0 and 35
       idcheck     eyeball drawn flat green (hair off): closed smile / blink combinations, for the exposure count
       flow        Cry with the cheek stream shown (structure demo)
Same orthographic camera and sun as t03 / t48 (the sun turns with the camera); view-angle keys follow the angle
(expr_mix.compose). Where the bangs cover a brow it is composited over them, darker, with the alpha of compose(). Output:
Models/Race3D/experiments/renders/<job>/<name>.png (transparent background).
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import expr_common as X  # noqa: E402
import expr_mix as M  # noqa: E402

E = X.E
O = bpy.data.objects
JOBS = sys.argv[sys.argv.index("--") + 1:]
ROOT = os.path.join(os.path.dirname(HERE), "experiments", "renders")
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
try:
    sc.eevee.taa_render_samples = 32
except Exception:
    pass
sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
cam_data = bpy.data.cameras.new("EX_Cam")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("EX_Cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
sun = O.get("TT_Sun")
for o in O:
    md = o.modifiers.get("TT_Outline") if hasattr(o, "modifiers") else None
    if md:
        md.show_render = True
AXY = 0.03
HAIR = [o for o in O if (o.name.startswith("hair_bob_01") or o.name.startswith("acc_head_hairclip")) and not o.hide_render]
BROWS = [O["Face_Brow.L"], O["Face_Brow.R"]]
SMILE_MOUTH = [o for o in O if o.name.startswith("Face_Mouth_Smile_")]
LINE = O["TT_Mouth_Closed"]
OMOUTH = O["Face_Mouth_ExO"]
SMOUTH = O["Face_Mouth_ExSmile"]
TEARS = [O["Face_Tear.L"], O["Face_Tear.R"]]
STREAMS = [O["Face_TearStream.L"], O["Face_TearStream.R"]]


def x_px(p, a):
    t = math.radians(a)
    return 1030 + E.PPM * (p[0] * math.cos(t) + (p[1] - AXY) * math.sin(t)), float(E.PY(p[2]))


def eye_centre(s):
    ib = E.TGT[s]["iris_bbox"]
    x, z = float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2))
    y, _ = E.front_hit(E.bvh_of([f"Eye_Ball.{s}"]), x, z)
    return x, y, z


EC = {s: eye_centre(s) for s in "LR"}
MC = tuple(X.world(LINE).mean(0))


def boxes(a):
    (xl, yl), (xr, yr) = x_px(EC["L"], a), x_px(EC["R"], a)
    cx, cy = (xl + xr) / 2, (yl + yr) / 2
    mx, my = x_px(MC, a)
    return dict(face=(int(cx - 300), int(cy - 230), int(cx + 300), int(cy + 270)),
                eyes=(int(cx - 290), int(cy - 175), int(cx + 290), int(cy + 135)),
                mouth=(int(mx - 55), int(my - 40), int(mx + 55), int(my + 40)))


def shoot(path, box, yaw, scale):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    sc.render.resolution_x, sc.render.resolution_y = int(w * scale), int(h * scale)
    sc.render.resolution_percentage = 100
    cam_data.ortho_scale = max(w, h) / E.PPM
    cx, cz = E.X((x0 + x1) / 2), E.Z((y0 + y1) / 2)
    t = math.radians(yaw)
    view = Vector((-math.sin(t), math.cos(t), 0))
    right = Vector((math.cos(t), math.sin(t), 0))
    cam.location = Vector((0, AXY, float(cz))) - 3.0 * view + float(cx) * right
    cam.rotation_euler = (math.radians(90), 0, t)
    if sun is not None:
        sun.rotation_euler = (math.radians(60), 0, math.radians(-20) + t)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def set_keys(o, vals):
    if o.type == "MESH" and o.data.shape_keys:
        for k in o.data.shape_keys.key_blocks[1:]:
            k.value = float(vals.get(k.name, 0.0))


def apply(st, yaw):
    c = M.compose(st, E.view_key_values, yaw)
    for o in O:
        if o.type != "MESH":
            continue
        n = o.name
        if n.startswith(M.EYE_MESHES):
            set_keys(o, c["eye"])
        elif n == "TT_Mouth_Closed":
            set_keys(o, c["line"])
        elif n.startswith("Face_Mouth_Smile_"):
            set_keys(o, {})
        elif n == "Face_Mouth_ExSmile":
            set_keys(o, {"ExHappy": c["mouth_open"]})
        elif n == "Face_Mouth_ExO":
            set_keys(o, {"ExSurprise": c["o"]})
        elif n.startswith(("Face_Tear", "Face_TearStream")):
            set_keys(o, c["tear"])
        else:
            set_keys(o, c["face"])
    for o in SMILE_MOUTH:
        o.hide_render = True
    SMOUTH.hide_render = c["mouth_open"] <= 0.02
    LINE.hide_render = not c["show_line"]
    OMOUTH.hide_render = not c["show_o"]
    for o in TEARS:
        o.hide_render = not c["show_tear"]
    for o in STREAMS:
        o.hide_render = not c["show_flow"]
    E.set_gaze(c["gaze"])
    bpy.context.view_layer.update()
    return c


def render(path, box, yaw, scale, st, hair=True, brows_over=True):
    c = apply(st, yaw)
    for o in HAIR:
        o.hide_render = not hair
    os.makedirs(os.path.dirname(path), exist_ok=True)
    shoot(path, box, yaw, scale)
    a = c["brow_alpha"] if (hair and brows_over) else 0.0
    if a > 0.01:
        # brows over the bangs: brows alone, composited with alpha a
        vis = [o for o in O if o.type in ("MESH", "CURVE") and not o.hide_render and o not in BROWS]
        for o in vis:
            o.hide_render = True
        tmp = path[:-4] + "__brow.png"
        shoot(tmp, box, yaw, scale)
        for o in vis:
            o.hide_render = False
        base, top = bpy.data.images.load(path), bpy.data.images.load(tmp)
        P = np.array(base.pixels[:]).reshape(-1, 4)
        T = np.array(top.pixels[:]).reshape(-1, 4)
        # only where something (the bangs) covers the brow; there in a darker brow colour (hair is the same brown)
        hidden = (np.abs(P[:, :3] - T[:, :3]).max(1) > 0.06).astype(float)
        k = (T[:, 3] * a * hidden)[:, None]
        P[:, :3] = P[:, :3] * (1 - k) + T[:, :3] * 0.62 * k
        P[:, 3] = np.maximum(P[:, 3], T[:, 3] * a)
        base.pixels[:] = P.ravel()
        base.filepath_raw = path
        base.file_format = "PNG"
        base.save()
        bpy.data.images.remove(base)
        bpy.data.images.remove(top)
        os.remove(tmp)
    return c


ANG = (0, 35, -35, 45, -45)
PRESETS = [
    ("Neutral", {}),
    ("Happy030", {"happy": 0.3}), ("Happy060", {"happy": 0.6}), ("Happy100", {"happy": 1.0}),
    ("Angry050", {"angry": 0.5}), ("Angry100", {"angry": 1.0}),
    ("Sad050", {"sad": 0.5}), ("Sad100", {"sad": 1.0}),
    ("Cry050", {"sad": 1.0, "cry": 0.5}), ("Cry100", {"sad": 1.0, "cry": 1.0}),
    ("Surprise050", {"surprise": 0.5}), ("Surprise100", {"surprise": 1.0}),
]
log = {}
if "compare" in JOBS:
    d = os.path.join(ROOT, "compare")
    cases = [("OldEyeSmile050", {"eyesmile": 0.5}), ("OldEyeSmile100", {"eyesmile": 1.0}),
             ("NewHappy030", {"happy": 0.3}), ("NewHappy060", {"happy": 0.6}), ("NewHappy100", {"happy": 1.0})]
    for a in ANG:
        b = boxes(a)
        for n, st in cases:
            st = dict(st)
            if n.startswith("New"):
                # eyes, brows, cheeks only: the mouth stays neutral like the old EyeSmile
                c = apply(st, a)
            render(os.path.join(d, f"{n}_{a}.png"), b["eyes"], a, 1.5, st, brows_over=False)
            if n.startswith("New"):
                pass
    print("JOB compare done")
if "express" in JOBS:
    d = os.path.join(ROOT, "express")
    for a in ANG:
        b = boxes(a)
        for n, st in PRESETS:
            render(os.path.join(d, f"{n}_face_{a}.png"), b["face"], a, 1.0, st)
            render(os.path.join(d, f"{n}_eyes_{a}.png"), b["eyes"], a, 1.5, st)
            render(os.path.join(d, f"{n}_mouth_{a}.png"), b["mouth"], a, 4.0, st)
    print("JOB express done")
if "transition" in JOBS:
    d = os.path.join(ROOT, "transition")
    seq = [{}, {"happy": 1.0}, {"angry": 1.0}, {"sad": 1.0, "cry": 0.6}, {"surprise": 1.0}]
    frames = []
    for i in range(len(seq) - 1):
        for k in range(8):
            frames.append(M.lerp_state(seq[i], seq[i + 1], k / 8))
    frames.append(seq[-1])
    for a in (0, 35):
        b = boxes(a)
        for f, st in enumerate(frames):
            render(os.path.join(d, f"t{a}_{f:02d}.png"), b["face"], a, 0.8, st)
    json.dump(frames, open(os.path.join(d, "frames.json"), "w"), indent=1)
    print("JOB transition done", len(frames))
if "idcheck" in JOBS:
    d = os.path.join(ROOT, "idcheck")
    green = bpy.data.materials.new("EX_ID_Green")
    green.use_nodes = True
    nt = green.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0, 1, 0, 1)
    nt.links.new(em.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs[0])
    saved = {}
    for s in "LR":
        ob = O[f"Eye_Ball.{s}"]
        saved[ob.name] = [sl.material for sl in ob.material_slots]
        for sl in ob.material_slots:
            sl.material = green
    cases = [("Blink100", {"blink": 1.0}), ("Happy100", {"happy": 1.0}), ("Happy090", {"happy": 0.9}),
             ("Happy100_Blink050", {"happy": 1.0, "blink": 0.5}), ("Angry100_Blink100", {"angry": 1.0, "blink": 1.0}),
             ("Cry100_Blink100", {"sad": 1.0, "cry": 1.0, "blink": 1.0}), ("Surprise100_Blink100", {"surprise": 1.0, "blink": 1.0})]
    for a in ANG:
        b = boxes(a)
        for n, st in cases:
            render(os.path.join(d, f"{n}_{a}.png"), b["eyes"], a, 1.5, st, hair=False)
    for name, mats in saved.items():
        for sl, m in zip(O[name].material_slots, mats):
            sl.material = m
    print("JOB idcheck done")
if "flow" in JOBS:
    d = os.path.join(ROOT, "flow")
    for a in (0, 35):
        b = boxes(a)
        render(os.path.join(d, f"CryFlow_face_{a}.png"), b["face"], a, 1.0, {"sad": 1.0, "cry": 1.0, "flow": 1.0})
        render(os.path.join(d, f"CryFlow_eyes_{a}.png"), b["eyes"], a, 1.5, {"sad": 1.0, "cry": 1.0, "flow": 1.0})
    print("JOB flow done")
