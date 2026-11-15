"""ToonTest_01 step 29 (Blender, background, the .blend is not saved): export a v6 eye test (or v5g) to FBX for Unity.

usage: Blender -b <MG_ToonTest_01_v5g_temple | v6a_eye | v6b_eye>.blend --python t29_eye_export_fbx.py -- <out.fbx>
Head, face details, eyes, hair and clip in one file:
  - TT_Outline off (Unity draws its own outline); head vertex colour Col.R = outline weight (B: 0 in the socket)
  - every remaining modifier is applied with the shape keys rebuilt from the evaluated result (iris Shrinkwrap etc.)
  - open-mouth meshes exported too (Unity switches them on for MouthOpen); curves converted to meshes
  - meshes unparented with their world transform (bake_space_transform mis-scales children of empties)
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

assert os.path.abspath(bpy.data.filepath).startswith(E.EXP)
out = sys.argv[sys.argv.index("--") + 1]
for o in bpy.data.objects:
    if o.name.startswith("Face_Mouth_Smile") and o.type == "MESH":
        o.hide_render = False
for o in bpy.data.objects:
    md = o.modifiers.get("TT_Outline") if hasattr(o, "modifiers") else None
    if md:
        md.show_render = False
        md.show_viewport = False
keep = [o for o in bpy.data.objects if o.type in ("MESH", "CURVE") and not o.hide_render and o.visible_get()
        and not o.name.endswith("_ref") and not o.name.startswith("REF_")]
bpy.ops.object.select_all(action="DESELECT")
for o in [o for o in keep if o.type == "CURVE"]:
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    o.select_set(False)
keep = [bpy.data.objects[o.name] for o in keep]
baked = E.bake_modifiers_with_keys([o for o in keep if o.type == "MESH" and o.data.shape_keys])
head = bpy.data.objects["Blockout_Head"]
col = head.data.color_attributes.get("Col") or head.data.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
vg = head.vertex_groups.get("v6b_outline")
for i, v in enumerate(head.data.vertices):
    w = 1.0
    if vg is not None:
        w = next((g.weight for g in v.groups if g.group == vg.index), 1.0)
    col.data[i].color = (w, 1.0, 1.0, 1.0)
for o in keep:
    if o.parent is not None:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
for o in keep:
    o.hide_set(False)
    o.select_set(True)
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.export_scene.fbx(filepath=out, use_selection=True, object_types={"MESH"}, use_mesh_modifiers=True,
                         apply_unit_scale=True, bake_space_transform=True, mesh_smooth_type="FACE",
                         colors_type="LINEAR", add_leaf_bones=False, bake_anim=False, embed_textures=False,
                         use_custom_props=False)
print("EXPORTED", len(keep), "baked", baked, out)
print("KEYS", {o.name: [k.name for k in o.data.shape_keys.key_blocks[1:]] for o in keep if o.type == "MESH" and o.data.shape_keys})
