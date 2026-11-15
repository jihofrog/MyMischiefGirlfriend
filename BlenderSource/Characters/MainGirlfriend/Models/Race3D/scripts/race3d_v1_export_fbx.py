"""MainGirlfriend Race3D v1 (Blender, background, the .blend is not saved): FBX for Unity.

usage: Blender -b Models/MainGirlfriend_Race3D_v1.blend --python race3d_v1_export_fbx.py -- <out.fbx>
Runs Experiments/ToonTest_01/scripts/t29_eye_export_fbx.py unchanged (the v6j export rules: TT_Outline off, head vertex
colour R = outline weight, modifiers baked with the shape keys, curves to meshes, meshes unparented), only without its
check that the .blend lies in the experiment folder.
"""
import os

T29 = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "Experiments",
                                   "ToonTest_01", "scripts", "t29_eye_export_fbx.py"))
src = open(T29).read()
old = "assert os.path.abspath(bpy.data.filepath).startswith(E.EXP)"
assert old in src
src = src.replace(old, "pass")
g = {"__file__": T29, "__name__": "__main__"}
exec(compile(src, T29, "exec"), g)
