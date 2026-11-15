"""ToonTest_01 step 10 (Blender, background): export hair_bob_01 + the X clip + its socket to FBX for the Unity check.

usage: Blender -b <MG_ToonTest_01_v4_hair.blend | v5*.blend> --python t10_export_hair_fbx.py -- <out.fbx>
(hidden helper meshes *_ref are not exported)
Outline Solidify modifiers are switched off (Unity draws its own outline pass); the outline material slot stays on
the mesh but owns no faces. The clip and its socket are exported unparented (world transform kept). Vertex colours (Col: R = AO, G = strand random, B = along-strand t) are exported.
The .blend is not saved.
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
out = sys.argv[sys.argv.index("--") + 1]

names = [o.name for o in bpy.data.collections["hair_bob_01"].objects if o.type == "MESH" and not o.name.endswith("_ref")]
names += ["acc_head_hairclip_x_01", "Socket_acc_head"]
bpy.ops.object.select_all(action="DESELECT")
for n in names:
    o = bpy.data.objects[n]
    for md in getattr(o, "modifiers", []):
        if md.name == "TT_Outline":
            md.show_render = False; md.show_viewport = False
    o.hide_set(False); o.select_set(True)
for n in ("acc_head_hairclip_x_01", "Socket_acc_head"):
    # bake_space_transform mis-scales children of empties (0.01); export as siblings, Unity re-attaches by socket name
    o = bpy.data.objects[n]; mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.export_scene.fbx(filepath=out, use_selection=True, object_types={"MESH", "EMPTY"}, use_mesh_modifiers=True,
                         apply_unit_scale=True, bake_space_transform=True, mesh_smooth_type="FACE",
                         colors_type="LINEAR", add_leaf_bones=False, bake_anim=False, embed_textures=False)
print("EXPORTED", len(names), out)
