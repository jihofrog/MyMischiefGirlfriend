"""ToonTest_01 step 3 (Blender, background): orthographic renders matching the r30 framing.

usage: Blender -b <Experiments/ToonTest_01/MG_ToonTest_01.blend> --python t03_render.py -- [tag] [hair [collection]]
Scale: r30 head (hair top to chin) 733 px = Blender head height (blender_fit.json) -> px per metre. The face camera
uses the r30 crop (700, 0)-(1360, 860) of the 2048 x 3072 canvas; the body camera the whole canvas at half size.
Writes ../renders/<tag>_face_front.png, _face_34.png, _face_side.png, _body_front.png (transparent background).
With "hair": only <tag>_hair_front / _34 / _side / _back in the wider HAIRBOX crop, plus _hair_mask_front (hair
collection alone) and _hair_id_front (hair and clip flat red) for t15_hair_metrics.py.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
tag = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1 else "v1"
fit = json.load(open(os.path.join(EXP, "spec", "blender_fit.json")))
spec = json.load(open(os.path.join(EXP, "spec", "r30_face_spec.json")))
PPM = spec["head_height_px"] / fit["head_h"]
z_canvas_top = fit["top_z"] + spec["hair_top_y"] / PPM
x_of = lambda px: (px - spec["face_centre_x"]) / PPM
z_of = lambda py: z_canvas_top - py / PPM

sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
try:
    sc.eevee.taa_render_samples = 32
except Exception:
    pass
sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"

cam_data = bpy.data.cameras.new("TT_Cam"); cam_data.type = "ORTHO"
cam = bpy.data.objects.new("TT_Cam", cam_data); sc.collection.objects.link(cam); sc.camera = cam
sun = bpy.data.objects.get("TT_Sun")


def shoot(name, box, yaw_deg, scale=1.0):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    sc.render.resolution_x, sc.render.resolution_y = int(w * scale), int(h * scale)
    sc.render.resolution_percentage = 100
    cam_data.ortho_scale = max(w, h) / PPM
    cx, cz = x_of((x0 + x1) / 2), z_of((y0 + y1) / 2)
    t = math.radians(yaw_deg)
    d, cy = 3.0, 0.03                     # orbit around the vertical axis through the head (x 0, y 0.03)
    view = Vector((-math.sin(t), math.cos(t), 0)); right = Vector((math.cos(t), math.sin(t), 0))
    cam.location = Vector((0, cy, cz)) - d * view + cx * right
    cam.rotation_euler = (math.radians(90), 0, t)
    if sun is not None:     # the light keeps its angle relative to the camera
        sun.rotation_euler = (math.radians(60), 0, math.radians(-20) + t)
    sc.render.filepath = os.path.join(EXP, "renders", f"{tag}_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", sc.render.filepath)


FACE = (700, 0, 1360, 860)
WIDE = (600, 0, 1460, 860)          # same pixel scale, wider so the turned head stays in frame
HAIRBOX = (480, 0, 1580, 1000)      # whole r30 hair (x 551..1491, y 20..912)
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(args) > 1 and args[1] == "hair":
    # hair views: tag hair [collection]; also a hair-only silhouette (clip excluded) for the r30 comparison
    for name, yaw in (("hair_front", 0), ("hair_34", 35), ("hair_side", 90), ("hair_back", 180)):
        shoot(name, HAIRBOX, yaw)
    hair = set(o.name for o in bpy.data.collections[args[2] if len(args) > 2 else "hair_bob_01"].all_objects)
    hidden = [o for o in sc.objects if o.type in ("MESH", "CURVE") and o.name not in hair and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    shoot("hair_mask_front", HAIRBOX, 0)
    for o in hidden:
        o.hide_render = False
    # id render: hair and the clip flat red, the rest as is (exact forehead exposure)
    red = bpy.data.materials.new("TT_ID_Red"); red.use_nodes = True; nt = red.node_tree; nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (1, 0, 0, 1)
    nt.links.new(em.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs[0])
    ids = [o for o in sc.objects if o.type == "MESH" and not o.hide_render and (o.name in hair or o.name.startswith("acc_head_hairclip"))]
    saved = {o.name: [s.material for s in o.material_slots] for o in ids}
    for o in ids:
        for s in o.material_slots:
            s.material = red
    shoot("hair_id_front", HAIRBOX, 0)
    for o in ids:
        for s, m in zip(o.material_slots, saved[o.name]):
            s.material = m
    sys.exit(0)
shoot("face_front", FACE, 0)
shoot("face_34", WIDE, 35)
shoot("face_side", WIDE, 90)
shoot("face_back", WIDE, 180)
shoot("body_front", (0, 0, 2048, 3072), 0, 0.5)
