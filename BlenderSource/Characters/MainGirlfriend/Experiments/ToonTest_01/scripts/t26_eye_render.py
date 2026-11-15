"""ToonTest_01 step 26 (Blender, background, the .blend is not saved): eye renders for one variant (v5g, v6a, v6b).

usage: Blender -b <file.blend> --python t26_eye_render.py -- <tag> [quick]
Same cameras and sun as t03_render.py (orthographic, r30 scale, light fixed relative to the camera). Writes
renders/<tag>_eye_*.png:
  face_front / face_34 / face_side       whole face with hair (FACE / WIDE boxes)
  zoom_front / zoom_34 / zoom_side        eyes close up, with hair
  expr_<pose>                             front, eyes + mouth: neutral, Blink, Blink50, EyeSmile, Smile, SmileEyeSmile,
                                          Surprise, MouthOpen
  expr34_<pose>, exprlid_<pose>           3/4 / left upper lid close up for the eye poses
  face_60, lid_front, lid_34              60 deg face, left upper lid close up (front x4, 3/4 x3)
  gaze_L / gaze_R (+ _34)                 gaze 0.15 rad (B: eyeball picture turned; A / v5g: Eye_Gaze moved the same arc)
  id_front, id_<pose>                     no hair, flat ids: eye white green, iris blue, lashes / lid line red, rest black
  prot_<view>, prot_<view>_head           no hair: eyeball / white / iris yellow, lashes magenta, head blue / head alone
  nohair_front / _34_L / _34_R / _60_L / _side_L  colour, no hair, prot box (light response of the eye vs the skin)
"""
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
assert os.path.abspath(bpy.data.filepath).startswith((EXP, "/tmp/", "/private/tmp/"))
args = sys.argv[sys.argv.index("--") + 1:]
tag = args[0]
quick = "quick" in args
sys.argv = [sys.argv[0], "--", tag]
p = os.path.join(HERE, "t03_render.py")
g = {"__file__": p, "__name__": "eye_render"}
exec(open(p).read().split("FACE = (700")[0], g)
shoot = lambda name, box, yaw, scale=1.0: g["shoot"]("eye_" + name, box, yaw, scale)
sc = bpy.context.scene
B = "Eye_Ball.L" in bpy.data.objects
HAIR = [o for o in bpy.data.objects if (o.name.startswith("hair_bob_01") or o.name.startswith("acc_head_hairclip"))
        and not o.hide_render]
GAZE = 0.15
gaze0 = {s: bpy.data.objects[f"Eye_Gaze.{s}"].location.copy() for s in E.SIDES if f"Eye_Gaze.{s}" in bpy.data.objects}


def gaze(v):
    if B:
        E.set_gaze(v)
        return
    for s, l0 in gaze0.items():
        o = bpy.data.objects[f"Eye_Gaze.{s}"]
        sca = o.parent.matrix_world.to_scale().x if o.parent else 1.0
        o.location = l0.copy()
        o.location.x += v * 0.09 / sca            # same arc as B (eyeball R ~ 9 cm)
    bpy.context.view_layer.update()


def mouth_open(v):
    E.set_keys("MouthOpen", v)
    for o in bpy.data.objects:
        if o.name.startswith("Face_Mouth_Smile") and o.type == "MESH":
            o.hide_render = v <= 0
    m = bpy.data.objects.get("TT_Mouth_Closed")
    if m:
        m.hide_render = v > 0


def pose(name):
    for o in bpy.data.objects:
        if o.type == "MESH" and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks[1:]:
                k.value = 0.0
    mouth_open(0.0)
    gaze(0.0)
    if name == "Blink50":
        E.set_keys("Blink", 0.5)
    elif name == "MouthOpen":
        mouth_open(1.0)
    elif name == "SmileEyeSmile":
        E.set_keys("Smile", 1.0)
        E.set_keys("EyeSmile", 1.0)
    elif name not in ("neutral", None):
        E.set_keys(name, 1.0)
    bpy.context.view_layer.update()


def hair(show):
    for o in HAIR:
        o.hide_render = not show


ZF = (780, 400, 1280, 600)
EX = (780, 380, 1280, 720)
Z34 = (700, 340, 1300, 660)
pose("neutral")
hair(True)
shoot("face_front", (700, 0, 1360, 860), 0)
shoot("zoom_front", ZF, 0, 2.0)
shoot("zoom_34", Z34, 35, 1.6)
if not quick:
    shoot("face_34", (600, 0, 1460, 860), 35)
    shoot("face_side", (600, 0, 1460, 860), 90)
    shoot("zoom_side", (600, 340, 1000, 596), 90, 2.0)
    shoot("zoom_60", (700, 340, 1300, 660), 60, 1.6)
    shoot("face_60", (600, 0, 1460, 860), 60)
    shoot("lid_front", (1070, 405, 1270, 525), 0, 4.0)           # left upper lid close up
    shoot("lid_34", (890, 390, 1110, 520), 35, 3.0)
for pz in ("neutral", "Blink", "Blink50", "EyeSmile", "Smile", "SmileEyeSmile", "Surprise", "MouthOpen"):
    if quick and pz not in ("Blink", "EyeSmile"):
        continue
    pose(pz)
    shoot(f"expr_{pz}", EX, 0, 1.2)
    if pz in ("neutral", "Blink", "Blink50", "EyeSmile", "Smile", "SmileEyeSmile", "Surprise"):
        shoot(f"expr34_{pz}", Z34, 35, 1.2)
    if pz in ("neutral", "Blink50", "Blink", "EyeSmile", "SmileEyeSmile", "Surprise") and not quick:
        shoot(f"exprlid_{pz}", (1070, 405, 1270, 560), 0, 3.0)
pose("neutral")
for nm, v in (("gaze_L", GAZE), ("gaze_R", -GAZE)):
    gaze(v)
    shoot(nm, ZF, 0, 1.5)
    if not quick:
        shoot(nm + "_34", Z34, 35, 1.2)
gaze(0.0)
if quick:
    sys.exit(0)

# ------------------------------------------------------------------ id renders (no hair)
hair(False)
for vname, yaw in (("front", 0), ("34_L", 35), ("34_R", -35), ("60_L", 60), ("side_L", 90)):   # colour, same boxes as prot_*
    shoot(f"nohair_{vname}", (600, 200, 1460, 760), yaw)


def flat(name, col):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = col
    nt.links.new(e.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs[0])
    return m


def recolour(mat, col, image=None, col2=None):
    """copy of a textured eye material: emission colour `col` (or col -> col2 by `image` red), keeping its alpha clip"""
    m = mat.copy()
    nt = m.node_tree
    em = next(n for n in nt.nodes if n.type == "EMISSION")
    for l in list(em.inputs["Color"].links):
        nt.links.remove(l)
    tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None)
    if image is not None and tex is not None:
        t2 = nt.nodes.new("ShaderNodeTexImage")
        t2.image = bpy.data.images.load(image, check_existing=True)
        t2.extension = "EXTEND"
        if tex.inputs["Vector"].links:
            nt.links.new(tex.inputs["Vector"].links[0].from_socket, t2.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["A"].default_value = col
        mix.inputs["B"].default_value = col2
        gt = nt.nodes.new("ShaderNodeMath")
        gt.operation = "GREATER_THAN"
        gt.inputs[1].default_value = 0.5
        nt.links.new(t2.outputs["Color"], gt.inputs[0])
        nt.links.new(gt.outputs[0], mix.inputs["Factor"])
        nt.links.new(mix.outputs["Result"], em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = col
    # alpha straight cut (iris picture alpha of A / v5g, lash alpha of B)
    for n in nt.nodes:
        if n.type == "MIX_SHADER" and tex is not None and n.inputs[0].links and n.inputs[0].links[0].from_node == tex:
            gt = nt.nodes.new("ShaderNodeMath")
            gt.operation = "GREATER_THAN"
            gt.inputs[1].default_value = 0.5
            nt.links.new(tex.outputs["Alpha"], gt.inputs[0])
            nt.links.new(gt.outputs[0], n.inputs[0])
    return m


GREEN, BLUE, RED, YELLOW, BLACK, MAGENTA = (0, 1, 0, 1), (0, 0, 1, 1), (1, 0, 0, 1), (1, 1, 0, 1), (0, 0, 0, 1), (1, 0, 1, 1)
mats = {"black": flat("ID6_Black", BLACK), "green": flat("ID6_Green", GREEN), "red": flat("ID6_Red", RED),
        "yellow": flat("ID6_Yellow", YELLOW), "blue": flat("ID6_Blue", BLUE), "magenta": flat("ID6_Magenta", MAGENTA)}


def role(o):
    n = o.name
    if n.startswith("Eye_Ball"):
        return "ball"
    if n.startswith("Eye_White"):
        return "white"
    if n.startswith("Eye_Iris"):
        return "iris"
    if n.startswith("Eye_Lash"):
        return "lashtex"
    if any(k in n for k in ("UpperLid", "Lashes", "OuterLine")):
        return "lash"
    if n.startswith("Eye_LowerLid") or n.startswith("Eye_UpperCrease"):
        return "line"
    return "other"


objs = [o for o in bpy.data.objects if o.type in ("MESH", "CURVE") and not o.hide_render and o.visible_get()]
saved = {o.name: [s.material for s in o.material_slots] for o in objs}
outl = {}
for o in objs:
    md = o.modifiers.get("TT_Outline") if hasattr(o, "modifiers") else None
    if md:
        outl[o.name] = md.show_render
        md.show_render = False


def assign(mode):
    """mode 'class': white / iris / lash ids; 'prot': eye parts yellow, head blue; 'head': head blue, eye parts hidden"""
    for o in objs:
        r = role(o)
        o.hide_render = False
        for i, s in enumerate(o.material_slots):
            m0 = saved[o.name][i]
            if mode == "class":
                if r == "white":
                    s.material = mats["green"]
                elif r == "iris":
                    s.material = recolour(m0, BLUE)
                elif r == "lash":
                    s.material = mats["red"]
                elif r == "lashtex":
                    s.material = recolour(m0, RED)
                elif r == "ball":
                    side = o.name[-1]
                    s.material = recolour(m0, GREEN, os.path.join(EXP, "r30", f"eye_tex_iris_{side}.png"), BLUE)
                elif r == "line":
                    o.hide_render = True
                else:
                    s.material = mats["black"]
            else:
                eye = r in ("white", "iris", "lash", "lashtex", "ball", "line")
                if mode == "head" and eye:
                    o.hide_render = True
                if o.name.startswith("Blockout_Head") or o.name.startswith("Eye_Lids") or o.name.startswith("Face_Ear"):
                    s.material = mats["blue"]
                elif r in ("lash", "lashtex", "line"):
                    s.material = recolour(m0, MAGENTA) if r == "lashtex" else mats["magenta"]
                elif eye:
                    s.material = recolour(m0, YELLOW) if r == "iris" else mats["yellow"]
                else:
                    s.material = mats["black"]


assign("class")
pose("neutral")
shoot("id_front", (700, 0, 1360, 860), 0)
for pz in ("Blink", "EyeSmile", "Smile", "Surprise"):
    pose(pz)
    shoot(f"id_{pz}", (700, 0, 1360, 860), 0)
pose("neutral")
for nm, v in (("gaze_L", GAZE), ("gaze_R", -GAZE)):
    gaze(v)
    shoot(f"id_{nm}", (700, 0, 1360, 860), 0)
gaze(0.0)
for mode in ("prot", "head"):
    assign(mode)
    for vname, yaw in (("front", 0), ("side_L", 90), ("side_R", -90), ("60_L", 60), ("60_R", -60), ("34_L", 35), ("34_R", -35)):
        shoot(f"prot_{vname}" + ("_head" if mode == "head" else ""), (600, 200, 1460, 760), yaw)
for o in objs:
    o.hide_render = False
    for s, m in zip(o.material_slots, saved[o.name]):
        s.material = m
print("EYE_RENDER_DONE", tag)
