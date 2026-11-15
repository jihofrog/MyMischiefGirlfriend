"""Shared helpers for the hair_bob_01 v2 rebuild (volume first, then large clumps). Blender only.

Front-view pixel <-> world mapping is the r30 framing used by t03_render.py (r30 head 733 px = Blender head height).
"""
import bisect
import json
import math
import os

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
SPEC = json.load(open(os.path.join(EXP, "spec", "r30_face_spec.json")))
FIT = json.load(open(os.path.join(EXP, "spec", "blender_fit.json")))
TGT = json.load(open(os.path.join(EXP, "spec", "r30_hair_targets.json")))
PPM = SPEC["head_height_px"] / FIT["head_h"]
ZTOP = FIT["top_z"] + SPEC["hair_top_y"] / PPM
CX = SPEC["face_centre_x"]
AX_Y = 0.02                                   # vertical hair axis (x 0, y AX_Y)
HC = Vector((0, AX_Y, 1.44))                  # centre for polar directions
COLL = "hair_bob_01"
# volume front opening: half-angle (deg from the front) by height: closed above the forehead hairline, behind the ears
# at ear height, wrapping forward toward the jaw below them
OPEN = [(1.10, 64), (1.20, 65), (1.24, 70), (1.27, 80), (1.30, 95), (1.33, 103), (1.40, 102), (1.42, 90), (1.44, 76),
        (1.465, 64), (1.49, 52), (1.51, 38), (1.53, 18), (1.548, 0), (1.70, 0)]


def px_x(px):
    return (px - CX) / PPM


def py_z(py):
    return ZTOP - py / PPM


def table(tab, x):
    """Piecewise linear lookup in [(x, y), ...] sorted by x."""
    if x <= tab[0][0]:
        return tab[0][1]
    if x >= tab[-1][0]:
        return tab[-1][1]
    i = bisect.bisect_right(tab, (x, float("inf")))
    (x0, y0), (x1, y1) = tab[i - 1], tab[i]
    return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def smax(a, b, k):
    return 0.5 * (a + b + math.sqrt((a - b) ** 2 + k * k))


def polar_dir(th, ph):
    t, p = math.radians(th), math.radians(ph)
    return Vector((math.sin(p) * math.sin(t), -math.sin(p) * math.cos(t), math.cos(p)))


def bvh_of(names):
    dg = bpy.context.evaluated_depsgraph_get()
    outl = [bpy.data.objects[n].modifiers.get("TT_Outline") for n in names]
    was = [m.show_viewport if m else None for m in outl]
    for m in outl:
        if m:
            m.show_viewport = False                        # the outline hull is not an occluder
    dg.update()
    verts, polys = [], []
    for n in names:
        o = bpy.data.objects[n]; ev = o.evaluated_get(dg); me = ev.to_mesh()
        off = len(verts)
        verts += [ev.matrix_world @ v.co for v in me.vertices]
        polys += [[off + i for i in p.vertices] for p in me.polygons]
        ev.to_mesh_clear()
    for m, w in zip(outl, was):
        if m:
            m.show_viewport = w
    dg.update()
    return BVHTree.FromPolygons(verts, polys)


def bvh_of_bmesh(bm):
    return BVHTree.FromBMesh(bm)


# ------------------------------------------------------------------ materials
def srgb(c):
    c = [v / 255.0 for v in c]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)


def hair_material(name):
    """Anime toon: greyscale ramp x HairColor (separate from the style) x baked AO (vertex colour R). Opaque."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); L = nt.links.new
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    hc = nt.nodes.new("ShaderNodeRGB"); hc.label = "HairColor"; hc.outputs[0].default_value = srgb(SPEC["hair"]["base"])
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse"); s2r = nt.nodes.new("ShaderNodeShaderToRGB"); bw = nt.nodes.new("ShaderNodeRGBToBW")
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = "LINEAR"
    el = ramp.color_ramp.elements
    for e, (p, g) in zip([el[0], el[1]], [(0.0, 0.50), (0.30, 0.50)]):
        e.position, e.color = p, (g, g, g, 1)
    for p, g in [(0.40, 0.80), (0.60, 1.0), (0.68, 1.22), (1.0, 1.22)]:
        e = el.new(p); e.color = (g, g, g, 1)
    L(diff.outputs[0], s2r.inputs[0]); L(s2r.outputs["Color"], bw.inputs[0]); L(bw.outputs[0], ramp.inputs[0])
    tone = nt.nodes.new("ShaderNodeMix"); tone.data_type = "RGBA"; tone.blend_type = "MULTIPLY"; tone.inputs["Factor"].default_value = 1.0
    L(hc.outputs[0], tone.inputs["A"]); L(ramp.outputs["Color"], tone.inputs["B"])
    ca = nt.nodes.new("ShaderNodeVertexColor"); ca.layer_name = "Col"
    sep = nt.nodes.new("ShaderNodeSeparateColor"); L(ca.outputs["Color"], sep.inputs[0])
    aom = nt.nodes.new("ShaderNodeMapRange"); aom.inputs["To Min"].default_value = 0.55; aom.inputs["To Max"].default_value = 1.0
    L(sep.outputs[0], aom.inputs["Value"])
    ao = nt.nodes.new("ShaderNodeMix"); ao.data_type = "RGBA"; ao.blend_type = "MULTIPLY"; ao.inputs["Factor"].default_value = 1.0
    L(tone.outputs["Result"], ao.inputs["A"]); L(aom.outputs["Result"], ao.inputs["B"])
    em = nt.nodes.new("ShaderNodeEmission"); L(ao.outputs["Result"], em.inputs["Color"]); L(em.outputs[0], out.inputs[0])
    return m


def add_outline(o, thickness):
    line = bpy.data.materials.get("TT_Line_Hair")
    if line is None:
        return
    o.data.materials.append(line)
    sol = o.modifiers.new("TT_Outline", "SOLIDIFY")
    sol.thickness = thickness; sol.offset = 1.0; sol.use_flip_normals = True; sol.use_rim = False
    sol.material_offset = len(o.data.materials) - 1
    sol.use_even_offset = False; sol.thickness_clamp = 1.0           # no spikes at narrow tips


def apply_solidify(o, thickness, offset=-1.0, rim=True, vertex_group=""):
    """Bake a real thickness into the mesh (evaluated copy), keeping UV / colour layers."""
    sol = o.modifiers.new("Shell", "SOLIDIFY")
    sol.thickness = thickness; sol.offset = offset; sol.use_rim = rim; sol.use_even_offset = False
    if vertex_group:
        sol.vertex_group = vertex_group; sol.thickness_vertex_group = 0.0
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    o.modifiers.remove(sol)
    old = o.data; o.data = me; me.name = old.name; bpy.data.meshes.remove(old)


def orient_outward(bm):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    s = sum(f.normal.dot(f.calc_center_median() - HC) * f.calc_area() for f in bm.faces)
    if s < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.normal_update()


def bake_ao(objs, occluder_names, dist=0.04, n_rays=10):
    """Vertex colour R = 1 - 0.8 * occlusion (cone rays around the normal against hair + body)."""
    occ = bvh_of(occluder_names)
    for o in objs:
        me = o.data; mw = o.matrix_world
        col = me.color_attributes.get("Col")
        vals = []
        for v in me.vertices:
            p = mw @ v.co; n = (mw.to_3x3() @ v.normal).normalized()
            t1 = n.orthogonal().normalized(); t2 = n.cross(t1)
            hit = 0
            for k in range(n_rays):
                a = 2 * math.pi * k / n_rays; s = 0.75
                d = (n + (t1 * math.cos(a) + t2 * math.sin(a)) * s).normalized()
                if occ.ray_cast(p + n * 0.0015, d, dist)[0] is not None:
                    hit += 1
            vals.append(1.0 - 0.8 * hit / n_rays)
        for li, loop in enumerate(me.loops):
            c = col.data[li].color
            col.data[li].color = (vals[loop.vertex_index], c[1], c[2], 1.0)


def mesh_object(name, bm, coll):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me); coll.objects.link(o)
    return o


# ------------------------------------------------------------------ front-view projection (sheets)
class FrontProjector:
    """Lift r30 front-view pixels onto the hair volume (outer surface) or, where there is no volume, the face."""

    def __init__(self, volume_outer_bvh, body_names, wrap_names=("Blockout_Head", "Blockout_Neck"), use_body=True):
        self.vol = volume_outer_bvh
        self.body = bvh_of(body_names)
        self.use_body = use_body
        self.wrap = bvh_of(list(wrap_names))

    def r_wrap(self, th, z, gap=0.03, r_min=0.105):
        d = Vector((math.sin(math.radians(th)), -math.cos(math.radians(th)), 0)); o = Vector((0, AX_Y, z))
        h = self.wrap.ray_cast(o + d, -d, 1.0)
        return max(r_min, (0.0 if h[0] is None else (h[0] - o).length) + gap)

    def wrap_point(self, px, py):
        """No surface under the pixel: put it on a shell ~3 cm around face / jaw / neck (wraps the cheek)."""
        x, z = px_x(px), py_z(py)
        lo, hi = 0.0, 100.0
        for _ in range(30):
            mid = (lo + hi) / 2
            if self.r_wrap(mid, z) * math.sin(math.radians(mid)) < abs(x):
                lo = mid
            else:
                hi = mid
        th = (lo + hi) / 2; r = self.r_wrap(th, z)
        return Vector((x, AX_Y - r * math.cos(math.radians(th)), z))

    def hit(self, px, py):
        x, z = px_x(px), py_z(py)
        o = Vector((x, -1.0, z)); d = Vector((0, 1, 0))
        hv = self.vol.ray_cast(o, d, 2.0) if self.vol else (None,) * 4
        hb = self.body.ray_cast(o, d, 2.0)
        if hv[0] is not None and hv[1].y < -0.12 and (hb[0] is None or hv[3] <= hb[3]):
            return "vol", hv[0], hv[1]
        if self.use_body and hb[0] is not None and (hv[0] is None or hb[3] < hv[3]):
            n = hb[1] if hb[1].dot(hb[0] - HC) > 0 else -hb[1]
            if n.y < -0.35:                                # grazing hits on the side of the face are unstable
                return "body", hb[0], n
        return None


def layer_on_volume(bm, uvl, coll_layer, vol_bvh, th_a, th_b, z_top, z_bot, off, rand, nr=30, nc=8, tip=0.3, root=0.3):
    """A wide thin layer lying on the volume's outer surface between angles th_a(z) .. th_b(z) (deg, same sign side),
    from z_top down to z_bot. Over the first `root` of its length it grows out of the volume (narrow, flush), over the
    last `tip` it narrows to a rounded end; offset off(t) outward."""
    vs = []
    for r in range(nr):
        t = r / (nr - 1); z = z_top + (z_bot - z_top) * t
        a, b = th_a(z), th_b(z)
        k = max(0.0, (t - (1 - tip)) / tip); k = k * k * (3 - 2 * k)
        q = min(1.0, t / root); q = q * q * (3 - 2 * q)
        c = (a + b) / 2; h = (b - a) / 2 * (1 - 0.7 * k) * (0.3 + 0.7 * q)
        row = []
        for j in range(nc):
            th = c - h + 2 * h * j / (nc - 1)
            d = Vector((math.sin(math.radians(th)), -math.cos(math.radians(th)), 0)); o = Vector((0, AX_Y, z))
            hit = vol_bvh.ray_cast(o + d * 1.0, -d, 1.0)
            if hit[0] is None:
                p, n = o + d * 0.2, d
            else:
                p, n = hit[0], (hit[1] if hit[1].dot(d) > 0 else -hit[1])
            row.append(bm.verts.new(p + n * (off(t) * q + 0.0006)))
        vs.append(row)
    for r in range(nr - 1):
        for j in range(nc - 1):
            f = bm.faces.new((vs[r][j], vs[r][j + 1], vs[r + 1][j + 1], vs[r + 1][j]))
            for loop, (jj, rr) in zip(f.loops, [(j, r), (j + 1, r), (j + 1, r + 1), (j, r + 1)]):
                loop[uvl].uv = (jj / (nc - 1), rr / (nr - 1))
                loop[coll_layer] = (1.0, rand, rr / (nr - 1), 1.0)


def sheet_from_rows(bm, uvl, coll_layer, rows, proj, off_vol, off_body, rand, ncol=7, behind_z=None):
    """rows: [(py, xl, xr), ...] top -> tip. Builds a grid surface lifted onto the head. Points with no surface below
    wrap around the face (FrontProjector.wrap_point); within behind_z = (z_lo, z_hi) (ear height) they instead take the
    depth of the nearest valid point in the row, i.e. stay behind the ear."""
    grid = []
    for py, xl, xr in rows:
        row = []
        for c in range(ncol):
            u = c / (ncol - 1); px = xl + (xr - xl) * u
            h = proj.hit(px, py)
            if h is None:
                row.append(None)
            else:
                kind, p, n = h
                # over the face: lift toward the viewer only, so the r30 outline (forehead gaps) stays where it is
                row.append(p + n * off_vol if kind == "vol" else p + Vector((0, -off_body, 0)))
        grid.append(row)
    for r, row in enumerate(grid):
        for c in range(ncol):
            if row[c] is None:
                cand = [(abs(c2 - c), q) for c2, q in enumerate(row) if q is not None]
                py, xl, xr = rows[r]; pxc = xl + (xr - xl) * c / (ncol - 1); x = px_x(pxc); z = py_z(py)
                if behind_z and behind_z[0] <= z <= behind_z[1] and cand:
                    row[c] = Vector((x, min(cand, key=lambda t: t[0])[1].y, z))
                else:
                    row[c] = proj.wrap_point(pxc, py)
    vs = [[bm.verts.new(p) for p in row] for row in grid]
    nr = len(vs)
    for r in range(nr - 1):
        for c in range(ncol - 1):
            f = bm.faces.new((vs[r][c], vs[r][c + 1], vs[r + 1][c + 1], vs[r + 1][c]))
            for loop, (cc, rr) in zip(f.loops, [(c, r), (c + 1, r), (c + 1, r + 1), (c, r + 1)]):
                loop[uvl].uv = (cc / (ncol - 1), rr / (nr - 1))
                loop[coll_layer] = (1.0, rand, rr / (nr - 1), 1.0)
