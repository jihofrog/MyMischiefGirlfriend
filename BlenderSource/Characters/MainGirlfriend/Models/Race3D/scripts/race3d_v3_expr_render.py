"""Race3D v3 expressions (Blender, background, the .blend is not saved): renders of the second-pass expressions.

v3 on top of the v2 renderer: eyeball projection per state (iris scale for Surprise, a little upward gaze for Angry),
eye sparkles, tear bead / stream with the "Flow" reveal value, brows over the bangs from the brow cards
(Face_BrowCard.<s>: shown where the bangs hide the plain brow - found with a pass of flat green brows -, alpha from
compose()).
usage: Blender -b Models/Race3D/experiments/MainGirlfriend_Race3D_v3_Expressions.blend --python race3d_v3_expr_render.py
       -- <job> [job ...]
jobs:  compare     current EyeSmile vs the new Happy eyes (same cameras), both eyes x1.5, 0 / +-35 / +-45
       express     every preset: face x1, eyes + brows x1.5, mouth x4 at 0 / +-35 / +-45
       transition  Neutral -> Happy -> Angry -> Sad -> Surprise, 8 steps each, face at 0 and 35
       idcheck     eyeball drawn flat green (hair off): closed smile / blink combinations, for the exposure count
       flow        Cry with the stream mask Flow = 0 / 0.25 / 0.5 / 0.75 / 1 (face at 0 and 35)
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
import expr_mix_v3 as M  # noqa: E402

E = X.E
O = bpy.data.objects
JOBS = sys.argv[sys.argv.index("--") + 1:]
ROOT = os.path.join(os.path.dirname(HERE), "experiments", "renders_v3")
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
CARDS = [O["Face_BrowCard.L"], O["Face_BrowCard.R"]]
SPARKS = [O["Eye_Sparkle.L"], O["Eye_Sparkle.R"]]
STREAM_FLOW = bpy.data.materials["M_TearStream"].node_tree.nodes["Flow"].outputs[0]


def ball_projection(s):
    """the two MULTIPLY_ADD nodes of the eyeball material (u = X su + tu, v = Z sv + tv) and the iris centre in uv"""
    ob = O[f"Eye_Ball.{s}"]
    m = ob.material_slots[0].material
    nodes = {}
    for l in m.node_tree.links:
        if l.from_node.type == "SEPXYZ" and l.to_node.type == "MATH" and l.to_node.operation == "MULTIPLY_ADD":
            nodes[l.from_socket.name] = l.to_node
    nu, nv = nodes["X"], nodes["Z"]
    base = (nu.inputs[1].default_value, nu.inputs[2].default_value, nv.inputs[1].default_value, nv.inputs[2].default_value)
    ib = E.TGT[s]["iris_bbox"]
    c = ob.matrix_world.inverted() @ Vector((float(E.X((ib[0] + ib[2]) / 2)), 0.0, float(E.Z((ib[1] + ib[3]) / 2))))
    uc, vc = c.x * base[0] + base[1], c.z * base[2] + base[3]
    return nu, nv, base, (uc, vc)


PROJ = {s: ball_projection(s) for s in "LR"}
GREEN = bpy.data.materials.new("EX_BrowVisible")
GREEN.use_nodes = True
GREEN.node_tree.nodes.clear()
_em = GREEN.node_tree.nodes.new("ShaderNodeEmission")
_em.inputs["Color"].default_value = (0, 1, 0, 1)
GREEN.node_tree.links.new(_em.outputs[0], GREEN.node_tree.nodes.new("ShaderNodeOutputMaterial").inputs[0])


def set_projection(scale, pitch):
    """iris drawn smaller by `scale` about its centre, moved up by `pitch` metres"""
    for s, (nu, nv, (su, tu, sv, tv), (uc, vc)) in PROJ.items():
        nu.inputs[1].default_value = su / scale
        nu.inputs[2].default_value = (tu - uc) / scale + uc
        nv.inputs[1].default_value = sv / scale
        nv.inputs[2].default_value = (tv - vc) / scale + vc - pitch * sv / scale
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
        elif n.startswith("Eye_Sparkle"):
            set_keys(o, {"ExSurprise": c["sparkle"]})
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
    STREAM_FLOW.default_value = c["flow"]
    for o in SPARKS:
        o.hide_render = c["sparkle"] <= 0.02
    for o in CARDS:
        o.hide_render = True
    set_projection(c["iris_scale"], c["gaze_pitch"])
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
        # brows over the bangs: the brow card is laid (alpha a) where the brow exists but the bangs hide it. Visible
        # brow pixels come from a pass with the brows flat green (the brow and hair colours are nearly the same)
        tmp_v, tmp_c = path[:-4] + "__vis.png", path[:-4] + "__card.png"
        saved = [[sl.material for sl in o.material_slots] for o in BROWS]
        for o in BROWS:
            for sl in o.material_slots:
                sl.material = GREEN
        shoot(tmp_v, box, yaw, scale)
        for o, mats in zip(BROWS, saved):
            for sl, m in zip(o.material_slots, mats):
                sl.material = m
        vis = [o for o in O if o.type in ("MESH", "CURVE") and not o.hide_render]
        for o in vis:
            o.hide_render = True
        for o in CARDS:
            o.hide_render = False
        shoot(tmp_c, box, yaw, scale)
        for o in CARDS:
            o.hide_render = True
        for o in vis:
            o.hide_render = False
        base, vimg, card = bpy.data.images.load(path), bpy.data.images.load(tmp_v), bpy.data.images.load(tmp_c)
        P = np.array(base.pixels[:]).reshape(-1, 4)
        V = np.array(vimg.pixels[:]).reshape(-1, 4)
        C = np.array(card.pixels[:]).reshape(-1, 4)
        visible = ((V[:, 1] > 0.6) & (V[:, 0] < 0.3) & (V[:, 2] < 0.3)).astype(float)
        k = (C[:, 3] * a * (1 - visible))[:, None]
        P[:, :3] = P[:, :3] * (1 - k) + C[:, :3] * k
        base.pixels[:] = P.ravel()
        base.filepath_raw = path
        base.file_format = "PNG"
        base.save()
        for im in (base, vimg, card):
            bpy.data.images.remove(im)
        os.remove(tmp_v)
        os.remove(tmp_c)
    return c


ANG = (0, 35, -35, 45, -45)
PRESETS = [
    ("Neutral", {}),
    ("Happy030", {"happy": 0.3}), ("Happy060", {"happy": 0.6}), ("Happy080", {"happy": 0.8}), ("Happy100", {"happy": 1.0}),
    ("Angry100", {"angry": 1.0}), ("Sad100", {"sad": 1.0}), ("Cry100", {"sad": 1.0, "cry": 1.0}),
    ("Surprise100", {"surprise": 1.0}),
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
    # Cry with the stream revealed step by step (the "Flow" mask value of M_TearStream)
    d = os.path.join(ROOT, "flow")
    for a in (0, 35):
        b = boxes(a)
        for fl in (0.0, 0.25, 0.5, 0.75, 1.0):
            render(os.path.join(d, f"CryFlow{int(fl * 100):03d}_face_{a}.png"), b["face"], a, 1.0, {"sad": 1.0, "cry": 1.0, "flow": fl})
    print("JOB flow done")
