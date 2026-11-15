"""ToonTest_01 step 9 (Blender, background): rebuild the hair as strands (hair_bob_01) on the v3 toon file.

usage: Blender -b <Experiments/ToonTest_01/MG_ToonTest_01_v3.blend> --python t09_hair_bob_01.py
Writes MG_ToonTest_01_v4_hair.blend (v3 untouched). The old helmet hair (Hair_Main, Hair_Clip_X) is kept in the
collection Hair_Helmet_Backup, hidden. Face, eyes and shape keys are not touched.

Structure (collection hair_bob_01; object names <itemId>__<part>, 05 doc 10-2):
  hair_bob_01__Scalp     inner scalp (low-poly head mesh above the hairline, pushed out 6 mm), dark hair colour
  hair_bob_01__Crown     3 wide pieces from the parting (wrapped to the head curvature)
  hair_bob_01__Bangs     10 locks; tips measured on the r30 Bangs layer (front view)
  hair_bob_01__Side_R/L  5 locks each around the cheeks and jaw (front ones on the cheek, back ones behind the ear)
  hair_bob_01__Back      12 chunks, tips curling in under the nape
  hair_bob_01__Flyaway   3 thin strands
  hair_bob_01_Guides     the Bezier centre lines (hidden; edit these and re-run to reshape)
  acc_head_hairclip_x_01 + Socket_acc_head (empty; the clip is parented to the socket, not to the hair)
Each strand: Catmull-Rom keys -> Bezier guide -> resampled centre line -> lens cross-section swept along it,
width / thickness taper root -> tip, pushed outside head / neck / ears. Vertex colour "Col": R = baked occlusion
(strand overlap + roots), G = per-strand random, B = position along the strand. UV: u across, v along.
"""
import json
import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
SPEC = json.load(open(os.path.join(EXP, "spec", "r30_face_spec.json")))
FIT = json.load(open(os.path.join(EXP, "spec", "blender_fit.json")))
PPM = SPEC["head_height_px"] / FIT["head_h"]
ZTOP = FIT["top_z"] + SPEC["hair_top_y"] / PPM
AX_Y = 0.02                                   # vertical hair axis (x 0, y AX_Y)
HC = Vector((0, AX_Y, 1.44))                  # head centre for outward directions
rng = random.Random(7)
dg = bpy.context.evaluated_depsgraph_get()


def px_to_world(px, py):
    return (px - SPEC["face_centre_x"]) / PPM, ZTOP - py / PPM


def dirv(th):
    t = math.radians(th)
    return Vector((math.sin(t), -math.cos(t), 0.0))


def bvh_of(names):
    verts, polys = [], []
    for n in names:
        o = bpy.data.objects[n]; ev = o.evaluated_get(dg); me = ev.to_mesh()
        off = len(verts)
        verts += [ev.matrix_world @ v.co for v in me.vertices]
        polys += [[off + i for i in p.vertices] for p in me.polygons]
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys)


BODY = bvh_of(["Blockout_Head", "Blockout_Neck", "Face_Ear.L", "Face_Ear.R"])


def r_base(th, z):
    d = dirv(th); o = Vector((0, AX_Y, z)) + d * 1.0
    hit = BODY.ray_cast(o, -d, 1.0)
    return 0.0 if hit[0] is None else (hit[0] - Vector((0, AX_Y, z))).length


def key_pos(k):
    th, z = k[0], k[1]
    if len(k) == 4:                                  # (th, z, 'r', absolute radius)
        r = k[3]
    else:                                            # (th, z, offset from the surface)
        r = r_base(th, z) + k[2]
    return Vector((0, AX_Y, z)) + dirv(th) * r


def theta_for_x(x, z, off):
    lo, hi = -85.0, 85.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if (r_base(mid, z) + off) * math.sin(math.radians(mid)) < x:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ------------------------------------------------------------------ strand definitions
STRANDS = []   # dict(group, keys, w, t, wrap, taper, curl)


def add(group, keys, w, t, wrap=0.0, taper=0.6):
    """taper: where the tip narrowing starts (0..1 along the strand)."""
    STRANDS.append(dict(group=group, keys=keys, w=w, t=t, wrap=wrap, taper=taper))


def width_at(s, t):
    k = max(0.0, (t - s["taper"]) / (1 - s["taper"]))
    k = k * k * (3 - 2 * k)
    return max(0.0008, s["w"] * (0.92 + 0.08 * math.sin(math.pi * min(1.0, t / max(s["taper"], 1e-3)) * 0.5)) * (1 - 0.94 * k))


# crown: three wide pieces from the parting (theta 0) over the top
add("Crown", [(12, 1.649, 0.006), (52, 1.626, 0.010), (86, 1.575, 0.014), (102, 1.51, 0.018), (106, 1.46, 0.020)], 0.17, 0.012, wrap=0.15, taper=0.7)
add("Crown", [(-12, 1.649, 0.006), (-53, 1.624, 0.010), (-88, 1.572, 0.014), (-103, 1.51, 0.018), (-107, 1.46, 0.020)], 0.17, 0.012, wrap=0.15, taper=0.7)
add("Crown", [(180, 1.650, 0.006), (180, 1.615, 0.010), (180, 1.56, 0.015), (180, 1.50, 0.020), (180, 1.45, 0.022)], 0.22, 0.012, wrap=0.16, taper=0.75)

# bangs: tips from the r30 Bangs lower edge (px, py); roots near the parting at the front of the crown
BANG_TIPS = [(855, 607, -30, 0.060), (897, 332, -20, 0.046), (921, 359, -16, 0.044), (957, 453, -10, 0.050),
             (993, 466, -5, 0.048), (1029, 472, 0, 0.054), (1065, 449, 6, 0.050), (1101, 385, 12, 0.046),
             (1149, 284, 18, 0.044), (1209, 593, 28, 0.060)]
for px, py, th_r, w in BANG_TIPS:
    x, z = px_to_world(px, py)
    off = 0.015 + 0.004 * rng.random()
    th_t = theta_for_x(x, z, off)
    th_h = theta_for_x(x * 0.85, 1.555, 0.012)
    keys = [(th_r * 0.5, 1.644, 0.004), (th_r * 0.8 + th_h * 0.2, 1.618, 0.008), (th_h, 1.555, 0.012)]
    if z < 1.50:
        keys.append(((th_h + th_t) / 2, (1.53 + z) / 2 + 0.02, off - 0.001))
    keys.append((th_t, z, off))
    add("Bangs", keys, w * 1.25, 0.008, taper=0.5 if z < 1.42 else 0.4)

# sides (character left = +theta): front lock on the cheek ... lock behind the ear; right side mirrored with changes
SIDE_L = [
    [(60, 1.600, 0.002), (58, 1.50, 0.016), (50, 1.40, 0.020), (44, 1.31, 0.022), (40, 1.245, "r", 0.115), (36, 1.205, "r", 0.098)],
    [(68, 1.600, 0.002), (67, 1.50, 0.022), (60, 1.39, 0.040), (54, 1.30, "r", 0.165), (50, 1.230, "r", 0.160), (46, 1.190, "r", 0.128)],
    [(78, 1.600, 0.002), (76, 1.50, 0.030), (70, 1.39, 0.060), (64, 1.30, "r", 0.205), (60, 1.225, "r", 0.200), (55, 1.180, "r", 0.160)],
    [(95, 1.600, 0.002), (96, 1.50, 0.040), (95, 1.39, 0.080), (93, 1.30, "r", 0.240), (92, 1.215, "r", 0.235), (88, 1.165, "r", 0.180)],
    [(115, 1.600, 0.002), (116, 1.50, 0.040), (116, 1.39, 0.075), (117, 1.30, "r", 0.225), (120, 1.215, "r", 0.215), (124, 1.170, "r", 0.160)],
]
SIDE_R = [
    [(-58, 1.600, 0.002), (-57, 1.50, 0.016), (-49, 1.40, 0.021), (-43, 1.31, 0.023), (-39, 1.250, "r", 0.118), (-35, 1.212, "r", 0.100)],
    [(-69, 1.600, 0.002), (-66, 1.50, 0.024), (-59, 1.39, 0.042), (-53, 1.30, "r", 0.170), (-50, 1.228, "r", 0.162), (-45, 1.186, "r", 0.130)],
    [(-80, 1.600, 0.002), (-77, 1.50, 0.032), (-71, 1.39, 0.062), (-65, 1.30, "r", 0.210), (-62, 1.222, "r", 0.205), (-57, 1.172, "r", 0.158)],
    [(-97, 1.600, 0.002), (-97, 1.50, 0.040), (-95, 1.39, 0.082), (-94, 1.30, "r", 0.245), (-93, 1.210, "r", 0.238), (-90, 1.160, "r", 0.182)],
    [(-114, 1.600, 0.002), (-115, 1.50, 0.038), (-117, 1.39, 0.074), (-118, 1.30, "r", 0.222), (-121, 1.220, "r", 0.212), (-126, 1.172, "r", 0.158)],
]
for i, keys in enumerate(SIDE_L):
    add("Side_L", keys, [0.074, 0.090, 0.110, 0.122, 0.112][i], 0.011, wrap=0.25, taper=0.62)
for i, keys in enumerate(SIDE_R):
    add("Side_R", keys, [0.076, 0.088, 0.106, 0.125, 0.110][i], 0.011, wrap=0.25, taper=0.62)

# back: 10 chunks, the tip turns in under the nape
for i in range(12):
    th = 126 + i * (234 - 126) / 11 + rng.uniform(-3, 3)
    side = abs(180 - th) / 52.0                       # 0 centre .. 1 near the sides
    r_low = 0.205 + 0.03 * side + rng.uniform(-0.006, 0.006)
    z_tip = 1.160 + 0.012 * side + rng.uniform(-0.008, 0.008)
    keys = [(th * 0.9 + 180 * 0.1, 1.612, 0.002), (th, 1.55, 0.014), (th, 1.44, 0.030), (th, 1.33, "r", r_low),
            (th, 1.235, "r", r_low - 0.005), (th, z_tip + 0.012, "r", r_low - 0.055), (th + rng.uniform(-3, 3), z_tip + 0.035, "r", r_low - 0.095)]
    add("Back", keys, 0.105 + rng.uniform(-0.012, 0.014), 0.012, wrap=0.22, taper=0.66)

# flyaways: thin loose strands
add("Flyaway", [(-8, 1.646, 0.006), (-20, 1.628, 0.022), (-34, 1.600, 0.030), (-44, 1.575, 0.026)], 0.006, 0.003, taper=0.5)
add("Flyaway", [(70, 1.45, 0.022), (60, 1.36, 0.028), (52, 1.29, 0.024), (49, 1.255, "r", 0.118)], 0.008, 0.003, taper=0.5)
add("Flyaway", [(150, 1.50, 0.034), (160, 1.38, "r", 0.215), (165, 1.28, "r", 0.230), (170, 1.215, "r", 0.205)], 0.009, 0.003, taper=0.5)


# ------------------------------------------------------------------ geometry
def catmull_bezier(ps):
    """Bezier points (co, left, right) through ps (Catmull-Rom tangents)."""
    out = []
    for i, p in enumerate(ps):
        a = ps[max(i - 1, 0)]; b = ps[min(i + 1, len(ps) - 1)]
        tan = (b - a) / (6.0 if 0 < i < len(ps) - 1 else 3.0)
        out.append((p, p - tan, p + tan))
    return out


def sample_bezier(bz, n):
    pts = []
    for (p0, _, h0), (p1, h1, _) in zip(bz[:-1], bz[1:]):
        for k in range(24):
            t = k / 24.0; s = 1 - t
            pts.append(p0 * s ** 3 + h0 * 3 * s * s * t + h1 * 3 * s * t * t + p1 * t ** 3)
    pts.append(bz[-1][0])
    L = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        L.append(L[-1] + (b - a).length)
    out = []
    for i in range(n):
        target = L[-1] * i / (n - 1)
        j = max(1, min(len(L) - 1, next((k for k, l in enumerate(L) if l >= target), len(L) - 1)))
        f = (target - L[j - 1]) / max(L[j] - L[j - 1], 1e-9)
        out.append(pts[j - 1].lerp(pts[j], f))
    return out, L[-1]


def push_out(p, margin):
    th = math.degrees(math.atan2(p.x, -(p.y - AX_Y)))
    r = Vector((p.x, p.y - AX_Y, 0)).length
    need = r_base(th, p.z) + margin
    if r < need:
        p = Vector((0, AX_Y, p.z)) + dirv(th) * need
    return p


def build_strand(bm, s, uv_layer, col_layer, guides, idx):
    keys = [key_pos(k) for k in s["keys"]]
    bz = catmull_bezier(keys)
    cu = bpy.data.curves.new(f"hair_bob_01_guide_{s['group']}_{idx:02d}", "CURVE"); cu.dimensions = "3D"
    sp = cu.splines.new("BEZIER"); sp.bezier_points.add(len(bz) - 1)
    for bp, (co, hl, hr) in zip(sp.bezier_points, bz):
        bp.co, bp.handle_left, bp.handle_right = co, hl, hr
        bp.handle_left_type = bp.handle_right_type = "FREE"
    go = bpy.data.objects.new(cu.name, cu); guides.objects.link(go); go.hide_render = True
    n = 14 if s["w"] < 0.02 else 18
    pts, length = sample_bezier(bz, n)
    K = 6 if s["w"] < 0.02 else 10
    rand = rng.random()
    rings = []
    for i, p in enumerate(pts):
        t = i / (n - 1)
        th = s["t"] * (1 - 0.6 * t)
        p = push_out(p, th / 2 + 0.003)
        pts[i] = p
    for i, p in enumerate(pts):
        t = i / (n - 1)
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        Nn = (p - HC).normalized()
        N = (Nn - T * Nn.dot(T)).normalized()
        B = T.cross(N).normalized()
        w = width_at(s, t)
        thk = s["t"] * (1 - 0.6 * t)
        ring = []
        for k in range(K):
            a = 2 * math.pi * k / K
            xa = w / 2 * math.cos(a); sy = math.sin(a)
            no = thk / 2 * sy * (1.0 if sy > 0 else 0.55)
            if s["wrap"]:
                no -= xa * xa / (2 * s["wrap"])
            ring.append((bm.verts.new(p + B * xa + N * no), 0.5 + 0.5 * math.cos(a)))
        rings.append((ring, t))
    tip = bm.verts.new(pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.002)
    root = bm.verts.new(pts[0] - (pts[1] - pts[0]).normalized() * 0.001)
    faces = []
    for (ra, ta), (rb, tb) in zip(rings[:-1], rings[1:]):
        for k in range(K):
            k2 = (k + 1) % K
            f = bm.faces.new((ra[k][0], ra[k2][0], rb[k2][0], rb[k][0]))
            faces.append((f, [(ra[k][1], ta), (ra[k2][1], ta), (rb[k2][1], tb), (rb[k][1], tb)]))
    last, first = rings[-1][0], rings[0][0]
    for k in range(K):
        k2 = (k + 1) % K
        f = bm.faces.new((last[k][0], last[k2][0], tip)); faces.append((f, [(last[k][1], 1.0), (last[k2][1], 1.0), (0.5, 1.0)]))
        f = bm.faces.new((first[k2][0], first[k][0], root)); faces.append((f, [(first[k2][1], 0.0), (first[k][1], 0.0), (0.5, 0.0)]))
    for f, uvs in faces:
        for loop, (u, v) in zip(f.loops, uvs):
            loop[uv_layer].uv = (u, v)
            loop[col_layer] = (1.0, rand, v, 1.0)
    return dict(group=s["group"], n=n, K=K, length=round(length, 3), w=s["w"])


# ------------------------------------------------------------------ build
old = bpy.data.collections.get("MainGirlfriend_Hair")
old_counts = {}
for o in old.objects:                                # counted before hiding (hidden objects are not evaluated)
    if o.type != "MESH":
        continue
    sol = o.modifiers.get("TT_Outline"); was = sol.show_viewport if sol else None
    if sol:
        sol.show_viewport = False
    dg.update(); ev = o.evaluated_get(dg); om = ev.to_mesh(); om.calc_loop_triangles()
    old_counts[o.name] = dict(verts=len(om.vertices), tris=len(om.loop_triangles)); ev.to_mesh_clear()
    if sol:
        sol.show_viewport = was
backup = bpy.data.collections.new("Hair_Helmet_Backup"); bpy.context.scene.collection.children.link(backup)
for o in list(old.objects):
    backup.objects.link(o); old.objects.unlink(o); o.hide_render = True; o.hide_viewport = True
coll = bpy.data.collections.new("hair_bob_01"); bpy.context.scene.collection.children.link(coll)
guides = bpy.data.collections.new("hair_bob_01_Guides"); coll.children.link(guides)

stats = []
groups = {}
for idx, s in enumerate(STRANDS):
    g = s["group"]
    if g not in groups:
        bm = bmesh.new()
        groups[g] = (bm, bm.loops.layers.uv.new("UVMap"), bm.loops.layers.color.new("Col"))
    bm, uvl, coll_ = groups[g]
    stats.append(build_strand(bm, s, uvl, coll_, guides, idx))
objs = {}
for g, (bm, _, _) in groups.items():
    me = bpy.data.meshes.new(f"hair_bob_01__{g}")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])          # closed strands: normals point outward
    bm.normal_update(); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(me.name, me); coll.objects.link(o); objs[g] = o

# scalp: head faces above the hairline (low-poly base mesh, no subdivision), pushed out 6 mm
head = bpy.data.objects["Blockout_Head"]
bm = bmesh.new(); bm.from_mesh(head.data)
bm.transform(head.matrix_world)
bm.normal_update()
kill = [f for f in bm.faces if not (f.calc_center_median().z > 1.535 or (f.calc_center_median().y > -0.02 and f.calc_center_median().z > 1.26))]
bmesh.ops.delete(bm, geom=kill, context="FACES")
for v in bm.verts:
    v.co += v.normal * 0.006
uvl = bm.loops.layers.uv.new("UVMap"); cl = bm.loops.layers.color.new("Col")
for f in bm.faces:
    for loop in f.loops:
        loop[uvl].uv = (0.5, 0.5); loop[cl] = (0.35, 0.5, 0.0, 1.0)
me = bpy.data.meshes.new("hair_bob_01__Scalp"); bm.to_mesh(me); bm.free()
for p in me.polygons:
    p.use_smooth = True
scalp = bpy.data.objects.new(me.name, me); coll.objects.link(scalp); objs["Scalp"] = scalp

# baked occlusion (vertex colour R): rays from each strand vertex against all hair (+ head)
bpy.context.view_layer.update()
allv, allp = [], []
for o in objs.values():
    off = len(allv); allv += [o.matrix_world @ v.co for v in o.data.vertices]; allp += [[off + i for i in p.vertices] for p in o.data.polygons]
hair_bvh = BVHTree.FromPolygons(allv, allp)
dirs = []
for i in range(8):
    a = 2 * math.pi * i / 8
    dirs.append(Vector((math.cos(a) * 0.6, math.sin(a) * 0.6, 1.0)).normalized())
for g, o in objs.items():
    if g == "Scalp":
        continue
    me = o.data
    vocc = []
    for v in me.vertices:
        n = v.normal.normalized()
        rot = n.to_track_quat("Z", "Y")
        hits = 0
        for d in dirs:
            dd = rot @ d
            h = hair_bvh.ray_cast(v.co + n * 0.0015, dd, 0.03)
            if h[0] is not None:
                hits += 1
        vocc.append(hits / len(dirs))
    cola = me.color_attributes["Col"]
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            c = cola.data[li].color
            t = c[2]
            ao = (1 - 0.8 * vocc[vi]) * (0.62 + 0.38 * min(1.0, t / 0.22))
            cola.data[li].color = (ao, c[1], c[2], 1.0)

# ------------------------------------------------------------------ materials
def srgb(c):
    c = [v / 255.0 for v in c]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)


HAIR_COLOUR = SPEC["hair"]["base"]               # character appearance colour (hair), not part of the style item
m = bpy.data.materials.new("M_hair_bob_01_01"); m.use_nodes = True
nt = m.node_tree; nt.nodes.clear(); L = nt.links.new
out = nt.nodes.new("ShaderNodeOutputMaterial")
hc = nt.nodes.new("ShaderNodeRGB"); hc.label = "HairColor"; hc.outputs[0].default_value = srgb(HAIR_COLOUR)
diff = nt.nodes.new("ShaderNodeBsdfDiffuse"); s2r = nt.nodes.new("ShaderNodeShaderToRGB"); bw = nt.nodes.new("ShaderNodeRGBToBW")
ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = "LINEAR"
el = ramp.color_ramp.elements
for e, (p, g) in zip([el[0], el[1]], [(0.0, 0.50), (0.30, 0.50)]):
    e.position, e.color = p, (g, g, g, 1)
for p, g in [(0.40, 0.80), (0.60, 1.0), (0.68, 1.30), (1.0, 1.30)]:
    e = el.new(p); e.color = (g, g, g, 1)
L(diff.outputs[0], s2r.inputs[0]); L(s2r.outputs["Color"], bw.inputs[0]); L(bw.outputs[0], ramp.inputs[0])
tone = nt.nodes.new("ShaderNodeMix"); tone.data_type = "RGBA"; tone.blend_type = "MULTIPLY"; tone.inputs["Factor"].default_value = 1.0
L(hc.outputs[0], tone.inputs["A"]); L(ramp.outputs["Color"], tone.inputs["B"])
ca = nt.nodes.new("ShaderNodeVertexColor"); ca.layer_name = "Col"
sep = nt.nodes.new("ShaderNodeSeparateColor")
L(ca.outputs["Color"], sep.inputs[0])
aom = nt.nodes.new("ShaderNodeMapRange"); aom.inputs["To Min"].default_value = 0.5; aom.inputs["To Max"].default_value = 1.0
L(sep.outputs[0], aom.inputs["Value"])
ao_mul = nt.nodes.new("ShaderNodeMix"); ao_mul.data_type = "RGBA"; ao_mul.blend_type = "MULTIPLY"; ao_mul.inputs["Factor"].default_value = 1.0
L(tone.outputs["Result"], ao_mul.inputs["A"]); L(aom.outputs["Result"], ao_mul.inputs["B"])
uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "UVMap"; sxy = nt.nodes.new("ShaderNodeSeparateXYZ"); L(uv.outputs[0], sxy.inputs[0])
across = nt.nodes.new("ShaderNodeMath"); across.operation = "MULTIPLY_ADD"; across.inputs[1].default_value = 2.0; across.inputs[2].default_value = -1.0
L(sxy.outputs["X"], across.inputs[0])
absx = nt.nodes.new("ShaderNodeMath"); absx.operation = "ABSOLUTE"; L(across.outputs[0], absx.inputs[0])
edge = nt.nodes.new("ShaderNodeMath"); edge.operation = "POWER"; edge.inputs[1].default_value = 3.0; L(absx.outputs[0], edge.inputs[0])
edge_dark = nt.nodes.new("ShaderNodeMix"); edge_dark.data_type = "RGBA"
L(edge.outputs[0], edge_dark.inputs["Factor"]); L(ao_mul.outputs["Result"], edge_dark.inputs["A"])
dk = nt.nodes.new("ShaderNodeMix"); dk.data_type = "RGBA"; dk.blend_type = "MULTIPLY"; dk.inputs["Factor"].default_value = 1.0
dk.inputs["B"].default_value = (0.72, 0.72, 0.72, 1)
L(ao_mul.outputs["Result"], dk.inputs["A"]); L(dk.outputs["Result"], edge_dark.inputs["B"])
# highlight: a short band along each strand (position jittered per strand), centred across the strand,
# only where lit and facing the camera
jit = nt.nodes.new("ShaderNodeMath"); jit.operation = "MULTIPLY_ADD"; jit.inputs[1].default_value = -0.16; jit.inputs[2].default_value = -0.22
L(sep.outputs[1], jit.inputs[0])                                    # band centre along the strand: v 0.22 .. 0.38
dz = nt.nodes.new("ShaderNodeMath"); dz.operation = "ADD"; L(sxy.outputs["Y"], dz.inputs[0]); L(jit.outputs[0], dz.inputs[1])
adz = nt.nodes.new("ShaderNodeMath"); adz.operation = "ABSOLUTE"; L(dz.outputs[0], adz.inputs[0])
band = nt.nodes.new("ShaderNodeMapRange"); band.inputs["From Min"].default_value = 0.008; band.inputs["From Max"].default_value = 0.035
band.inputs["To Min"].default_value = 1.0; band.inputs["To Max"].default_value = 0.0
L(adz.outputs[0], band.inputs["Value"])
cen = nt.nodes.new("ShaderNodeMapRange"); cen.inputs["From Min"].default_value = 0.35; cen.inputs["From Max"].default_value = 0.85
cen.inputs["To Min"].default_value = 1.0; cen.inputs["To Max"].default_value = 0.0
L(absx.outputs[0], cen.inputs["Value"])
lit = nt.nodes.new("ShaderNodeMapRange"); lit.inputs["From Min"].default_value = 0.40; lit.inputs["From Max"].default_value = 0.6
L(bw.outputs[0], lit.inputs["Value"])
lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.4
face = nt.nodes.new("ShaderNodeMath"); face.operation = "SUBTRACT"; face.inputs[0].default_value = 1.0; L(lw.outputs["Facing"], face.inputs[1])
m1 = nt.nodes.new("ShaderNodeMath"); m1.operation = "MULTIPLY"; L(band.outputs["Result"], m1.inputs[0]); L(cen.outputs["Result"], m1.inputs[1])
m2 = nt.nodes.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; L(m1.outputs[0], m2.inputs[0]); L(lit.outputs["Result"], m2.inputs[1])
m3 = nt.nodes.new("ShaderNodeMath"); m3.operation = "MULTIPLY"; L(m2.outputs[0], m3.inputs[0]); L(face.outputs[0], m3.inputs[1])
m4 = nt.nodes.new("ShaderNodeMath"); m4.operation = "MULTIPLY"; m4.inputs[1].default_value = 0.5; L(m3.outputs[0], m4.inputs[0])
hl_col = nt.nodes.new("ShaderNodeMix"); hl_col.data_type = "RGBA"; hl_col.inputs["Factor"].default_value = 0.5
L(hc.outputs[0], hl_col.inputs["A"]); hl_col.inputs["B"].default_value = (1, 1, 1, 1)
hl = nt.nodes.new("ShaderNodeMix"); hl.data_type = "RGBA"
L(m4.outputs[0], hl.inputs["Factor"]); L(edge_dark.outputs["Result"], hl.inputs["A"]); L(hl_col.outputs["Result"], hl.inputs["B"])
em = nt.nodes.new("ShaderNodeEmission"); L(hl.outputs["Result"], em.inputs["Color"]); L(em.outputs[0], out.inputs[0])

ms = bpy.data.materials.new("M_hair_bob_01_02"); ms.use_nodes = True
nt2 = ms.node_tree; nt2.nodes.clear(); o2 = nt2.nodes.new("ShaderNodeOutputMaterial"); e2 = nt2.nodes.new("ShaderNodeEmission")
e2.inputs["Color"].default_value = srgb([c * 0.5 for c in HAIR_COLOUR]); nt2.links.new(e2.outputs[0], o2.inputs[0])
line = bpy.data.materials.get("TT_Line_Hair")
for g, o in objs.items():
    o.data.materials.append(ms if g == "Scalp" else m)
    if g != "Scalp" and line is not None:
        o.data.materials.append(line)
        sol = o.modifiers.new("TT_Outline", "SOLIDIFY")
        sol.thickness = 0.0010 if g != "Flyaway" else 0.0006
        sol.offset = 1.0; sol.use_flip_normals = True; sol.use_rim = False; sol.material_offset = 1
        sol.use_even_offset = False; sol.thickness_clamp = 1.0           # no spikes at the narrow root / tip fans

# ------------------------------------------------------------------ hair clip (accessory with its own socket)
bpy.context.view_layer.update()
cx, cz = px_to_world(1291, 315)
hit = hair_bvh.ray_cast(Vector((cx, -1.0, cz)), Vector((0, 1, 0)), 2.0)
loc, nrm = hit[0], hit[1].normalized()
if nrm.y > 0:                                                  # face the viewer side (-Y)
    nrm = -nrm
sock = bpy.data.objects.new("Socket_acc_head", None); sock.empty_display_type = "ARROWS"; sock.empty_display_size = 0.03
coll.objects.link(sock)
rot = nrm.to_track_quat("Z", "Y").to_matrix().to_4x4()
sock.matrix_world = Matrix.Translation(loc) @ rot
sock.parent = head; sock.matrix_parent_inverse = head.matrix_world.inverted()
bm = bmesh.new()
L_bar, W_bar, T_bar = (SPEC["hairclip"][2] - SPEC["hairclip"][0]) / PPM * 1.12, 0.0115, 0.0055
for ang in (45, -45):
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r["verts"]
    bmesh.ops.scale(bm, vec=(L_bar, W_bar, T_bar), verts=vs)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(ang), 3, "Z"), verts=vs)
bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.0022, segments=2, affect="EDGES")
cm = bpy.data.meshes.new("acc_head_hairclip_x_01"); bm.to_mesh(cm); bm.free()
for p in cm.polygons:
    p.use_smooth = True
clip = bpy.data.objects.new("acc_head_hairclip_x_01", cm); coll.objects.link(clip)
clip.parent = sock; clip.location = (0, 0, T_bar / 2 + 0.0015)
mc = bpy.data.materials.get("TT_Clip").copy(); mc.name = "M_acc_head_hairclip_x_01_01"
cm.materials.append(mc)
if line is not None:
    cm.materials.append(line)
    sol = clip.modifiers.new("TT_Outline", "SOLIDIFY"); sol.thickness = 0.0008; sol.offset = 1.0
    sol.use_flip_normals = True; sol.use_rim = False; sol.material_offset = 1

# ------------------------------------------------------------------ stats
info = dict(strands=len(STRANDS), by_group={}, objects={})
for st in stats:
    info["by_group"][st["group"]] = info["by_group"].get(st["group"], 0) + 1
for o in list(objs.values()) + [clip]:
    me = o.data
    info["objects"][o.name] = dict(verts=len(me.vertices), tris=sum(len(p.vertices) - 2 for p in me.polygons),
                                   materials=[mm.name for mm in me.materials])
info["old_helmet"] = old_counts                      # modifiers applied, outline off
info["clip"] = dict(location=[round(v, 4) for v in loc], normal=[round(v, 3) for v in nrm], bar_length=round(L_bar, 4))
json.dump(info, open(os.path.join(EXP, "spec", "hair_bob_01_stats.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, "MG_ToonTest_01_v4_hair.blend"))
print("HAIR_OK", json.dumps(info))
