"""ToonTest_01 step 7 (Blender, background): render the shape-key expressions (front face crop).

usage: Blender -b <MG_ToonTest_01_v3[_soft].blend> --python t07_expressions.py -- <tag>
Poses: neutral, Blink 1.0, Smile 1.0, MouthOpen 0.5, MouthOpen 1.0 (open-mouth meshes shown, closed line hidden).
Camera as t03 (front, r30 scale), cropped to eyes + mouth: r30 box (790, 380)-(1270, 720).
"""
import json
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
tag = sys.argv[sys.argv.index("--") + 1]
fit = json.load(open(os.path.join(EXP, "spec", "blender_fit.json")))
spec = json.load(open(os.path.join(EXP, "spec", "r30_face_spec.json")))
PPM = spec["head_height_px"] / fit["head_h"]
ztop = fit["top_z"] + spec["hair_top_y"] / PPM
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"; sc.render.film_transparent = True
box = (790, 380, 1270, 720)
sc.render.resolution_x, sc.render.resolution_y = box[2] - box[0], box[3] - box[1]
cd = bpy.data.cameras.new("TT_ExprCam"); cd.type = "ORTHO"; cd.ortho_scale = (box[2] - box[0]) / PPM
cam = bpy.data.objects.new("TT_ExprCam", cd); sc.collection.objects.link(cam); sc.camera = cam
cam.location = Vector(((((box[0] + box[2]) / 2) - spec["face_centre_x"]) / PPM, -3.0, ztop - ((box[1] + box[3]) / 2) / PPM))
cam.rotation_euler = (1.5707963, 0, 0)
sun = bpy.data.objects.get("TT_Sun")
if sun:
    sun.rotation_euler = (1.0472, 0, -0.349)


def keys(name, value):
    for o in bpy.data.objects:
        if o.type == "MESH" and o.data.shape_keys and name in o.data.shape_keys.key_blocks:
            o.data.shape_keys.key_blocks[name].value = value


def mouth_open(v):
    keys("MouthOpen", v)
    for o in bpy.data.objects:
        if o.name.startswith("Face_Mouth_Smile"):
            o.hide_render = v <= 0
    m = bpy.data.objects.get("TT_Mouth_Closed")
    if m:
        m.hide_render = v > 0


for pose, setup in (("neutral", lambda: None), ("blink", lambda: keys("Blink", 1.0)), ("smile", lambda: keys("Smile", 1.0)),
                    ("mouth_half", lambda: mouth_open(0.5)), ("mouth_open", lambda: mouth_open(1.0))):
    keys("Blink", 0.0); keys("Smile", 0.0); mouth_open(0.0)
    setup()
    sc.render.filepath = os.path.join(EXP, "renders", f"{tag}_expr_{pose}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", pose)
