"""Race3D v3b expressions (Blender, background, the .blend is not saved): renders for the checks pass.

usage: Blender -b Models/Race3D/experiments/MainGirlfriend_Race3D_v3b_Expressions.blend --python race3d_v3b_expr_render.py
       -- <job> [job ...]
jobs:  express     presets (v3 set + Happy 0.8 + Angry 2) x 0 / +-35 / +-45: face and eyes (brows: "pull")
       happy       Happy 0.6 / 0.7 / 0.8 / 0.9 / 1.0 x 0 / +-35 / +-45 (eyes) and a 0.6 -> 1 sequence at 0 and 35
       angrybrow   Angry / Angry 2 x 0 / +-35 / +-45 with the brow modes hide / over / pull
       cry         Cry 1.0 with Flow 0 / 0.25 / 0.5 / 0.75 / 1 at 0 / +35 / -35 (face and eyes)
       surprise    Surprise 0.5 / 1.0 x gaze -0.25 / 0 / +0.25 x 0 / +-35 (eyes)
       view        emotions x camera 0 / +-35 / +-45 / +-60, view keys on / off (eyes, no hair) for the far-eye check
       transition  Neutral -> Happy -> Angry -> Sad (+Cry 0.6) -> Surprise, 8 steps each, face at 0 and 35
       idcheck     eyeball flat green (hair off), closed states
Same cameras, sun and mixing as v3 (expr_mix_v3b); the eyeball sparkle is the material value "Sparkle".
Output: Models/Race3D/experiments/renders_v3b/<job>/.
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
import expr_mix_v3b as M  # noqa: E402

E = X.E
O = bpy.data.objects
JOBS = sys.argv[sys.argv.index("--") + 1:]
ROOT = os.path.join(os.path.dirname(HERE), "experiments", "renders_v3b")
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
SPARKLE = [O[f"Eye_Ball.{s}"].material_slots[0].material.node_tree.nodes["Sparkle"].outputs[0] for s in "LR"]
BROW_PULL = 0.030                     # "pull" mode: the brow card moved this far toward the camera, then depth tested
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
    view_fn = E.view_key_values if not st.get("noview") else (lambda *a: {})
    c = M.compose(st, view_fn, yaw)
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
    STREAM_FLOW.default_value = c["flow"]
    for sk in SPARKLE:
        sk.default_value = c["sparkle"]
    for o in CARDS:
        o.hide_render = True
    set_projection(c["iris_scale"], c["gaze_pitch"])
    E.set_gaze(c["gaze"])
    bpy.context.view_layer.update()
    return c


def render(path, box, yaw, scale, st, hair=True, brows_over=True, brow_mode="over"):
    """brow_mode: "hide" (bangs hide the brows, r30), "over" (card over every bang pixel: stencil + ZTest Always),
    "pull" (card moved BROW_PULL toward the camera and depth tested: only bangs close in front of the brow let it show)"""
    c = apply(st, yaw)
    for o in HAIR:
        o.hide_render = not hair
    os.makedirs(os.path.dirname(path), exist_ok=True)
    shoot(path, box, yaw, scale)
    a = c["brow_alpha"] if (hair and brows_over and brow_mode != "hide") else 0.0
    if a > 0.01:
        tmp_v, tmp_c = path[:-4] + "__vis.png", path[:-4] + "__card.png"
        saved = [[sl.material for sl in o.material_slots] for o in BROWS]
        for o in BROWS:
            for sl in o.material_slots:
                sl.material = GREEN
        shoot(tmp_v, box, yaw, scale)                       # visible plain brow pixels
        for o, mats in zip(BROWS, saved):
            for sl, m in zip(o.material_slots, mats):
                sl.material = m
        # card colour: the cards alone
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
        tmp_d = None
        if brow_mode == "pull":
            # which card pixels win the depth test once the card is pulled toward the camera (card drawn flat green)
            tmp_d = path[:-4] + "__depth.png"
            t = math.radians(yaw)
            toward = Vector((math.sin(t), -math.cos(t), 0)) * BROW_PULL
            card_mats = [[sl.material for sl in o.material_slots] for o in CARDS]
            for o in BROWS:
                o.hide_render = True
            for o in CARDS:
                o.hide_render = False
                o.location += toward
                for sl in o.material_slots:
                    sl.material = GREEN
            shoot(tmp_d, box, yaw, scale)
            for o, mats in zip(CARDS, card_mats):
                o.hide_render = True
                o.location -= toward
                for sl, m in zip(o.material_slots, mats):
                    sl.material = m
            for o in BROWS:
                o.hide_render = False
        base, vimg, card = bpy.data.images.load(path), bpy.data.images.load(tmp_v), bpy.data.images.load(tmp_c)
        P = np.array(base.pixels[:]).reshape(-1, 4)
        V = np.array(vimg.pixels[:]).reshape(-1, 4)
        C = np.array(card.pixels[:]).reshape(-1, 4)
        visible = ((V[:, 1] > 0.6) & (V[:, 0] < 0.3) & (V[:, 2] < 0.3)).astype(float)
        cov, col = C[:, 3], C[:, :3]
        if tmp_d:
            Dp = bpy.data.images.load(tmp_d)
            Dd = np.array(Dp.pixels[:]).reshape(-1, 4)
            cov = cov * ((Dd[:, 1] > 0.6) & (Dd[:, 0] < 0.3) & (Dd[:, 2] < 0.3))
            bpy.data.images.remove(Dp)
            os.remove(tmp_d)
        k = (cov * a * (1 - visible))[:, None]
        P[:, :3] = P[:, :3] * (1 - k) + col * k
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
    ("Neutral", {}), ("Happy030", {"happy": 0.3}), ("Happy060", {"happy": 0.6}), ("Happy080", {"happy": 0.8}),
    ("Happy100", {"happy": 1.0}), ("Angry100", {"angry": 1.0}), ("Angry2_100", {"angry2": 1.0}), ("Sad100", {"sad": 1.0}),
    ("Cry100", {"sad": 1.0, "cry": 1.0}), ("Surprise100", {"surprise": 1.0}),
]
if "express" in JOBS:
    d = os.path.join(ROOT, "express")
    for a in ANG:
        b = boxes(a)
        for n, st in PRESETS:
            render(os.path.join(d, f"{n}_face_{a}.png"), b["face"], a, 1.0, st, brow_mode="pull")
            render(os.path.join(d, f"{n}_eyes_{a}.png"), b["eyes"], a, 1.5, st, brow_mode="pull")
    print("JOB express done")
if "happy" in JOBS:
    d = os.path.join(ROOT, "happy")
    for a in ANG:
        b = boxes(a)
        for h in (0.6, 0.7, 0.8, 0.9, 1.0):
            render(os.path.join(d, f"Happy{int(round(h * 100)):03d}_eyes_{a}.png"), b["eyes"], a, 1.5, {"happy": h}, brow_mode="pull")
    for a in (0, 35):
        b = boxes(a)
        for k in range(17):
            h = 0.6 + 0.025 * k
            render(os.path.join(d, "seq", f"s{a}_{k:02d}.png"), b["eyes"], a, 0.8, {"happy": h}, brow_mode="pull")
    print("JOB happy done")
if "angrybrow" in JOBS:
    d = os.path.join(ROOT, "angrybrow")
    for a in ANG:
        b = boxes(a)
        for n, st in (("Angry100", {"angry": 1.0}), ("Angry2_100", {"angry2": 1.0})):
            for mode in ("hide", "over", "pull"):
                render(os.path.join(d, f"{n}_{mode}_eyes_{a}.png"), b["eyes"], a, 1.5, st, brow_mode=mode)
            render(os.path.join(d, f"{n}_pull_face_{a}.png"), b["face"], a, 1.0, st, brow_mode="pull")
    print("JOB angrybrow done")
if "cry" in JOBS:
    d = os.path.join(ROOT, "cry")
    for a in (0, 35, -35):
        b = boxes(a)
        for fl in (0.0, 0.25, 0.5, 0.75, 1.0):
            render(os.path.join(d, f"Flow{int(fl * 100):03d}_face_{a}.png"), b["face"], a, 1.0, {"sad": 1.0, "cry": 1.0, "flow": fl}, brow_mode="pull")
        render(os.path.join(d, f"Flow100_eyes_{a}.png"), b["eyes"], a, 1.5, {"sad": 1.0, "cry": 1.0, "flow": 1.0}, brow_mode="pull")
    print("JOB cry done")
if "surprise" in JOBS:
    d = os.path.join(ROOT, "surprise")
    for a in (0, 35, -35):
        b = boxes(a)
        for sv in (0.5, 1.0):
            for gz in (-0.25, 0.0, 0.25):
                render(os.path.join(d, f"S{int(sv * 100):03d}_g{gz:+.2f}_eyes_{a}.png"), b["eyes"], a, 1.5,
                       {"surprise": sv, "gaze": gz}, brow_mode="pull")
    print("JOB surprise done")
if "view" in JOBS:
    d = os.path.join(ROOT, "view")
    for a in (0, 35, -35, 45, -45, 60, -60):
        b = boxes(a)
        for n, st in (("Neutral", {}), ("Happy060", {"happy": 0.6}), ("Angry100", {"angry": 1.0}), ("Sad100", {"sad": 1.0}),
                      ("Cry100", {"sad": 1.0, "cry": 1.0}), ("Surprise100", {"surprise": 1.0}),
                      ("Surprise100_gR", {"surprise": 1.0, "gaze": -0.25}), ("Angry100_b05", {"angry": 1.0, "blink": 0.5})):
            for view in (True, False):
                st2 = dict(st, noview=not view)
                render(os.path.join(d, f"{n}_{'view' if view else 'noview'}_{a}.png"), b["eyes"], a, 1.5, st2, hair=False)
    print("JOB view done")
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
            render(os.path.join(d, f"t{a}_{f:02d}.png"), b["face"], a, 0.8, st, brow_mode="pull")
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
    cases = [("Blink100", {"blink": 1.0}), ("Happy100", {"happy": 1.0}), ("Happy095", {"happy": 0.95}),
             ("Happy100_Blink050", {"happy": 1.0, "blink": 0.5}), ("Angry2_100_Blink100", {"angry2": 1.0, "blink": 1.0}),
             ("Cry100_Blink100", {"sad": 1.0, "cry": 1.0, "blink": 1.0}), ("Surprise100_Blink100", {"surprise": 1.0, "blink": 1.0})]
    for a in ANG:
        b = boxes(a)
        for n, st in cases:
            render(os.path.join(d, f"{n}_{a}.png"), b["eyes"], a, 1.5, st, hair=False)
    for name, mats in saved.items():
        for sl, m in zip(O[name].material_slots, mats):
            sl.material = m
    print("JOB idcheck done")
