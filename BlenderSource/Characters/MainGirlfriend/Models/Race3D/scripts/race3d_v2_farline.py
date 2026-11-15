"""Far-eye 1 px vertical line (Race3D v1, +-35 / +-45): two local fix candidates on copies (Blender, background).

usage: Blender -b Models/MainGirlfriend_Race3D_v1.blend --python race3d_v2_farline.py -- <A|B|B2> <out.blend>
Cause (t48 id renders): on the far eye the view-angle keys close the upper lid sheet over the outer white while the lash
band there stays (t81 keep mode), so the lid sheet edge (skin colour) and a strip of eye white show between the lash
skirt and the eyeball as a thin light line along the outer side.
  A  material only: the edge strip of the upper lid sheet (quads between row 0 = skirt and row 1 = edge) in the outer
     part of the eye (u > 0.45) gets a dark lash-coloured material. No vertex moves; in the front view that strip lies
     under the lash band.
  B  view keys only: in ViewFar<s>, ViewFar<s>_GO / _GI and ViewSide<s> the lash skirt row (row 0) of the outer band
     columns comes down to the upper lid edge of the same key (0.3 mm in front of it), so the skirt covers the lid edge.
     Basis and the expression keys are unchanged, so the front view is unchanged.
  B2 as B, from u > 0.35, and the skirt goes 0.8 mm further down past the lid edge (onto the eye white), 0.5 mm in front.
"""
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import expr_common as X  # noqa: E402
import expr_design as D  # noqa: E402

E = X.E
O = bpy.data.objects
args = sys.argv[sys.argv.index("--") + 1:]
MODE, OUT = args[0], os.path.abspath(args[1])
assert os.path.basename(bpy.data.filepath) == "MainGirlfriend_Race3D_v1.blend"
for s in E.SIDES:
    lids, lash = O[f"Eye_Lids.{s}"], O[f"Eye_Lash.{s}"]
    nc = len(lids.data.vertices) // 14
    Bw = X.key_world(lids, "Basis")
    lid_x = E.PX(Bw[np.arange(nc) * 7 + 1, 0])
    u = D.eye_u(s, lid_x, E.TGT[s]["opening"])
    if MODE == "A":
        m = bpy.data.materials.get("TT_Lid_Edge_Dark") or bpy.data.materials.new("TT_Lid_Edge_Dark")
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*E.srgb((52, 24, 22))[:3], 1)
        nt.links.new(em.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs[0])
        if m.name not in lids.data.materials:
            lids.data.materials.append(m)
        mi = list(lids.data.materials).index(m)
        n = 0
        for p in lids.data.polygons:
            vs = list(p.vertices)
            if max(vs) >= nc * 7:                      # lower sheet
                continue
            rows = sorted({v % 7 for v in vs})
            col = min(v // 7 for v in vs)
            if rows == [0, 1] and u[col] > 0.45:
                p.material_index = mi
                n += 1
        print("FARLINE A", s, "faces", n)
    else:
        nb, nr = int(lash["mmg_band_cols"]), int(lash["mmg_band_rows"])
        LB = X.key_world(lash, "Basis")
        band_x = E.PX(LB[np.arange(nb) * nr + 1, 0])
        ub = D.eye_u(s, band_x, E.TGT[s]["opening"])
        near = np.array([np.argmin(np.abs(lid_x - x)) for x in band_x])
        u0, extra, fwd = (0.35, 0.0008, 0.0005) if MODE == "B2" else (0.45, 0.0, 0.0003)
        w = D.smooth((ub - u0) / 0.25) * (1 - D.smooth((ub - 1.15) / 0.2))
        for k in (f"ViewFar{s}", f"ViewFar{s}_GO", f"ViewFar{s}_GI", f"ViewSide{s}"):
            Kl = X.key_world(lids, k)
            Ks = X.key_world(lash, k)
            n = 0
            for c in range(nb):
                if w[c] <= 0:
                    continue
                edge = Kl[near[c] * 7 + 1]
                sk = Ks[c * nr]
                tgt = edge + np.array([0.0, -fwd, -extra])
                if tgt[2] < sk[2]:                     # only downward: the skirt reaches the lid edge
                    Ks[c * nr] = sk + w[c] * (tgt - sk)
                    n += 1
            X.set_key(lash, k, Ks)
            print("FARLINE B", s, k, "skirt columns", n)
bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True)
if os.path.exists(OUT + "1"):
    os.remove(OUT + "1")
print("FARLINE_DONE", MODE, OUT)
