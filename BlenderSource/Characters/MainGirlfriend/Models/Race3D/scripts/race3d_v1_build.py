"""MainGirlfriend Race3D v1 (Blender, background): the face / hair baseline from the approved v6j eye test.

usage: Blender -b <Experiments/ToonTest_01/MG_ToonTest_01_v6j.blend> --python race3d_v1_build.py -- <out.blend> [force] [ext=<m>] [extu=<u>]
The source .blend is read only; the result is a new file (refused if it exists unless "force").
  - v5g hair (hair_bob_01), v6j eyes (Eye_Lids / Eye_Lash / Eye_Ball, 47 blend shapes with the view-angle keys) and
    face details as they are in v6j; the excluded legacy collections stay excluded
  - lash root fix: the lowest visible row of the lash band (row 1) had UVs below the painted lash, so its bottom strip
    was transparent (alpha < 0.5) and the eyeball / lid sheet showed through as a 1 px light dotted line. Row 1 UVs of
    the columns over the eye opening move up the strand (towards row 2) to the first texel with alpha >= A_MIN plus a
    margin.
  - lash root overlap: in the front view the band edge stopped about 0.3 mm above the dark rim painted on the eyeball,
    a light sliver of the eyeball showed between them. Rows 1 and 0 (root and skirt) of the same columns move EXT
    further down the band (direction row 2 -> row 1 of each shape key, so every key keeps its own shape), fading out
    towards both eye corners; EXT stays well inside the 2.6 mm dark rim.
  - every image of the experiment folder is copied to Models/Race3D/textures and saved with relative paths
Writes Models/Race3D/spec/race3d_v1_build.json.
"""
import json
import os
import shutil
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACE3D = os.path.dirname(HERE)
EXP = os.path.abspath(os.path.join(RACE3D, "..", "..", "Experiments", "ToonTest_01"))
sys.path.insert(0, os.path.join(EXP, "scripts"))
import eye_v6_common as E  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(args[0])
assert os.path.basename(bpy.data.filepath) == "MG_ToonTest_01_v6j.blend", bpy.data.filepath
assert not os.path.exists(OUT) or "force" in args, f"{OUT} exists"
A_MIN = 0.9
MARGIN = 1.0 / 32
T_MAX = 0.5
U_RANGE = (-1.0, 1.6)            # iris half-widths from the iris centre: inner corner .. before the eye-tail flick
EXT = float(next((a.split("=", 1)[1] for a in args if a.startswith("ext=")), 0.0004))
EXT_RANGE = (-1.0, float(next((a.split("=", 1)[1] for a in args if a.startswith("extu=")), 1.6)))
EXT_FADE = (0.2, 0.3)            # iris half-widths over which the overlap fades in from each end of EXT_RANGE
O = bpy.data.objects
stats = dict(source=bpy.data.filepath, a_min=A_MIN, margin=MARGIN, t_max=T_MAX, u_range=U_RANGE, ext_m=EXT,
             ext_range=EXT_RANGE, ext_fade=EXT_FADE, sides={})


def lash_alpha(mat):
    node = next(n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image is not None)
    im = node.image
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    return px[:, :, 3], w, h, im.filepath


for s in E.SIDES:
    lash = O[f"Eye_Lash.{s}"]
    nb, nr = int(lash["mmg_band_cols"]), int(lash["mmg_band_rows"])
    alpha, w, h, src = lash_alpha(lash.data.materials[0])
    uvl = lash.data.uv_layers.active.data
    loops = {}
    for p in lash.data.polygons:
        for li, vi in zip(p.loop_indices, p.vertices):
            loops.setdefault(vi, []).append(li)

    def A(uv):
        x = min(max(int(uv[0] * w), 0), w - 1)
        y = min(max(int(uv[1] * h), 0), h - 1)            # Blender pixels: row 0 = bottom = v 0
        return float(alpha[y, x])

    ib = E.TGT[s]["iris_bbox"]
    sg = 1 if s == "L" else -1
    xc = float(E.X((ib[0] + ib[2]) / 2))
    ax = abs(float(E.X(ib[2]) - E.X(ib[0]))) / 2
    cols = []
    UV1 = [np.array(uvl[loops[c * nr + 1][0]].uv) for c in range(nb)]
    UV2 = [np.array(uvl[loops[c * nr + 2][0]].uv) for c in range(nb)]
    ts = np.arange(0, T_MAX + 1e-9, 1.0 / 64)

    def first_opaque(e1, e2):
        return next((t for t in ts if A(e1 + (e2 - e1) * t) >= A_MIN), None)

    for c in range(nb):
        i1 = c * nr + 1
        uv1, uv2 = UV1[c], UV2[c]
        if any(np.abs(np.array(uvl[li].uv) - uv1).max() > 1e-6 for li in loops[i1]):
            raise RuntimeError(f"{lash.name} row 1 column {c}: UV seam")
        u = sg * (float((lash.matrix_world @ lash.data.vertices[i1].co).x) - xc) / ax
        # the edge between columns is opaque only if both ends cover it: lines up to half way to each neighbour
        lines = [(uv1, uv2)]
        for n in (c - 1, c + 1):
            if 0 <= n < nb:
                for f in (0.25, 0.5):
                    lines.append((uv1 + (UV1[n] - uv1) * f, uv2 + (UV2[n] - uv2) * f))
        firsts = [first_opaque(e1, e2) for e1, e2 in lines]
        first = None if firsts[0] is None else max(t for t in firsts if t is not None)
        rec = dict(col=c, u=round(u, 3), alpha_row1=round(A(uv1), 3), t=0.0)
        if U_RANGE[0] <= u <= U_RANGE[1] and first is not None and first > 0:
            t = min(first + MARGIN, T_MAX)
            new = uv1 + (uv2 - uv1) * t
            for li in loops[i1]:
                uvl[li].uv = tuple(new)
            rec["t"] = round(float(t), 4)
        cols.append(rec)
    moved = [r for r in cols if r["t"] > 0]
    # overlap: rows 1 and 0 further down the band in every shape key
    wts = []
    for r in cols:
        u = r["u"]
        w = min(float(E.smooth((u - EXT_RANGE[0]) / EXT_FADE[0])), float(E.smooth((EXT_RANGE[1] - u) / EXT_FADE[1])))
        wts.append(w)
        r["ext_w"] = round(w, 3)
    for kb in lash.data.shape_keys.key_blocks:
        K = np.array([tuple(d.co) for d in kb.data])
        for c, w in enumerate(wts):
            if w <= 0:
                continue
            i0, i1, i2 = c * nr, c * nr + 1, c * nr + 2
            d = K[i1] - K[i2]
            n = np.linalg.norm(d)
            if n < 1e-9:
                continue
            off = d / n * EXT * w
            kb.data[i1].co = tuple(K[i1] + off)
            kb.data[i0].co = tuple(K[i0] + off)
    basis = lash.data.shape_keys.reference_key
    for v, d in zip(lash.data.vertices, basis.data):
        v.co = d.co
    lash.data.update()
    stats["sides"][s] = dict(texture=src, band_cols=nb, band_rows=nr, cols_moved=len(moved),
                             t_mean=round(float(np.mean([r["t"] for r in moved])), 4) if moved else 0.0,
                             t_max=max((r["t"] for r in moved), default=0.0),
                             ext_cols=sum(1 for w in wts if w > 0), columns=cols)
    print("LASH_ROOT", s, "uv moved", len(moved), "of", nb, "overlap columns", sum(1 for w in wts if w > 0))

# images of the experiment folder -> Models/Race3D/textures (the .blend then does not depend on the experiment)
tex_dir = os.path.join(RACE3D, "textures")
os.makedirs(tex_dir, exist_ok=True)
copied = []
for im in bpy.data.images:
    p = bpy.path.abspath(im.filepath) if im.filepath else ""
    if not p or not os.path.abspath(p).startswith(EXP + os.sep):
        continue
    dst = os.path.join(tex_dir, os.path.basename(p))
    if not os.path.exists(dst):
        shutil.copy2(p, dst)
    im.filepath = dst
    copied.append(os.path.basename(p))
stats["textures"] = sorted(copied)
# reference images: v6j points them to Experiments/References, which does not exist; the files are in MainGirlfriend/
mg_root = os.path.abspath(os.path.join(RACE3D, "..", ".."))
fixed = []
for im in bpy.data.images:
    p = bpy.path.abspath(im.filepath) if im.filepath else ""
    if not p or os.path.exists(p):
        continue
    for cand in (os.path.join(mg_root, "References", os.path.basename(p)), os.path.join(mg_root, os.path.basename(p))):
        if os.path.exists(cand):
            im.filepath = cand
            fixed.append(os.path.basename(p))
            break
stats["reference_images_fixed"] = fixed

sc = bpy.context.scene
sc["mmg_baseline"] = "MainGirlfriend_Race3D_v1"
sc["mmg_scope"] = "face and hair baseline; blockout body, no rig"
sc["mmg_source"] = "Experiments/ToonTest_01/MG_ToonTest_01_v6j.blend"
sc["mmg_eye"] = "v6j + lash root UV fix"
sc["mmg_hair"] = "v5g (hair_bob_01)"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True)
bpy.ops.file.make_paths_relative()                     # the copied textures, relative to the new location
bpy.ops.wm.save_mainfile()
if os.path.exists(OUT + "1"):
    os.remove(OUT + "1")
stats["images"] = {im.name: im.filepath for im in bpy.data.images if im.filepath}
spec = os.path.join(RACE3D, "spec")
os.makedirs(spec, exist_ok=True)
stats["out"] = OUT
json.dump(stats, open(os.path.join(spec, "race3d_v1_build.json"), "w"), indent=1, ensure_ascii=False)
print("RACE3D_BUILD_DONE", OUT, "textures", copied)
