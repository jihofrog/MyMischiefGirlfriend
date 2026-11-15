"""ToonTest_01 step 18 (Blender, background): hair_bob_01 v5f = v5e + finishing. v5e is kept as it is.

usage: Blender -b <MG_ToonTest_01_v5e_fix.blend> --python t18_hair_v5f.py
Writes MG_ToonTest_01_v5f_finish.blend and spec/hair_v5f_stats.json.

1. Back: five wide, thin layers (hair_bob_01__Back) on the volume, 30..37 deg wide, overlapping, growing out of the
   crown / mid back and ending 0.8..1.8 cm below the volume edge in rounded tips at different heights. Not strands.
2. Ends: the volume's bottom edge gets a gentle wave (0..6 mm, along the circumference) so it no longer reads as a
   horizontal cut; together with the layer tips the hem line is broken. Overall length kept (lowest point -6 mm).
3. Temple: the temple layers are kept under bang clump A / D (they poked through it), and the lower outer part of
   the bang side locks is smoothed in depth only (x, z untouched, so the front outline and forehead stay the same).
   The tops of the side layers (z 1.42..1.50) are pressed almost flush onto the volume and their roots converge like
   the back layers (no step at their top edge). Where the volume came out in front of a bang, the volume is pushed
   back in y (two-ring falloff); the bangs themselves keep their shape.
4. Material M_hair_bob_01_01 (all hair pieces): thin strand streaks (1D noise around the head axis, slightly slanted)
   darken the base a little, and a soft narrow highlight band at the upper head breaks up along the same streaks,
   only on the lit side facing the viewer. No per-strand blocks, no large round / square highlight.
Ear coverage, bangs layout, forehead, length, clip, face and eyes are not changed.
"""
import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hair_v2_common as H  # noqa: E402

assert os.path.abspath(bpy.data.filepath).startswith(H.EXP)
rng = random.Random(18)
coll = bpy.data.collections[H.COLL]
vol = bpy.data.objects["hair_bob_01__Volume"]; ref = bpy.data.objects["hair_bob_01__Volume_outer_ref"]
bangs = bpy.data.objects["hair_bob_01__Bangs"]


def dirv(th):
    t = math.radians(th)
    return Vector((math.sin(t), -math.cos(t), 0.0))


def theta_of(p):
    return math.degrees(math.atan2(p.x, -(p.y - H.AX_Y)))


def rho_of(p):
    return Vector((p.x, p.y - H.AX_Y, 0)).length


def smooth01(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def rho_on(bvh, th, z):
    d = dirv(th); o = Vector((0, H.AX_Y, z))
    h = bvh.ray_cast(o + d * 1.0, -d, 1.0)
    return None if h[0] is None else (h[0] - o).length


# ------------------------------------------------------------------ 2. hem wave on the volume
zmin = {}
for v in ref.data.vertices:
    k = int(theta_of(v.co) // 5)
    zmin[k] = min(zmin.get(k, 9.0), v.co.z)
WAVE = 0.006


def hem_dz(p):
    k = int(theta_of(p) // 5)
    zm = zmin.get(k, min(zmin.values()))
    if zm > 1.25:                                     # front bins end at the forehead hairline, not at the hem
        return 0.0
    w = smooth01(1.0 - (p.z - zm) / 0.022)
    if w <= 0:
        return 0.0
    t = math.radians(theta_of(p))
    wave = 0.5 + 0.5 * math.sin(5 * t + 0.7) * math.cos(2 * t - 0.3)
    return -WAVE * wave * w


for me in (vol.data, ref.data):
    for v in me.vertices:
        v.co.z += hem_dz(v.co)
    me.update()

# ------------------------------------------------------------------ 3. temple: keep the temple layers under the bangs, smooth the bang side locks
bmb = bmesh.new(); bmb.from_mesh(bangs.data)
side_lock = [v for v in bmb.verts if abs(v.co.x) > 0.09 and 1.40 < v.co.z < 1.52]      # temple part of the side locks
y0 = {v.index: v.co.y for v in side_lock}
for _ in range(12):
    bmesh.ops.smooth_vert(bmb, verts=side_lock, factor=0.5, use_axis_x=False, use_axis_y=True, use_axis_z=False)
    for v in side_lock:
        v.co.y = min(v.co.y, y0[v.index])            # only toward the viewer: fills the dents, never sinks into the face
bmb.to_mesh(bangs.data); bmb.free(); bangs.data.update()
bmr = bmesh.new(); bmr.from_mesh(ref.data); VOL0 = H.bvh_of_bmesh(bmr); bmr.free()
bmb = bmesh.new(); bmb.from_mesh(bangs.data); BANGS = H.bvh_of_bmesh(bmb); bmb.free()
lifted = 0                                        # where the volume came out in front of a bang: push the volume back
for me in (vol.data, ref.data):                   # (+y, falloff over two vertex rings)
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    push = {}
    for v in bm.verts:
        if v.co.z < 1.38 or v.co.y > 0.05:
            continue
        hit = BANGS.ray_cast(v.co, Vector((0, 1, 0)), 0.03)
        if hit[0] is not None:
            push[v.index] = hit[0].y + 0.003 - v.co.y
    for _ in range(2):
        add = {}
        for i, d in push.items():
            for e in bm.verts[i].link_edges:
                j = e.other_vert(bm.verts[i]).index
                if j not in push:
                    add[j] = max(add.get(j, 0.0), d * 0.5)
        push.update(add)
    for i, d in push.items():
        bm.verts[i].co.y += d
    if me is vol.data:
        lifted = len(push)
    bm.to_mesh(me); bm.free(); me.update()
tucked = 0
for n in ("hair_bob_01__Side_L", "hair_bob_01__Side_R"):
    me = bpy.data.objects[n].data
    for v in me.vertices:
        if v.co.z < 1.36:
            continue
        th = theta_of(v.co); rb = rho_on(BANGS, th, v.co.z); rv = rho_of(v.co)
        if rb is not None and rv > rb - 0.0025 and rv < rb + 0.02:
            v.co = Vector((0, H.AX_Y, v.co.z)) + dirv(th) * (rb - 0.0025); tucked += 1
    me.update()

# side layers (v5e) started with a step at z 1.50: near their top they now lie almost flush on the volume
bmr = bmesh.new(); bmr.from_mesh(ref.data); VOL = H.bvh_of_bmesh(bmr); bmr.free()
flushed = 0
for n in ("hair_bob_01__Side_L", "hair_bob_01__Side_R"):
    me = bpy.data.objects[n].data
    for v in me.vertices:
        if v.co.z < 1.42:
            continue
        th = theta_of(v.co); rv = rho_of(v.co); rvol = rho_on(VOL, th, v.co.z)
        if rvol is None:
            continue
        g = smooth01((1.50 - v.co.z) / 0.08)
        d = rv - rvol
        new = rvol + max(0.0012, d * (0.15 + 0.85 * g)) if d > 0 else rv
        v.co = Vector((0, H.AX_Y, v.co.z)) + dirv(th) * new; flushed += 1
    me.update()

# side layer roots converge like the back layers: per island (temple / outer layer), rows by UV v
ROOT = {"temple": (0.18, 0.45, 0.55), "outer": (0.30, 0.30, 0.70)}        # root length, old width factor a + b q
converged = 0
for n in ("hair_bob_01__Side_L", "hair_bob_01__Side_R"):
    o = bpy.data.objects[n]; bm = bmesh.new(); bm.from_mesh(o.data)
    uv = bm.loops.layers.uv["UVMap"]
    vv = {}
    for f in bm.faces:
        for lp in f.loops:
            vv[lp.vert.index] = lp[uv].uv[1]
    seen = set()
    for v0 in bm.verts:
        if v0.index in seen:
            continue
        island, stack = [], [v0]
        while stack:
            v = stack.pop()
            if v.index in seen:
                continue
            seen.add(v.index); island.append(v)
            stack += [e.other_vert(v) for e in v.link_edges]
        kind = "outer" if sum(abs(theta_of(v.co)) for v in island) / len(island) > 125 else "temple"
        root, a0, b0 = ROOT[kind]
        rows = {}
        for v in island:
            rows.setdefault(round(vv.get(v.index, 1.0), 3), []).append(v)
        for t, vs in rows.items():
            if t >= root:
                continue
            q = smooth01(t / root)
            ratio = (0.06 + 0.94 * q) / (a0 + b0 * q)
            ths = [theta_of(v.co) for v in vs]; thc = (min(ths) + max(ths)) / 2
            for v, th in zip(vs, ths):
                rv0 = rho_on(VOL0, th, v.co.z)
                th2 = thc + (th - thc) * ratio
                rv1 = rho_on(VOL0, th2, v.co.z)
                if rv0 is None or rv1 is None:
                    continue
                v.co = Vector((0, H.AX_Y, v.co.z)) + dirv(th2) * (rv1 + (rho_of(v.co) - rv0)); converged += 1
    bm.to_mesh(o.data); bm.free(); o.data.update()

# ------------------------------------------------------------------ 1. back layers
BACK = [  # (th_a, th_b, z_top, extra length below the volume edge, offset)
    (128.0, 160.0, 1.56, 0.010, 0.0030),
    (150.0, 186.0, 1.60, 0.016, 0.0046),
    (176.0, 211.0, 1.59, 0.009, 0.0036),
    (201.0, 233.0, 1.57, 0.013, 0.0052),
    (164.0, 197.0, 1.45, 0.018, 0.0062),       # short layer from mid back, on top
]


def back_layer(bm, uvl, cl, th_a, th_b, z_top, extra, off, rand, nr=38, nc=9, tip=0.28, root=0.45):
    thc = (th_a + th_b) / 2
    z_bot = min(zmin.get(int(thc % 360 if thc <= 180 else thc - 360) // 5, 1.17), 1.21) - extra
    last = [None] * nc
    vs = []
    for r in range(nr):
        t = r / (nr - 1); z = z_top + (z_bot - z_top) * t
        k = smooth01((t - (1 - tip)) / tip); q = smooth01(t / root)
        h = (th_b - th_a) / 2 * (1 - 0.62 * k) * (0.06 + 0.94 * q)          # roots converge, no top edge
        row = []
        for j in range(nc):
            th = thc - h + 2 * h * j / (nc - 1)
            rv = rho_on(VOL, th, z)
            if rv is None:                                    # below the volume edge: keep hanging, curl in a little
                base = last[j] if last[j] is not None else 0.15
                rv = base - 0.25 * max(0.0, (z_bot + extra) - z)
            else:
                last[j] = rv
            o = off * q * q
            row.append(bm.verts.new(Vector((0, H.AX_Y, z)) + dirv(th) * (rv + o + 0.0006)))
        vs.append(row)
    for r in range(nr - 1):
        for j in range(nc - 1):
            f = bm.faces.new((vs[r][j], vs[r][j + 1], vs[r + 1][j + 1], vs[r + 1][j]))
            for loop, (jj, rr) in zip(f.loops, [(j, r), (j + 1, r), (j + 1, r + 1), (j, r + 1)]):
                loop[uvl].uv = (jj / (nc - 1), rr / (nr - 1)); loop[cl] = (1.0, rand, rr / (nr - 1), 1.0)
    return z_bot


bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); cl = bm.loops.layers.color.new("Col")
tips = [round(back_layer(bm, uvl, cl, *spec, rng.random()), 4) for spec in BACK]
H.orient_outward(bm)
back = H.mesh_object("hair_bob_01__Back", bm, coll)
H.apply_solidify(back, 0.003, -1.0, True)
back.data.materials.append(bpy.data.materials["M_hair_bob_01_01"])


# ------------------------------------------------------------------ 4. material: strand streaks + soft flow highlight
def flow_material(m):
    nt = m.node_tree; L = nt.links.new
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    em = next(n for n in nt.nodes if n.type == "EMISSION")
    hc = next(n for n in nt.nodes if n.type == "RGB")
    bw = next(n for n in nt.nodes if n.type == "RGBTOBW")
    src = em.inputs["Color"].links[0].from_socket                   # toon x HairColor x AO
    geo = nt.nodes.new("ShaderNodeNewGeometry"); xyz = nt.nodes.new("ShaderNodeSeparateXYZ"); L(geo.outputs["Position"], xyz.inputs[0])
    by = nt.nodes.new("ShaderNodeMath"); by.operation = "SUBTRACT"; by.inputs[0].default_value = H.AX_Y; L(xyz.outputs["Y"], by.inputs[1])
    ang = nt.nodes.new("ShaderNodeMath"); ang.operation = "ARCTAN2"; L(xyz.outputs["X"], ang.inputs[0]); L(by.outputs[0], ang.inputs[1])
    w1 = nt.nodes.new("ShaderNodeMath"); w1.operation = "MULTIPLY"; w1.inputs[1].default_value = 38.0; L(ang.outputs[0], w1.inputs[0])
    w2 = nt.nodes.new("ShaderNodeMath"); w2.operation = "MULTIPLY_ADD"; w2.inputs[1].default_value = 6.0; L(xyz.outputs["Z"], w2.inputs[0]); L(w1.outputs[0], w2.inputs[2])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.noise_dimensions = "1D"; L(w2.outputs[0], nz.inputs["W"])
    nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 3.0; nz.inputs["Roughness"].default_value = 0.55
    st = nt.nodes.new("ShaderNodeMapRange"); st.inputs["From Min"].default_value = 0.32; st.inputs["From Max"].default_value = 0.68
    L(nz.outputs["Fac"], st.inputs["Value"])
    # streaks: up to 12 % darker between strands
    dk = nt.nodes.new("ShaderNodeMath"); dk.operation = "MULTIPLY_ADD"; dk.inputs[1].default_value = 0.12; dk.inputs[2].default_value = 0.88
    L(st.outputs["Result"], dk.inputs[0])
    base = nt.nodes.new("ShaderNodeMix"); base.data_type = "RGBA"; base.blend_type = "MULTIPLY"; base.inputs["Factor"].default_value = 1.0
    L(src, base.inputs["A"]); L(dk.outputs[0], base.inputs["B"])
    # highlight band around z 1.565, its centre moved up / down by the streaks, soft edges
    zc = nt.nodes.new("ShaderNodeMath"); zc.operation = "MULTIPLY_ADD"; zc.inputs[1].default_value = -0.018; zc.inputs[2].default_value = 0.009 - 1.565
    L(st.outputs["Result"], zc.inputs[0])
    dz = nt.nodes.new("ShaderNodeMath"); dz.operation = "ADD"; L(xyz.outputs["Z"], dz.inputs[0]); L(zc.outputs[0], dz.inputs[1])
    adz = nt.nodes.new("ShaderNodeMath"); adz.operation = "ABSOLUTE"; L(dz.outputs[0], adz.inputs[0])
    band = nt.nodes.new("ShaderNodeMapRange"); band.inputs["From Min"].default_value = 0.003; band.inputs["From Max"].default_value = 0.014
    band.inputs["To Min"].default_value = 1.0; band.inputs["To Max"].default_value = 0.0; L(adz.outputs[0], band.inputs["Value"])
    lit = nt.nodes.new("ShaderNodeMapRange"); lit.inputs["From Min"].default_value = 0.42; lit.inputs["From Max"].default_value = 0.6
    L(bw.outputs[0], lit.inputs["Value"])
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.4
    face = nt.nodes.new("ShaderNodeMath"); face.operation = "SUBTRACT"; face.inputs[0].default_value = 1.0; L(lw.outputs["Facing"], face.inputs[1])
    sw = nt.nodes.new("ShaderNodeMath"); sw.operation = "MULTIPLY_ADD"; sw.inputs[1].default_value = 0.65; sw.inputs[2].default_value = 0.35
    L(st.outputs["Result"], sw.inputs[0])
    f = band.outputs["Result"]
    for other in (lit.outputs["Result"], face.outputs[0], sw.outputs[0]):
        m_ = nt.nodes.new("ShaderNodeMath"); m_.operation = "MULTIPLY"; L(f, m_.inputs[0]); L(other, m_.inputs[1]); f = m_.outputs[0]
    k = nt.nodes.new("ShaderNodeMath"); k.operation = "MULTIPLY"; k.inputs[1].default_value = 0.5; L(f, k.inputs[0])
    hl_col = nt.nodes.new("ShaderNodeMix"); hl_col.data_type = "RGBA"; hl_col.inputs["Factor"].default_value = 0.45
    L(hc.outputs[0], hl_col.inputs["A"]); hl_col.inputs["B"].default_value = (1, 1, 1, 1)
    hl = nt.nodes.new("ShaderNodeMix"); hl.data_type = "RGBA"
    L(k.outputs[0], hl.inputs["Factor"]); L(base.outputs["Result"], hl.inputs["A"]); L(hl_col.outputs["Result"], hl.inputs["B"])
    L(hl.outputs["Result"], em.inputs["Color"])


flow_material(bpy.data.materials["M_hair_bob_01_01"])

names = ["hair_bob_01__Volume", "hair_bob_01__Bangs", "hair_bob_01__Side_L", "hair_bob_01__Side_R", "hair_bob_01__Back"]
H.bake_ao([bpy.data.objects[n] for n in names], names + ["Blockout_Head", "Blockout_Neck", "Blockout_Torso", "Face_Ear.L", "Face_Ear.R"])
H.add_outline(back, 0.0008)
stats = dict(back_layer_tips_z=tips, temple_vertices_tucked=tucked, side_root_vertices_flushed=flushed, side_root_vertices_converged=converged, volume_vertices_pushed_under_bangs=lifted, hem_wave_m=WAVE,
             objects={n: dict(verts=len(bpy.data.objects[n].data.vertices),
                              tris=sum(len(p.vertices) - 2 for p in bpy.data.objects[n].data.polygons)) for n in names})
json.dump(stats, open(os.path.join(H.EXP, "spec", "hair_v5f_stats.json"), "w"), indent=1)
print("V5F", json.dumps(stats))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H.EXP, "MG_ToonTest_01_v5f_finish.blend"))
print("V5F_OK")
