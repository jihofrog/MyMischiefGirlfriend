"""ToonTest_01 step 40 (Blender, background): v6e candidates against the 3/4 "eye pushed forward" look.

usage: V6E_A=<beta> [V6E_PSI=<deg>] V6E_B=<0/1> V6E_OUT=<file.blend> Blender -b MG_ToonTest_01_v6d_3.blend --python t40_eye_v6e.py
Starts from v6d_3 (kept as it is). Every change moves points along y only, so the front view (orthographic, r30 scale)
keeps the r30 eye shape; topology, materials, keys (31 in the FBX) stay.
  A  face band: the eye opening wraps 9 -> 57 deg of a round face, so at 3/4 the eye turns toward the camera. The skin
     and everything lying on it (head, eyeball, lid sheets, lash band + crease, brows, blush) in the band from the inner
     eye corner to just past the outer corner is drawn toward a plane turned only PSI deg outward (V6E_PSI, default 20)
     through the v5g face (before the socket) just inside the inner corner: y += beta * W * min(0, plane - y_face). W
     fades out over 2.8 cm from the outer corner toward the temple, 1.8 cm below and 1.6 cm above the eye; the shift
     is capped at 8 mm, kept 2.5 mm behind any hair in front of the face (bangs, side strands) and smoothed (1 mm grid,
     3 mm blur). Smooth (custom) normals of the skin / lids / eyeball / lashes are tilted by the same field, so the
     toon shading follows the new surface without the facets of the coarse eyeball / socket meshes.
  B  outer eye: eyeball pushed back toward the outer corner (up to 1.5 mm, a deeper outer pocket under the lids; the
     socket skin behind it follows), lower lid edge 0.2 mm more around the outer white, and in the eyeball material an
     outer-corner sclera shade that appears only as the view turns away from the face front (front unchanged)
Writes the .blend and spec/eye_<name>_stats.json (incl. hair penetration after the change).
"""
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
assert os.path.abspath(bpy.data.filepath).startswith(EXP) and "v6d_3" in os.path.basename(bpy.data.filepath)
BETA = float(os.environ.get("V6E_A", 0))
DO_B = os.environ.get("V6E_B", "0") == "1"
OUT = os.environ["V6E_OUT"]
SLOPE = float(os.environ.get("V6E_SLOPE", 1.0))
TILT = float(os.environ.get("V6E_TILT", 0.0))      # 0: keep the v6d_3 shading normals, 1: follow the new surface
O = bpy.data.objects
stats = dict(beta=BETA, psi=float(os.environ.get("V6E_PSI", 20)), b=DO_B)
FACE_OBJS = ["Blockout_Head", "Eye_Ball.L", "Eye_Ball.R", "Eye_Lids.L", "Eye_Lids.R", "Eye_Lash.L", "Eye_Lash.R",
             "Face_Brow.L", "Face_Brow.R", "Face_Blush.L", "Face_Blush.R"]


def blocks(o):
    return list(o.data.shape_keys.key_blocks) if o.data.shape_keys else []


def move_y(o, fn):
    """y += fn(world points) for the mesh and every shape key (each key with its own x, z)"""
    mw, mi = o.matrix_world, o.matrix_world.inverted()
    srcs = [kb.data for kb in blocks(o)] + [o.data.vertices]
    for src in srcs:
        P = np.array([tuple(mw @ v.co) for v in src])
        d = fn(P)
        for v, p, dd in zip(src, P, d):
            if dd != 0.0:
                v.co = mi @ Vector((p[0], p[1] + dd, p[2]))
    o.data.update()


# ------------------------------------------------------------------ the v5g face before the socket (smooth reference)
with bpy.data.libraries.load(os.path.join(EXP, "MG_ToonTest_01_v5g_temple.blend"), link=False) as (src, dst):
    dst.objects = ["Blockout_Head"]
ref = dst.objects[0]
bpy.context.scene.collection.objects.link(ref)
for m in ref.modifiers:
    if m.name == "TT_Outline":
        m.show_viewport = False
FACE0 = E.bvh_of([ref.name])
bpy.data.objects.remove(ref)


def face_y(x, z):
    out = np.full(len(x), np.nan)
    for i, (xx, zz) in enumerate(zip(x, z)):
        y, _ = E.front_hit(FACE0, xx, zz)
        if y is not None:
            out[i] = y
    return out


GEO = {}
for s, sgn in (("L", 1), ("R", -1)):
    poly = E.opening_poly(s)
    u = poly[:, 0] * sgn
    ib = E.TGT[s]["iris_bbox"]
    GEO[s] = dict(sgn=sgn, x_in=float(u.min()), x_out=float(u.max()), z_bot=float(poly[:, 1].min()), z_top=float(poly[:, 1].max()),
                  x_iris=float(E.X((ib[0] + ib[2]) / 2)) * sgn)


PSI = float(os.environ.get("V6E_PSI", 20))     # residual outward turn of the eye band (deg)
HAIRB = E.bvh_of([o.name for o in bpy.data.collections["hair_bob_01"].objects if o.type == "MESH" and not o.name.endswith("_ref")])
GRIDS = {}


def blur(a, r):
    k = np.exp(-0.5 * (np.arange(-3 * r, 3 * r + 1) / r) ** 2)
    k /= k.sum()
    a = np.apply_along_axis(lambda v: np.convolve(np.pad(v, 3 * r, mode="edge"), k, mode="valid"), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(np.pad(v, 3 * r, mode="edge"), k, mode="valid"), 1, a)


def build_grid(g):
    """forward shift (m, <= 0) on a 1 mm grid: toward a plane turned PSI deg outward through the skin just inside the
    inner corner, faded past the outer corner / above / below, kept 2.5 mm behind any hair in front of the face"""
    us = np.arange(g["x_in"] - 0.02, g["x_out"] + 0.04, 0.001)
    zs = np.arange(g["z_bot"] - 0.045, g["z_top"] + 0.035, 0.001)
    U, Z = np.meshgrid(us, zs)
    X = U * g["sgn"]
    yf = face_y(X.ravel(), Z.ravel()).reshape(U.shape)
    u0 = g["x_in"] - 0.008
    yr = face_y(np.full(len(zs), g["sgn"] * u0), zs)[:, None]
    plane = yr + np.tan(np.radians(PSI)) * (U - u0)
    wx = E.smooth((U - (g["x_in"] - 0.004)) / 0.012) * (1 - E.smooth((U - (g["x_out"] - 0.002)) / 0.028))
    wz = E.smooth((Z - (g["z_bot"] - 0.022)) / 0.018) * (1 - E.smooth((Z - (g["z_top"] + 0.006)) / 0.016))
    d = np.nan_to_num(BETA * wx * wz * np.minimum(plane - yf, 0.0))
    d = np.maximum(d, -0.008)
    cap = np.full(U.shape, -1.0)
    for a in range(U.shape[0]):
        for b in range(U.shape[1]):
            if np.isnan(yf[a, b]):
                continue
            yh, _ = E.front_hit(HAIRB, X[a, b], Z[a, b])
            if yh is not None and yh < yf[a, b]:
                cap[a, b] = -max(0.0, yf[a, b] - yh - 0.0025)
    # hair right next to the face (side hair, temple strands): no skin within 2.5 mm of a hair vertex in front of it
    for o in bpy.data.collections["hair_bob_01"].objects:
        if o.type != "MESH" or o.name.endswith("_ref"):
            continue
        src = O["hair_bob_01__Volume_outer_ref"] if o.name == "hair_bob_01__Volume" else o
        for v in src.data.vertices:
            p = src.matrix_world @ v.co
            uu = p.x * g["sgn"]
            if p.y > 0 or not (us[0] < uu < us[-1] and zs[0] < p.z < zs[-1]):
                continue
            j0, i0 = int((uu - us[0]) / 0.001), int((p.z - zs[0]) / 0.001)
            for a in range(max(0, i0 - 4), min(len(zs), i0 + 5)):
                for b in range(max(0, j0 - 4), min(len(us), j0 + 5)):
                    if not np.isnan(yf[a, b]) and p.y < yf[a, b]:
                        cap[a, b] = max(cap[a, b], -max(0.0, yf[a, b] - p.y - 0.0025))
    # limit rising with a slope (V6E_SLOPE) away from the hair, so the shift fades out instead of stopping at a step
    for _ in range(60):
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            cap = np.maximum(cap, np.roll(np.roll(cap, di, 0), dj, 1) - SLOPE * 0.001 * np.hypot(di, dj))
    # smooth limit that is never deeper than the raw one: 6 mm max filter, then a blur reaching 6 mm (sigma 2)
    capm = cap.copy()
    for di in range(-6, 7):
        for dj in range(-6, 7):
            capm = np.maximum(capm, np.roll(np.roll(cap, di, 0), dj, 1))
    cap = blur(capm, 2)
    d = blur(d, 3)
    k = 0.001
    d = 0.5 * (d + cap + np.sqrt((d - cap) ** 2 + k * k))          # smooth max(d, cap)
    d = np.minimum(d, 0.0)
    gz, gu = np.gradient(d, 0.001)
    return us, zs, d, cap, gu, gz


def field_A(P, which=2):
    """which: 2 = shift, 4 = d/dx, 5 = d/dz"""
    d = np.zeros(len(P))
    for s, g in GEO.items():
        if s not in GRIDS:
            GRIDS[s] = build_grid(g)
        us, zs = GRIDS[s][0], GRIDS[s][1]
        D = GRIDS[s][which] * (g["sgn"] if which == 4 else 1.0)
        u = P[:, 0] * g["sgn"]
        ok = (u > us[0]) & (u < us[-1]) & (P[:, 2] > zs[0]) & (P[:, 2] < zs[-1]) & (P[:, 1] < 0)
        k = np.nonzero(ok)[0]
        fu = (u[k] - us[0]) / 0.001
        fz = (P[k, 2] - zs[0]) / 0.001
        i0, j0 = np.floor(fz).astype(int), np.floor(fu).astype(int)
        i0, j0 = np.clip(i0, 0, len(zs) - 2), np.clip(j0, 0, len(us) - 2)
        tz, tu = fz - i0, fu - j0
        v = (D[i0, j0] * (1 - tz) * (1 - tu) + D[i0 + 1, j0] * tz * (1 - tu) + D[i0, j0 + 1] * (1 - tz) * tu + D[i0 + 1, j0 + 1] * tz * tu)
        d[k] += v
    return d


def vertex_normals(o):
    me = o.data
    acc = np.zeros((len(me.vertices), 3))
    for li, lp in enumerate(me.loops):
        acc[lp.vertex_index] += tuple(me.corner_normals[li].vector)
    acc /= np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-9)
    return acc


def tilt_normals(o, N0, uniform=False):
    """the smooth (custom) normals of v6d_3 tilted by the shift field: surface y = f(x, z) + d(x, z).
    uniform: one mean tilt for the whole object (eyeball: the round shading stays smooth, no band along the field)"""
    P = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices])
    gx, gz = TILT * field_A(P, 4), TILT * field_A(P, 5)
    if uniform:
        front = N0[:, 1] < -0.3
        gx, gz = np.full(len(P), gx[front].mean()), np.full(len(P), gz[front].mean())
    b = np.minimum(N0[:, 1], -0.05)
    fx, fz = N0[:, 0] / -b, N0[:, 2] / -b
    n = np.stack([fx + gx, -np.ones(len(P)), fz + gz], 1)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    n = np.where((N0[:, 1] < -0.05)[:, None], n, N0)            # leave faces turned away from the front as they are
    o.data.normals_split_custom_set_from_vertices([tuple(v) for v in n])


if BETA:
    for n in FACE_OBJS:
        lit = n.startswith(("Blockout_Head", "Eye_Lids", "Eye_Ball", "Eye_Lash"))
        N0 = vertex_normals(O[n]) if lit else None
        move_y(O[n], field_A)
        if lit:
            tilt_normals(O[n], N0, uniform=n.startswith("Eye_Ball"))
    H = np.array([tuple(O["Blockout_Head"].matrix_world @ v.co) for v in O["Blockout_Head"].data.vertices])
    d0 = field_A(H)
    stats["A_head_forward_mm_max"] = round(float(-d0.min()) * 1000, 2)

# ------------------------------------------------------------------ B: outer eye
if DO_B:
    for s, g in GEO.items():
        ball = O[f"Eye_Ball.{s}"]
        BV0 = E.bvh_of([ball.name])

        def outer_w(P, g=g):
            u = P[:, 0] * g["sgn"]
            wz = E.smooth((P[:, 2] - (g["z_bot"] - 0.008)) / 0.008) * (1 - E.smooth((P[:, 2] - (g["z_top"] + 0.008)) / 0.008))
            return E.smooth((u - g["x_iris"]) / (g["x_out"] - g["x_iris"])) * wz

        DB = 0.0015
        move_y(ball, lambda P: DB * outer_w(P))
        # socket skin hidden behind the eyeball follows it (no wall comes into view)
        head = O["Blockout_Head"]
        Hb = np.array([tuple(head.matrix_world @ v.co) for v in head.data.vertices])
        poly = E.opening_poly(s)
        cand = np.nonzero(E.signed_dist(Hb[:, [0, 2]], poly) < 0.006)[0]
        behind = set()
        for i in cand:
            y, _ = E.front_hit(BV0, Hb[i, 0], Hb[i, 2])
            if y is not None and Hb[i, 1] > y + 0.0001:
                behind.add(int(i))
        idx = np.array(sorted(behind))
        move_y(head, lambda P, idx=idx: np.where(np.isin(np.arange(len(P)), idx), DB * outer_w(P), 0.0))
        stats[f"B_socket_verts_{s}"] = len(idx)
        # lower lid edge a little more around the outer white (rest pose only; keys keep their poses)
        lids = O[f"Eye_Lids.{s}"]
        kbs = lids.data.shape_keys.key_blocks
        L = np.array([tuple(lids.matrix_world @ d.co) for d in kbs["Basis"].data])
        nc = len(L) // 14
        lo = L[nc * 7:].reshape(nc, 7, 3)
        u = lo[:, 1, 0] * g["sgn"]
        xmid = (g["x_in"] + g["x_out"]) / 2
        dl = 0.0002 * E.smooth((u - xmid) / (g["x_out"] - xmid))
        old = L.copy()
        lo[:, 0, 2] += dl
        lo[:, 1, 2] += dl
        L[nc * 7:] = lo.reshape(-1, 3)
        mi = lids.matrix_world.inverted()
        for kb in list(kbs)[1:]:
            K = np.array([tuple(lids.matrix_world @ d.co) for d in kb.data])
            if np.abs(K - old).max() < 1e-7:
                for d, p in zip(kb.data, L):
                    d.co = mi @ Vector(tuple(p))
        for d, v, p in zip(kbs["Basis"].data, lids.data.vertices, L):
            d.co = mi @ Vector(tuple(p))
            v.co = d.co.copy()
        lids.data.update()
        # outer-corner sclera shade at oblique views (object space x of the eyeball, front view unchanged)
        m = ball.material_slots[0].material.copy()
        m.name = f"MG6e_EyeBall_{s}"
        nt = m.node_tree
        em = next(n for n in nt.nodes if n.type == "EMISSION")
        src_link = em.inputs["Color"].links[0].from_socket
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs[0])
        cx = ball.location.x
        x0 = g["sgn"] * g["x_iris"] - cx + g["sgn"] * 0.008          # object x: from just outside the iris ...
        x1 = g["sgn"] * g["x_out"] - cx                               # ... to the outer corner
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.interpolation_type = "SMOOTHSTEP"
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = x0, x1
        nt.links.new(sep.outputs["X"], mr.inputs["Value"])
        sm = next(n for n in nt.nodes if n.type == "MAP_RANGE" and abs(n.inputs["From Min"].default_value - 0.55) < 1e-6)
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(sm.outputs[0], inv.inputs[1])
        tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE" and n.inputs["Vector"].links and n.inputs["Vector"].links[0].from_node.type == "COMBXYZ")
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(tex.outputs["Color"], bw.inputs[0])
        scl = nt.nodes.new("ShaderNodeMapRange")                       # sclera only (bright texels)
        scl.interpolation_type = "SMOOTHSTEP"
        scl.inputs["From Min"].default_value, scl.inputs["From Max"].default_value = 0.55, 0.75
        nt.links.new(bw.outputs[0], scl.inputs["Value"])
        m1 = nt.nodes.new("ShaderNodeMath")
        m1.operation = "MULTIPLY"
        nt.links.new(mr.outputs[0], m1.inputs[0])
        nt.links.new(inv.outputs[0], m1.inputs[1])
        m2 = nt.nodes.new("ShaderNodeMath")
        m2.operation = "MULTIPLY"
        nt.links.new(m1.outputs[0], m2.inputs[0])
        nt.links.new(scl.outputs[0], m2.inputs[1])
        m3 = nt.nodes.new("ShaderNodeMath")
        m3.operation = "MULTIPLY_ADD"
        m3.inputs[1].default_value = -0.22
        m3.inputs[2].default_value = 1.0
        nt.links.new(m2.outputs[0], m3.inputs[0])
        sc = nt.nodes.new("ShaderNodeVectorMath")
        sc.operation = "SCALE"
        nt.links.new(src_link, sc.inputs[0])
        nt.links.new(m3.outputs[0], sc.inputs["Scale"])
        nt.links.new(sc.outputs[0], em.inputs["Color"])
        m["mmg_v6e_outer_shade"] = json.dumps(dict(x0=x0, x1=x1, strength=0.22))
        ball.material_slots[0].material = m
    stats["B_eyeball_outer_back_mm"] = 1.5

# ------------------------------------------------------------------ hair penetration after the change
HEADB = E.bvh_of(["Blockout_Head"])
hair = [o for o in bpy.data.collections["hair_bob_01"].objects if o.type == "MESH" and not o.name.endswith("_ref")]


def inside(bvh, p):
    votes = 0
    for d in (Vector((1, 0.013, 0.007)), Vector((-0.011, 1, 0.017)), Vector((0.009, -0.015, 1))):
        d.normalize()
        q, n = p.copy(), 0
        for _ in range(64):
            h = bvh.ray_cast(q, d, 2.0)
            if h[0] is None:
                break
            n += 1
            q = h[0] + d * 1e-5
        votes += n % 2
    return votes >= 2


pen = {}
for o in hair:
    src = O["hair_bob_01__Volume_outer_ref"] if o.name == "hair_bob_01__Volume" else o
    c = 0
    for v in src.data.vertices:
        p = src.matrix_world @ v.co
        if abs(p.x) > 0.16 or p.z < 1.28 or p.z > 1.52 or p.y > 0.0:
            continue
        loc, nrm, _, _ = HEADB.find_nearest(p, 0.05)
        if loc is not None and (p - loc).dot(nrm) < -1e-4 and inside(HEADB, p):
            c += 1
    pen[o.name.replace("hair_bob_01__", "")] = c
stats["hair_penetration_face_band"] = pen
for o in bpy.data.objects:
    if o.type == "MESH" and o.data.shape_keys:
        for k in o.data.shape_keys.key_blocks[1:]:
            k.value = 0.0
name = os.path.splitext(OUT)[0].replace("MG_ToonTest_01_", "")
json.dump(stats, open(os.path.join(EXP, "spec", f"eye_{name}_stats.json"), "w"), indent=1)
for s_, g_ in GRIDS.items():
    np.savez(os.path.join("/tmp", f"e6_grid_{name}_{s_}.npz"), us=g_[0], zs=g_[1], d=g_[2], cap=g_[3])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, OUT))
print("V6E_OK", json.dumps(stats))
