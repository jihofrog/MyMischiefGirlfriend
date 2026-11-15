"""ToonTest_01 step 48 (Blender, background, the .blend is not saved): v6f renders, both eyes measured separately.

usage: Blender -b <file.blend> --python t48_eye_v6f_render.py -- <tag> [quick]
Same orthographic camera / sun as t03 (the light turns with the camera). Angles 0, +-35, +-45, +-60, +-90
(+ = camera toward the character's left: L is the near eye, R the far eye). renders/<tag>_f6_*.png:
  face_<a>, facenh_<a>      whole face with / without hair (x1)
  <s>_toon_<a>              eye <s> (L / R), no hair, toon (x4, 240 x 170 px box on the projected eye centre)
  <s>_hair_<a>              the same with hair
  <s>_id_<a>                the same, flat colours (t46 colours: skin grey, upper lid sheet blue / skirt cyan, lower lid
                            sheet violet / skirt pink, eyeball green, lash band red, lash skirt orange, lower lash
                            yellow, crease white; back faces at 35 %)
  expr_<pose>_<a>           a = 0, +35, -35: both eyes with hair (x1.4): Neutral, Blink50, Blink, EyeSmile,
                            SmileEyeSmile, Surprise, GazeL, GazeR (0.15 rad), GazeLmax, GazeRmax (0.25 rad: the
                            iris edge reaches the outer corner)
With pose=<key> (e.g. pose=EyeSmile): only <s>_toon_<key>_<a> and <s>_id_<key>_<a> at 0, +-35 in that key; gaze=<name>:<rad>
(e.g. gaze=GazeLmax:0.25) the same with that gaze (suffix _<name>).
Env ANGLES=<a,a,...> replaces the angle list; VIEWKEY=1 sets the ViewFar keys (t72) from the angle, gaze, Blink and EyeSmile of every shot
(eye_v6_common.view_key_values); VIEWRAW=1 with it: angle only (limit test).
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
tag = args[0]
quick = "quick" in args
POSE = next((a.split("=", 1)[1] for a in args if a.startswith("pose=")), None)   # pose=<key>: only toon + id close ups in that key
GZ = next((a.split("=", 1)[1] for a in args if a.startswith("gaze=")), None)    # gaze=<name>:<rad>: the same with that gaze
SUF = (f"_{POSE}" if POSE else "") + (f"_{GZ.split(':')[0]}" if GZ else "")
sys.argv = [sys.argv[0], "--", tag]
p = os.path.join(HERE, "t03_render.py")
g = {"__file__": p, "__name__": "f6"}
exec(open(p).read().split("FACE = (700")[0], g)
O = bpy.data.objects
AXY = 0.03
ANG = (0, 35, -35, 45, -45, 60, -60, 90, -90) if not quick else (35, -35, 45, -45)
if os.environ.get("ANGLES"):                     # e.g. ANGLES=0,15,-15,25,-25
    ANG = tuple(int(v) for v in os.environ["ANGLES"].split(","))
VIEW = os.environ.get("VIEWKEY") == "1"          # v6i: ViewFarL / ViewFarR from the camera angle (E.view_far_weights)
HAIR = [o for o in O if (o.name.startswith("hair_bob_01") or o.name.startswith("acc_head_hairclip")) and not o.hide_render]


def centre(s):
    ib = E.TGT[s]["iris_bbox"]
    x, z = float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2))
    y, _ = E.front_hit(E.bvh_of([f"Eye_Ball.{s}"]), x, z)
    return x, y, z


C = {s: centre(s) for s in "LR"}


def px_of(s, a):
    x, y, z = C[s]
    t = math.radians(a)
    return 1030 + E.PPM * (x * math.cos(t) + (y - AXY) * math.sin(t)), float(E.PY(z))


def ebox(s, a):
    cx, cy = px_of(s, a)
    return (int(cx - 120), int(cy - 85), int(cx + 120), int(cy + 85))


def hair(show):
    for o in HAIR:
        o.hide_render = not show


def keys(w):
    for o in O:
        if o.type == "MESH" and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks[1:]:
                k.value = w.get(k.name, 0.0)
    bpy.context.view_layer.update()


def shoot(name, b, a, sc=1.0):
    if VIEW:
        kb = O["Eye_Lids.L"].data.shape_keys.key_blocks
        gz = next(m.node_tree.nodes["Gaze"].outputs[0].default_value for m in bpy.data.materials
                  if m.node_tree and "Gaze" in m.node_tree.nodes)
        raw = os.environ.get("VIEWRAW") == "1"   # limit test: no Blink / EyeSmile scaling, no gaze keys
        vw = E.view_key_values(a, 0.0 if raw else gz, 0.0 if raw else kb["Blink"].value, 0.0 if raw else kb["EyeSmile"].value)
        for o in O:
            if o.type == "MESH" and o.data.shape_keys:
                for k in o.data.shape_keys.key_blocks[1:]:
                    if k.name in vw:
                        k.value = vw[k.name]
        bpy.context.view_layer.update()
    g["shoot"]("f6_" + name, b, a, sc)


keys({POSE: 1.0} if POSE else {})
E.set_gaze(float(GZ.split(":")[1]) if GZ else 0)
POSE = POSE or GZ
if POSE:
    ANG = (0, 35, -35)
for a in ANG:
    if POSE:
        hair(False)
        for s in "LR":
            shoot(f"{s}_toon{SUF}_{a}", ebox(s, a), a, 4.0)
        continue
    hair(True)
    if not quick:
        shoot(f"face_{a}", (600, 0, 1460, 860), a)
    for s in "LR":
        shoot(f"{s}_hair_{a}", ebox(s, a), a, 4.0)
    hair(False)
    if not quick:
        shoot(f"facenh_{a}", (600, 0, 1460, 860), a)
    for s in "LR":
        shoot(f"{s}_toon_{a}", ebox(s, a), a, 4.0)
hair(True)
POSES = (("Neutral", {}, 0), ("Blink50", {"Blink": 0.5}, 0), ("Blink", {"Blink": 1.0}, 0), ("EyeSmile", {"EyeSmile": 1.0}, 0),
         ("SmileEyeSmile", {"Smile": 1.0, "EyeSmile": 1.0}, 0), ("Surprise", {"Surprise": 1.0}, 0),
         ("GazeL", {}, 0.15), ("GazeR", {}, -0.15), ("GazeLmax", {}, 0.25), ("GazeRmax", {}, -0.25))
if not quick and not POSE:
    for a in (0, 35, -35):
        xl, yl = px_of("L", a)
        xr, yr = px_of("R", a)
        b = (int((xl + xr) / 2 - 280), int((yl + yr) / 2 - 110), int((xl + xr) / 2 + 280), int((yl + yr) / 2 + 150))
        for pn, w, gz in POSES:
            keys(w)
            E.set_gaze(gz)
            shoot(f"expr_{pn}_{a}", b, a, 1.4)
    keys({})
    E.set_gaze(0)

# ------------------------------------------------------------------ flat colour ids (no hair)
hair(False)
COL = dict(skin=(0.6, 0.6, 0.6), up=(0.1, 0.25, 1.0), upsk=(0.0, 0.9, 1.0), lo=(0.55, 0.2, 0.9), losk=(1.0, 0.45, 0.75),
           ball=(0.1, 0.85, 0.2), lash=(0.9, 0.05, 0.05), lashsk=(1.0, 0.5, 0.0), lowlash=(1.0, 0.95, 0.0),
           crease=(1.0, 1.0, 1.0), other=(0.25, 0.25, 0.25))


def id_mat(key, tex=None):
    m = bpy.data.materials.new(f"F6_{key}")
    m.use_nodes = True
    m.blend_method = "HASHED" if tex else "OPAQUE"
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    c = COL[key]
    mix.inputs[6].default_value = (*c, 1)
    mix.inputs[7].default_value = (c[0] * 0.35, c[1] * 0.35, c[2] * 0.35, 1)
    nt.links.new(geo.outputs["Backfacing"], mix.inputs[0])
    nt.links.new(mix.outputs[2], em.inputs["Color"])
    if tex is None:
        nt.links.new(em.outputs[0], out.inputs[0])
        return m
    ti = nt.nodes.new("ShaderNodeTexImage")
    ti.image = tex
    nt.links.new(nt.nodes.new("ShaderNodeUVMap").outputs[0], ti.inputs[0])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    ms = nt.nodes.new("ShaderNodeMixShader")
    gt = nt.nodes.new("ShaderNodeMath")
    gt.operation = "GREATER_THAN"
    gt.inputs[1].default_value = 0.5
    nt.links.new(ti.outputs["Alpha"], gt.inputs[0])
    nt.links.new(gt.outputs[0], ms.inputs[0])
    nt.links.new(tr.outputs[0], ms.inputs[1])
    nt.links.new(em.outputs[0], ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs[0])
    return m


for o in O:
    if hasattr(o, "modifiers") and "TT_Outline" in o.modifiers:
        o.modifiers["TT_Outline"].show_render = False
vis = [o for o in O if o.type in ("MESH", "CURVE") and not o.hide_render and o.visible_get()]
for o in vis:
    if o.name.startswith("Face_Blush"):
        o.hide_render = True
M = {k: id_mat(k) for k in COL}
for o in vis:
    n = o.name
    if o.type != "MESH":
        for s_ in o.material_slots:
            s_.material = M["other"]
        continue
    me = o.data
    if n.startswith("Eye_Lids"):
        nc = len(me.vertices) // 14
        me.materials.clear()
        for k in ("up", "upsk", "lo", "losk"):
            me.materials.append(M[k])
        for f in me.polygons:
            vs = list(f.vertices)
            f.material_index = (2 if min(vs) >= nc * 7 else 0) + (1 if min(v % 7 for v in vs) == 0 else 0)
    elif n.startswith("Eye_Lash"):
        nb, nr, cs = int(o["mmg_band_cols"]), int(o["mmg_band_rows"]), int(o["mmg_crease_start"])
        img = next(nd.image for nd in o.material_slots[0].material.node_tree.nodes if nd.type == "TEX_IMAGE" and nd.image)
        me.materials.clear()
        for k in ("lash", "lashsk", "lowlash", "crease"):
            me.materials.append(id_mat(k, img) if k in ("lash", "lowlash") else M[k])
        for f in me.polygons:
            vs = list(f.vertices)
            f.material_index = (3 if min(vs) >= cs else 2 if min(vs) >= nb * nr else 1 if min(v % nr for v in vs) == 0 else 0)
    else:
        key = ("ball" if n.startswith("Eye_Ball") else "skin" if n.startswith(("Blockout_Head", "Face_Ear", "Eye_TailWrap")) else "other")
        for s_ in o.material_slots:
            s_.material = M[key]
for a in ANG:
    for s in "LR":
        shoot(f"{s}_id{SUF}_{a}", ebox(s, a), a, 4.0)
print("F6_RENDER_DONE", tag)
