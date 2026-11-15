"""MainGirlfriend Race3D v1 (Blender, background, the .blend is not saved): the v6j verification renders for this file.

usage: [VIEWKEY=1] Blender -b Models/MainGirlfriend_Race3D_v1.blend --python race3d_v1_render_check.py -- <tag> [t48 args]
Runs Experiments/ToonTest_01/scripts/t48_eye_v6f_render.py unchanged (same camera, sun, boxes, poses and gaze as the v6j
renders), only without its check that the .blend lies in the experiment folder. Output: Experiments/ToonTest_01/renders/
<tag>_f6_*.png, next to the v6j renders it is compared with.
"""
import os

T48 = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "Experiments",
                                   "ToonTest_01", "scripts", "t48_eye_v6f_render.py"))
src = open(T48).read()
old = 'exec(open(p).read().split("FACE = (700")[0], g)'
assert old in src
src = src.replace(old, 'exec(open(p).read().replace("assert os.path.abspath(bpy.data.filepath).startswith(EXP)", "pass")'
                       '.split("FACE = (700")[0], g)')
g = {"__file__": T48, "__name__": "__main__"}
exec(compile(src, T48, "exec"), g)
