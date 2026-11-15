"""Shared helpers for the v6 eye tests (A: t24_eye_v6a.py, B: t25_eye_v6b.py, checks t26 / t27). Blender side.

Front projection = the r30 canvas: x = (px - 1030) / PPM, z = ZTOP - py / PPM, depth y (toward the viewer = -y).
"""
import json
import math
import os

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
FIT = json.load(open(os.path.join(EXP, "spec", "blender_fit.json")))
SPEC = json.load(open(os.path.join(EXP, "spec", "r30_face_spec.json")))
TGT = json.load(open(os.path.join(EXP, "spec", "r30_eye_targets.json")))
PPM = SPEC["head_height_px"] / FIT["head_h"]
ZTOP = FIT["top_z"] + SPEC["hair_top_y"] / PPM
CXP = SPEC["face_centre_x"]
SIDES = ("L", "R")
EXPR = ("Blink", "EyeSmile", "Smile", "Surprise")


def X(px):
    return (np.asarray(px, float) - CXP) / PPM


def Z(py):
    return ZTOP - np.asarray(py, float) / PPM


def PX(x):
    return CXP + np.asarray(x, float) * PPM


def PY(z):
    return (ZTOP - np.asarray(z, float)) * PPM


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def srgb(c):
    c = [v / 255.0 for v in c]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)


# ------------------------------------------------------------------ evaluated geometry
def world_mesh(o, dg=None):
    dg = dg or bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    vs = [ev.matrix_world @ v.co for v in me.vertices]
    fs = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return vs, fs


def bvh_of(names):
    """BVH of the evaluated objects without their TT_Outline hulls"""
    off = []
    for n in names:
        md = bpy.data.objects[n].modifiers.get("TT_Outline")
        if md is not None and md.show_viewport:
            md.show_viewport = False
            off.append(md)
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    V, F = [], []
    for n in names:
        vs, fs = world_mesh(bpy.data.objects[n], dg)
        k = len(V)
        V += vs
        F += [tuple(i + k for i in f) for f in fs]
    for md in off:
        md.show_viewport = True
    return BVHTree.FromPolygons(V, F)


def front_hit(bvh, x, z):
    """front-most surface hit along +y at (x, z): (y, normal) or (None, None)"""
    h = bvh.ray_cast(Vector((float(x), -1.0, float(z))), Vector((0, 1, 0)), 3.0)
    return (h[0].y, h[1]) if h[0] is not None else (None, None)


# ------------------------------------------------------------------ r30 eye outlines (metres)
def opening_poly(s):
    p = np.array(TGT[s]["opening"], float)
    return np.stack([X(p[:, 0]), Z(p[:, 1])], 1)


def cols(s, key):
    """{px column: (top py, bottom py)} of r30_eye_targets.json"""
    return {int(k): tuple(v) for k, v in TGT[s][key].items()}


def signed_dist(P, poly):
    """2D signed distance (m) of points P (N, 2) to the closed polygon (negative inside)"""
    P = np.asarray(P, float)
    A = poly
    B = np.roll(poly, -1, 0)
    AB = B - A
    AP = P[:, None, :] - A[None]
    t = np.clip((AP * AB).sum(-1) / np.maximum((AB * AB).sum(-1), 1e-15), 0, 1)
    d = np.linalg.norm(AP - t[..., None] * AB, axis=-1).min(1)
    y = P[:, 1][:, None]
    x = P[:, 0][:, None]
    cross = ((A[None, :, 1] > y) != (B[None, :, 1] > y)) & (
        x < (B[None, :, 0] - A[None, :, 0]) * (y - A[None, :, 1]) / (B[None, :, 1] - A[None, :, 1] + 1e-15) + A[None, :, 0])
    inside = cross.sum(1) % 2 == 1
    return np.where(inside, -d, d)


# ------------------------------------------------------------------ stylised eyeball: spheroid with a vertical axis
class Spheroid:
    """((x-cx)^2 + (y-cy)^2) / R^2 + (z-cz)^2 / C^2 = 1; turning it about its vertical axis leaves the surface as it is"""

    def __init__(self, centre, R, C):
        self.c = np.array(centre, float)
        self.R, self.C = float(R), float(C)

    def front_y(self, x, z):
        x, z = np.asarray(x, float), np.asarray(z, float)
        q = self.R ** 2 * (1 - ((z - self.c[2]) / self.C) ** 2) - (x - self.c[0]) ** 2
        return np.where(q >= 0, self.c[1] - np.sqrt(np.maximum(q, 0)), np.nan)

    def front_y_clamped(self, x, z):
        """front_y, continued past the silhouette at the silhouette depth (for smooth blends)"""
        x, z = np.asarray(x, float), np.asarray(z, float)
        zz = np.clip((z - self.c[2]) / self.C, -0.999, 0.999)
        q = self.R ** 2 * (1 - zz ** 2) - (x - self.c[0]) ** 2
        return self.c[1] - np.sqrt(np.maximum(q, 0))

    def ny(self, x, z):
        """|y component| of the surface normal at the front point (x, z) (along-y = along-normal / ny)"""
        y = self.front_y_clamped(x, z)
        n = self.normal(np.stack([np.asarray(x, float), y, np.asarray(z, float)], -1))
        return np.maximum(np.abs(n[..., 1]), 0.35)

    def normal(self, p):
        p = np.asarray(p, float)
        g = np.stack([(p[..., 0] - self.c[0]) / self.R ** 2, (p[..., 1] - self.c[1]) / self.R ** 2,
                      (p[..., 2] - self.c[2]) / self.C ** 2], -1)
        return g / np.linalg.norm(g, axis=-1, keepdims=True)

    def surf(self, x, z, gap=0.0):
        x, z = np.asarray(x, float), np.asarray(z, float)
        p = np.stack([x, self.front_y(x, z), z], -1)
        g = np.asarray(gap, float)
        return p + self.normal(p) * (g[..., None] if g.ndim else g)

    def param(self, p):
        """(azimuth about the vertical axis, elevation) of the surface point nearest in direction"""
        d = np.asarray(p, float) - self.c
        az = np.arctan2(d[..., 0], -d[..., 1])
        el = np.arcsin(np.clip(d[..., 2] / self.C, -1, 1))
        return az, el

    def point(self, az, el):
        az, el = np.asarray(az, float), np.asarray(el, float)
        return self.c + np.stack([self.R * np.cos(el) * np.sin(az), -self.R * np.cos(el) * np.cos(az), self.C * np.sin(el)], -1)

    def as_dict(self):
        return dict(centre=self.c.round(5).tolist(), R=round(self.R, 5), C=round(self.C, 5))


def fit_spheroid(P, w, init, R_range=(0.045, 0.12), C_ratio=(1.0, 2.2), iters=60):
    """Levenberg-Marquardt on (cx, cy, cz, R, C): residual = front_y(x, z) - y of the target points (along y)"""
    P = np.asarray(P, float)
    w = np.sqrt(np.asarray(w, float))

    def res(q):
        s = Spheroid(q[:3], q[3], q[4])
        y = s.front_y(P[:, 0], P[:, 2])
        r = np.where(np.isnan(y), 0.02, y - P[:, 1])
        return r * w

    q = np.array(list(init.c) + [init.R, init.C], float)
    lam = 1e-3
    r0 = res(q)
    for _ in range(iters):
        J = np.zeros((len(r0), 5))
        for k in range(5):
            dq = np.zeros(5)
            dq[k] = 1e-5
            J[:, k] = (res(q + dq) - r0) / 1e-5
        A = J.T @ J
        g = J.T @ r0
        while True:
            step = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-12), g)
            qn = q + step
            qn[3] = np.clip(qn[3], *R_range)
            qn[4] = np.clip(qn[4], qn[3] * C_ratio[0], qn[3] * C_ratio[1])
            rn = res(qn)
            if (rn ** 2).sum() < (r0 ** 2).sum():
                q, r0, lam = qn, rn, lam * 0.3
                break
            lam *= 10
            if lam > 1e6:
                return Spheroid(q[:3], q[3], q[4])
    return Spheroid(q[:3], q[3], q[4])


# ------------------------------------------------------------------ meshes, materials
def mesh_object(name, verts, faces, coll, uvs=None, mat=None, parent=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    if uvs is not None:
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = uvs[me.loops[li].vertex_index]
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    if mat is not None:
        o.data.materials.append(mat)
    if parent is not None:
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o


def grid_faces(nc, nr, start=0, flip=False):
    """quads of an nc x nr vertex grid stored column-major (index = start + i * nr + j)"""
    f = []
    for i in range(nc - 1):
        for j in range(nr - 1):
            a, b = start + i * nr + j, start + (i + 1) * nr + j
            q = (a, b, b + 1, a + 1)
            f.append(q[::-1] if flip else q)
    return f


def toon_tex_material(name, image_path, lit=(0.80, 0.93, 1.0), clip=False):
    """r30-painted texture with a soft toon light response (same sun as the skin), optional alpha clip"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(image_path, check_existing=True)
    tex.interpolation = "Cubic"
    tex.extension = "EXTEND"
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    cr.elements[0].position, cr.elements[0].color = 0.15, (lit[0],) * 3 + (1,)
    cr.elements[1].position, cr.elements[1].color = 0.75, (lit[2],) * 3 + (1,)
    e = cr.elements.new(0.45)
    e.color = (lit[1],) * 3 + (1,)
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    em = nt.nodes.new("ShaderNodeEmission")
    L = nt.links.new
    L(dif.outputs[0], s2r.inputs[0])
    L(s2r.outputs["Color"], bw.inputs[0])
    L(bw.outputs[0], ramp.inputs[0])
    L(tex.outputs["Color"], mul.inputs["A"])
    L(ramp.outputs["Color"], mul.inputs["B"])
    L(mul.outputs["Result"], em.inputs["Color"])
    if clip:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        gt = nt.nodes.new("ShaderNodeMath")
        gt.operation = "GREATER_THAN"
        gt.inputs[1].default_value = 0.5
        mix = nt.nodes.new("ShaderNodeMixShader")
        L(tex.outputs["Alpha"], gt.inputs[0])
        L(gt.outputs[0], mix.inputs[0])
        L(tr.outputs[0], mix.inputs[1])
        L(em.outputs[0], mix.inputs[2])
        L(mix.outputs[0], out.inputs[0])
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "DITHERED"
    else:
        L(em.outputs[0], out.inputs[0])
    m["mmg_tex"] = os.path.basename(image_path)
    return m


def eyeball_material(name, image_path, side, centre, lit=(0.80, 0.93, 1.0)):
    """eyeball: r30 painted eye, front projected from the object space of the eyeball (origin = spheroid centre); the
    value node "Gaze" (radians, + = toward character left) turns the picture about the vertical axis -> gaze without
    moving the mesh (the same projection is done in the Unity shader)"""
    m = toon_tex_material(name, image_path, lit)
    nt = m.node_tree
    tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
    bx = TGT["tex_box"][side]
    w, h = bx[2] - bx[0], bx[3] - bx[1]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    rot = nt.nodes.new("ShaderNodeVectorRotate")
    rot.rotation_type = "Z_AXIS"
    gaze = nt.nodes.new("ShaderNodeValue")
    gaze.name = gaze.label = "Gaze"
    gaze.outputs[0].default_value = 0.0
    neg = nt.nodes.new("ShaderNodeMath")
    neg.operation = "MULTIPLY"
    neg.inputs[1].default_value = -1.0
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mu = nt.nodes.new("ShaderNodeMath")
    mu.operation = "MULTIPLY_ADD"
    mu.inputs[1].default_value = PPM / w
    mu.inputs[2].default_value = (CXP + centre[0] * PPM - bx[0]) / w
    mv = nt.nodes.new("ShaderNodeMath")
    mv.operation = "MULTIPLY_ADD"
    mv.inputs[1].default_value = PPM / h
    mv.inputs[2].default_value = 1 - ((ZTOP - centre[2]) * PPM - bx[1]) / h
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    L = nt.links.new
    L(tc.outputs["Object"], rot.inputs["Vector"])
    L(gaze.outputs[0], neg.inputs[0])
    L(neg.outputs[0], rot.inputs["Angle"])
    L(rot.outputs[0], sep.inputs[0])
    L(sep.outputs["X"], mu.inputs[0])
    L(sep.outputs["Z"], mv.inputs[0])
    L(mu.outputs[0], comb.inputs["X"])
    L(mv.outputs[0], comb.inputs["Y"])
    L(comb.outputs[0], tex.inputs["Vector"])
    m["mmg_eye_uv"] = json.dumps(dict(su=PPM / w, tu=mu.inputs[2].default_value, sv=PPM / h, tv=mv.inputs[2].default_value))
    return m


def set_gaze(rad):
    for m in bpy.data.materials:
        if m.node_tree and "Gaze" in m.node_tree.nodes:
            m.node_tree.nodes["Gaze"].outputs[0].default_value = rad


def toon_flat_material(name, colour, lit=(0.80, 0.93, 1.0)):
    """flat colour with the same soft light response (replaces the unlit emission eye materials in A)"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    cr.elements[0].position, cr.elements[0].color = 0.15, tuple(c * lit[0] for c in colour[:3]) + (1,)
    cr.elements[1].position, cr.elements[1].color = 0.75, tuple(c * lit[2] for c in colour[:3]) + (1,)
    e = cr.elements.new(0.45)
    e.color = tuple(c * lit[1] for c in colour[:3]) + (1,)
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(dif.outputs[0], s2r.inputs[0])
    nt.links.new(s2r.outputs["Color"], bw.inputs[0])
    nt.links.new(bw.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def add_light_response(m, lit=(0.80, 0.93, 1.0)):
    """multiply the emission colour of an unlit toon material by the soft sun response (in place)"""
    nt = m.node_tree
    em = next(n for n in nt.nodes if n.type == "EMISSION")
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    cr.elements[0].position, cr.elements[0].color = 0.15, (lit[0],) * 3 + (1,)
    cr.elements[1].position, cr.elements[1].color = 0.75, (lit[2],) * 3 + (1,)
    cr.elements.new(0.45).color = (lit[1],) * 3 + (1,)
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    src = em.inputs["Color"].links[0].from_socket if em.inputs["Color"].links else None
    if src is not None:
        nt.links.new(src, mul.inputs["A"])
    else:
        mul.inputs["A"].default_value = em.inputs["Color"].default_value[:]
    nt.links.new(dif.outputs[0], s2r.inputs[0])
    nt.links.new(s2r.outputs["Color"], bw.inputs[0])
    nt.links.new(bw.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], mul.inputs["B"])
    nt.links.new(mul.outputs["Result"], em.inputs["Color"])
    m["mmg_lit"] = list(lit)
    return m


# ------------------------------------------------------------------ shape keys
def set_keys(name, value):
    for o in bpy.data.objects:
        if o.type == "MESH" and o.data.shape_keys and name in o.data.shape_keys.key_blocks:
            o.data.shape_keys.key_blocks[name].value = value


def bake_modifiers_with_keys(objs, keep=("TT_Outline",)):
    """apply every modifier except `keep` and rebuild the shape keys from the evaluated result (FBX drops the keys of
    meshes that still have modifiers). All objects are evaluated together per key name, so a Shrinkwrap onto a mesh
    that has the same key follows it."""
    objs = [o for o in objs if any(m.name not in keep for m in o.modifiers)]
    if not objs:
        return []
    names = set()
    for o in objs:
        if o.data.shape_keys:
            names |= {k.name for k in o.data.shape_keys.key_blocks[1:]}
    kept = {}
    for o in objs:
        for m in o.modifiers:
            if m.name in keep:
                kept[(o.name, m.name)] = m.show_viewport
                m.show_viewport = False
    all_keys = [o for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys]
    for o in all_keys:
        for k in o.data.shape_keys.key_blocks[1:]:
            k.value = 0.0
    dg = bpy.context.evaluated_depsgraph_get()

    def snap():
        dg.update()
        res = {}
        for o in objs:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            res[o.name] = [v.co.copy() for v in me.vertices]
            ev.to_mesh_clear()
        return res

    base_meshes = {}
    for o in objs:
        dg.update()
        base_meshes[o.name] = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    keyed = {}
    for n in sorted(names):
        set_keys(n, 1.0)
        keyed[n] = snap()
        set_keys(n, 0.0)
    for o in objs:
        old = o.data
        had = [k.name for k in old.shape_keys.key_blocks[1:]] if old.shape_keys else []
        o.data = base_meshes[o.name]
        for m in list(o.modifiers):
            if m.name not in keep:
                o.modifiers.remove(m)
        for (on, mn), v in kept.items():
            if on == o.name:
                o.modifiers[mn].show_viewport = v
        ks = [n for n in sorted(names) if n in had]
        if o.data.shape_keys:
            o.shape_key_clear()
        if ks:
            o.shape_key_add(name="Basis", from_mix=False)
            for n in ks:
                k = o.shape_key_add(name=n, from_mix=False)
                co = keyed[n][o.name]
                assert len(co) == len(k.data), (o.name, n)
                for i, c in enumerate(co):
                    k.data[i].co = c
                k.value = 0.0
    return [o.name for o in objs]


def add_key(o, name, coords_world):
    """add (or replace) shape key `name` from world coordinates"""
    if not o.data.shape_keys:
        o.shape_key_add(name="Basis", from_mix=False)
    kb = o.data.shape_keys.key_blocks
    k = kb.get(name) or o.shape_key_add(name=name, from_mix=False)
    mi = o.matrix_world.inverted()
    for i, c in enumerate(coords_world):
        k.data[i].co = mi @ Vector(tuple(map(float, c)))
    k.value = 0.0
    return k


def brow_keys(head_bvh):
    """Blink / EyeSmile / Smile / Surprise keys on the (baked) brows: moved up / down, kept on the skin"""
    for s in SIDES:
        o = bpy.data.objects[f"Face_Brow.{s}"]
        B0 = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices])
        off = np.array([front_hit(head_bvh, p[0], p[2])[0] - p[1] for p in B0])
        xin = B0[:, 0].min() if s == "L" else B0[:, 0].max()
        inner = 1 - np.abs(B0[:, 0] - xin) / np.ptp(B0[:, 0])               # 1 at the inner (nose) end
        for pose, dz in (("Blink", -0.0012 + 0 * inner), ("EyeSmile", 0.0008 + 0 * inner), ("Smile", 0.0004 + 0 * inner),
                         ("Surprise", 0.0032 + 0.0012 * inner)):
            co = B0.copy()
            co[:, 2] += dz
            co[:, 1] = np.array([front_hit(head_bvh, p[0], p[2])[0] for p in co]) - off
            add_key(o, pose, co)


def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


# ------------------------------------------------------------------ v6i: view-angle correction keys
VIEW_LO, VIEW_HI = 20.0, 40.0


def view_far_weights(yaw_deg, lo=VIEW_LO, hi=VIEW_HI):
    """shape key values of ViewFarL / ViewFarR for a camera at yaw_deg (+ = toward the character's left, so R is the far
    eye): 0 up to lo, smoothstep to 1 at hi, 1 beyond; the near eye stays 0"""
    w = float(smooth((abs(yaw_deg) - lo) / (hi - lo)))
    return {"ViewFarR": w if yaw_deg > 0 else 0.0, "ViewFarL": w if yaw_deg < 0 else 0.0}


def view_stage_values(weights, n):
    """ViewFar<s> weight -> values of the stage keys ViewFar<s>_1..n (piecewise along the curved path, t70)"""
    out = {}
    for k, w in weights.items():
        for i in range(1, n + 1):
            out[f"{k}_{i}"] = float(np.clip(n * w - (i - 1), 0.0, 1.0))
    return out


SIDE_LO, SIDE_HI, SIDE_MAX = 50.0, 65.0, 0.8


def view_key_values(yaw_deg, gaze=0.0, blink=0.0, eyesmile=0.0, go=0.25, gi=0.12):
    """values of ViewFar<s>, ViewFar<s>_GO, ViewFar<s>_GI, ViewSide<s> (t72) for camera yaw, gaze (rad, + = character
    left), Blink and EyeSmile values (0..1). Far-eye weight from the angle, split over the gaze keys (outward up to go,
    inward up to gi, clamped); ViewSide (a Blink copy) closes the far eye up to SIDE_MAX from SIDE_LO to SIDE_HI deg.
    Per vertex the closing is Blink + (1 - Blink)(1 - EyeSmile)(side + (1 - side) ViewFar), never past Blink 100 %."""
    w = view_far_weights(yaw_deg)
    side = float(smooth((abs(yaw_deg) - SIDE_LO) / (SIDE_HI - SIDE_LO))) * SIDE_MAX
    out = {}
    for s, sg in (("L", 1), ("R", -1)):
        far = w[f"ViewFar{s}"] > 0
        sd = side if far else 0.0
        k = (1 - blink) * (1 - eyesmile)
        ws = w[f"ViewFar{s}"] * k * (1 - sd)
        g_out = sg * gaze
        to = float(np.clip(g_out / go, 0, 1))
        ti = float(np.clip(-g_out / gi, 0, 1))
        out[f"ViewFar{s}"] = ws * (1 - to - ti)
        out[f"ViewFar{s}_GO"] = ws * to
        out[f"ViewFar{s}_GI"] = ws * ti
        out[f"ViewSide{s}"] = sd * k
    return out
