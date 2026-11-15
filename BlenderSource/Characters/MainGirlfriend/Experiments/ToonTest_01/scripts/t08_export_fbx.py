"""ToonTest_01 step 8 (Blender, background): export the v3 test character to FBX for the Unity URP check.

usage: Blender -b <MG_ToonTest_01_v3.blend> --python t08_export_fbx.py -- <out.fbx>
Outline Solidify modifiers are switched off (Unity draws its own outline pass), curves are converted to meshes,
objects hidden in renders (pupil / highlight meshes baked into the iris picture, open-mouth meshes, reference
images) are left out. The .blend is not saved.
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
out = sys.argv[sys.argv.index("--") + 1]
for o in bpy.data.objects:
    for md in getattr(o, "modifiers", []):
        if md.name == "TT_Outline":
            md.show_render = False; md.show_viewport = False
bpy.ops.object.select_all(action="DESELECT")
keep = []
for o in list(bpy.data.objects):
    if o.type == "CURVE" and not o.hide_render:
        bpy.context.view_layer.objects.active = o; o.select_set(True)
        bpy.ops.object.convert(target="MESH"); o.select_set(False)
for o in bpy.data.objects:
    if o.type == "MESH" and not o.hide_render and o.visible_get():
        o.select_set(True); keep.append(o.name)
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.export_scene.fbx(filepath=out, use_selection=True, object_types={"MESH"}, use_mesh_modifiers=True,
                         apply_unit_scale=True, bake_space_transform=True, mesh_smooth_type="FACE",
                         add_leaf_bones=False, bake_anim=False, path_mode="COPY", embed_textures=False)
print("EXPORTED", len(keep), out)
