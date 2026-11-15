"""ToonTest_01 step 35 (Blender, background): v6d candidates - small tweaks against the "eyeball pushed forward" look.

usage: V6D_BACK=<mm> V6D_FLAT=<0..0.1> V6D_LIDS=<0/1> V6D_MAT=<0/1> V6D_OUT=<file.blend> \
       Blender -b MG_ToonTest_01_v6c_eye.blend --python t35_eye_v6d.py
Starts from v6c (kept as it is). Socket, eyeball spheroid, gaze, lid sheets, lash band, crease, keys and FBX layout stay.
  BACK   eyeball moved back along y (front view unchanged); head vertices hidden behind the eyeball in the socket move
         back with it so no socket wall comes into view
  FLAT   eyeball front dome over the plane through the opening rim lowered by FLAT (only the part in front of that plane,
         so nothing comes forward)
  LIDS   upper lid edge + lash band 0.35 mm lower over the iris (more iris top under the lid), lower lid edge up to
         0.45 mm higher toward the outer corner (wraps the outer white); only Basis moves, keys keep their poses
  MAT    eyeball texture with socket AO in alpha (t36, read through UV0), white dimmed by up to 10 % and highlights by a
         further 20 % as the view turns away from the face front (front view unchanged)
Writes the .blend and spec/eye_<name>_stats.json.
"""
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
assert os.path.abspath(bpy.data.filepath).startswith(EXP) and "v6c" in os.path.basename(bpy.data.filepath)
BACK = float(os.environ.get("V6D_BACK", 0)) / 1000
FLAT = float(os.environ.get("V6D_FLAT", 0))
LIDS = os.environ.get("V6D_LIDS", "0") == "1"
MAT = os.environ.get("V6D_MAT", "0") == "1"
OUT = os.environ["V6D_OUT"]
O = bpy.data.objects
stats = dict(back_mm=BACK * 1000, flat=FLAT, lids=LIDS, mat=MAT)


def world(o, kb=None):
    src = kb.data if kb is not None else o.data.vertices
    return np.array([tuple(o.matrix_world @ v.co) for v in src])


def set_world(o, P, kb=None):
    mi = o.matrix_world.inverted()
    src = kb.data if kb is not None else o.data.vertices
    for v, p in zip(src, P):
        v.co = mi @ Vector(tuple(p))


def set_basis(o, P):
    """new Basis; keys that were equal to the old Basis follow it, the others keep their poses"""
    kbs = o.data.shape_keys.key_blocks
    old = world(o, kbs["Basis"])
    for kb in list(kbs)[1:]:
        if np.abs(world(o, kb) - old).max() < 1e-7:
            set_world(o, P, kb)
    set_world(o, P, kbs["Basis"])
    set_world(o, P)
    o.data.update()


for s in E.SIDES:
    ball = O[f"Eye_Ball.{s}"]
    poly = E.opening_poly(s)
    BV0 = E.bvh_of([ball.name])
    # ---------------- BACK
    if BACK:
        head = O["Blockout_Head"]
        kbs = head.data.shape_keys.key_blocks
        Hb = world(head, kbs["Basis"])
        near = np.nonzero((E.signed_dist(Hb[:, [0, 2]], poly) < 0.009) & (Hb[:, 1] < -0.03))[0]
        move = []
        for i in near:
            y, _ = E.front_hit(BV0, Hb[i, 0], Hb[i, 2])
            if y is not None and Hb[i, 1] > y + 0.0001:
                move.append(i)
        mi = head.matrix_world.inverted().to_3x3()
        d = mi @ Vector((0, BACK, 0))
        for kb in kbs:
            for i in move:
                kb.data[int(i)].co += d
        for i in move:
            head.data.vertices[int(i)].co += d
        head.data.update()
        ball.location.y += BACK
        bpy.context.view_layer.update()
        stats[f"head_socket_verts_moved_{s}"] = len(move)
    # ---------------- FLAT
    if FLAT:
        BV = E.bvh_of([ball.name])
        rim = []
        for x, z in poly[::3]:
            y, _ = E.front_hit(BV, x, z)
            if y is not None:
                rim.append((x, y, z))
        rim = np.array(rim)
        A = np.c_[rim[:, 0], rim[:, 2], np.ones(len(rim))]
        coef, *_ = np.linalg.lstsq(A, rim[:, 1], rcond=None)
        P = world(ball)
        plane = P[:, 0] * coef[0] + P[:, 2] * coef[1] + coef[2]
        dome = plane - P[:, 1]                                          # + = in front of the rim plane
        P[:, 1] += FLAT * np.maximum(dome, 0)
        set_world(ball, P)
        ball.data.update()
        stats[f"dome_max_before_mm_{s}"] = round(float(dome.max()) * 1000, 2)
        stats[f"dome_lowered_max_mm_{s}"] = round(float(FLAT * dome.max()) * 1000, 2)
    # ---------------- LIDS
    if LIDS:
        ib = E.TGT[s]["iris_bbox"]
        ix0, ix1 = float(E.X(ib[0])), float(E.X(ib[2]))
        icx, ihw = (ix0 + ix1) / 2, (ix1 - ix0) / 2
        iris_w = lambda x: E.smooth((1 - np.abs(x - icx) / ihw) / 0.4)    # 1 over the middle of the iris
        oc = E.cols(s, "opening_cols")
        xs_o = np.array(sorted(oc), float)
        xin, xout = (E.X(xs_o.min()), E.X(xs_o.max())) if s == "L" else (E.X(xs_o.max()), E.X(xs_o.min()))
        xmid = (xin + xout) / 2
        outer_w = lambda x: E.smooth((x - xmid) / (xout - xmid))         # 0 in the middle -> 1 at the outer corner
        lids = O[f"Eye_Lids.{s}"]
        lash = O[f"Eye_Lash.{s}"]
        L = world(lids, lids.data.shape_keys.key_blocks["Basis"])
        nc = len(L) // 14
        up = L[:nc * 7].reshape(nc, 7, 3)
        lo = L[nc * 7:].reshape(nc, 7, 3)
        du = 0.00035 * iris_w(up[:, 1, 0])
        up[:, 0, 2] -= du
        up[:, 1, 2] -= du
        up[:, 2, 2] -= du * 0.5
        dl = 0.00045 * outer_w(lo[:, 1, 0])
        lo[:, 0, 2] += dl
        lo[:, 1, 2] += dl
        lo[:, 2, 2] += dl * 0.5
        set_basis(lids, np.concatenate([up.reshape(-1, 3), lo.reshape(-1, 3)]))
        nb = int(lash["mmg_band_cols"])
        Lb = world(lash, lash.data.shape_keys.key_blocks["Basis"])
        band = Lb[:nb * 7].reshape(nb, 7, 3)
        band[:, :, 2] -= (0.00035 * iris_w(band[:, 1, 0]))[:, None]
        Lb[:nb * 7] = band.reshape(-1, 3)
        set_basis(lash, Lb)
        stats[f"lid_shift_mm_{s}"] = dict(upper_max=round(float(du.max()) * 1000, 2), lower_outer_max=round(float(dl.max()) * 1000, 2))
    # ---------------- MAT
    if MAT:
        m = ball.material_slots[0].material.copy()
        m.name = f"MG6d_EyeBall_{s}"
        nt = m.node_tree
        tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
        img = bpy.data.images.load(os.path.join(EXP, "r30", f"eye_tex_ball_v6d_{s}.png"), check_existing=True)
        img.alpha_mode = "STRAIGHT"
        tex.image = img
        mul = next(n for n in nt.nodes if n.type == "MIX" and n.blend_type == "MULTIPLY")
        em = next(n for n in nt.nodes if n.type == "EMISSION")
        # socket AO through UV0 (stays with the lids when the gaze turns)
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "UVMap"
        t2 = nt.nodes.new("ShaderNodeTexImage")
        t2.image = img
        t2.extension = "EXTEND"
        nt.links.new(uvn.outputs[0], t2.inputs["Vector"])
        # view factor f = cos(angle between the view and the face front), 1 in front
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        dot = nt.nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        dot.inputs[1].default_value = (0, -1, 0)
        nt.links.new(geo.outputs["Incoming"], dot.inputs[0])
        sm = nt.nodes.new("ShaderNodeMapRange")
        sm.interpolation_type = "SMOOTHSTEP"
        sm.inputs["From Min"].default_value, sm.inputs["From Max"].default_value = 0.55, 1.0
        nt.links.new(dot.outputs["Value"], sm.inputs["Value"])
        # white dim: 1 - 0.10 (1 - s); highlight dim: a further 0.20 on near-white texels
        dimw = nt.nodes.new("ShaderNodeMapRange")
        dimw.inputs["To Min"].default_value, dimw.inputs["To Max"].default_value = 0.90, 1.0
        nt.links.new(sm.outputs[0], dimw.inputs["Value"])
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(tex.outputs["Color"], bw.inputs[0])
        hl = nt.nodes.new("ShaderNodeMapRange")
        hl.interpolation_type = "SMOOTHSTEP"
        hl.inputs["From Min"].default_value, hl.inputs["From Max"].default_value = 0.93, 0.99
        nt.links.new(bw.outputs[0], hl.inputs["Value"])
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(sm.outputs[0], inv.inputs[1])
        hd = nt.nodes.new("ShaderNodeMath")
        hd.operation = "MULTIPLY"
        nt.links.new(hl.outputs[0], hd.inputs[0])
        nt.links.new(inv.outputs[0], hd.inputs[1])
        hd2 = nt.nodes.new("ShaderNodeMath")
        hd2.operation = "MULTIPLY_ADD"
        hd2.inputs[1].default_value = -0.20
        hd2.inputs[2].default_value = 1.0
        nt.links.new(hd.outputs[0], hd2.inputs[0])
        f1 = nt.nodes.new("ShaderNodeMath")
        f1.operation = "MULTIPLY"
        nt.links.new(dimw.outputs[0], f1.inputs[0])
        nt.links.new(hd2.outputs[0], f1.inputs[1])
        f2 = nt.nodes.new("ShaderNodeMath")
        f2.operation = "MULTIPLY"
        nt.links.new(f1.outputs[0], f2.inputs[0])
        nt.links.new(t2.outputs["Alpha"], f2.inputs[1])
        mul2 = nt.nodes.new("ShaderNodeVectorMath")
        mul2.operation = "SCALE"
        nt.links.new(mul.outputs["Result"], mul2.inputs[0])
        nt.links.new(f2.outputs[0], mul2.inputs["Scale"])
        nt.links.new(mul2.outputs[0], em.inputs["Color"])
        m["mmg_tex"] = f"eye_tex_ball_v6d_{s}.png"
        m["mmg_v6d"] = json.dumps(dict(ao="uv0 alpha", view_dim=0.10, hl_dim=0.20, view_from=0.55))
        ball.material_slots[0].material = m

for o in bpy.data.objects:
    if o.type == "MESH" and o.data.shape_keys:
        for k in o.data.shape_keys.key_blocks[1:]:
            k.value = 0.0
bpy.context.view_layer.update()
name = os.path.splitext(OUT)[0].replace("MG_ToonTest_01_", "")
json.dump(stats, open(os.path.join(EXP, "spec", f"eye_{name}_stats.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, OUT))
print("V6D_OK", json.dumps(stats))
