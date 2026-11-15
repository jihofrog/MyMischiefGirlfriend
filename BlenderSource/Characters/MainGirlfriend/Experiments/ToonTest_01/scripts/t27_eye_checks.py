"""ToonTest_01 step 27 (Blender, background, read only): eye structure measurements for one variant.

usage: Blender -b <file.blend> --python t27_eye_checks.py -- <tag>
Writes spec/eye_checks_<tag>.json (per eye L / R, mm; front projection = r30 canvas). Run on v5g first: it stores the
v5g skin depth grid (spec/eye_skin_v5g.json) that the other variants are measured against.
  eye_vs_face        visible eye surface (white / eyeball) inside the r30 opening vs the ORIGINAL v5g skin at the same
                     point (+ = in front of the face surface = sticks out)
  eye_below_ring     eye surface 2 mm inside the opening vs the current skin 5 mm outside it (+ = eye sits deeper)
  iris_sagitta       bulge of the iris surface over its own flat plane (lens look), iris over white
  upper_lid_edge     lid / lash front 0.8 mm above the r30 lid line vs the eye surface 0.8 mm below it (lid thickness)
  lower_lid_step     skin / lid 1.2 mm below the opening vs the eye surface 1.2 mm inside it (+ = a real lid edge)
  lower_lash_gap     lower lash vertices to the skin
  b_pokes            (B) eyeball points outside the socket that come in front of the skin; lid sheets inside the
                     eyeball at Blink 0 / 0.5 / 1, EyeSmile 1
  tris / draws       eye related meshes as exported (visible, curves as meshes)
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
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
tag = sys.argv[sys.argv.index("--") + 1]
B = "Eye_Ball.L" in bpy.data.objects
vis = [o for o in bpy.data.objects if o.type in ("MESH", "CURVE") and not o.hide_render and o.visible_get()]
names = [o.name for o in vis]


def role(n):
    if n.startswith("Eye_Ball") or n.startswith("Eye_White"):
        return "eye"
    if n.startswith("Eye_Iris"):
        return "iris"
    if n.startswith("Eye_Lids") or n.startswith("Blockout_Head"):
        return "skin"
    if n.startswith("Eye_Lash") or any(k in n for k in ("UpperLid", "Lashes", "OuterLine")):
        return "lash"
    return "other"


def bvh(role_names):
    ns = [n for n in names if role(n) in role_names and bpy.data.objects[n].type == "MESH"]
    return E.bvh_of(ns) if ns else None


EYE = bvh(("eye",))
IRIS = bvh(("iris",))
SKIN = bvh(("skin",))
LID = bvh(("lash", "skin"))
HEAD = E.bvh_of(["Blockout_Head"])
out = {"tag": tag, "method": "B" if B else ("A" if tag != "v5g" else "v5g")}

skin_path = os.path.join(EXP, "spec", "eye_skin_v5g.json")
grid = {}
for s in E.SIDES:
    poly = E.opening_poly(s)
    x0, z0 = poly.min(0)
    x1, z1 = poly.max(0)
    gx, gz = np.meshgrid(np.arange(x0, x1, 0.001), np.arange(z0, z1, 0.001))
    G = np.stack([gx.ravel(), gz.ravel()], 1)
    grid[s] = G[E.signed_dist(G, poly) < -0.001]
if tag == "v5g":
    json.dump({s: [E.front_hit(HEAD, x, z)[0] for x, z in grid[s]] for s in E.SIDES}, open(skin_path, "w"))
orig = json.load(open(skin_path))


def y_of(b, x, z):
    if b is None:
        return np.nan
    y, _ = E.front_hit(b, x, z)
    return np.nan if y is None else y


def stat(a):
    a = np.asarray(a, float)
    a = a[~np.isnan(a)]
    if not len(a):
        return None
    return dict(min=round(float(a.min()) * 1000, 2), med=round(float(np.median(a)) * 1000, 2), max=round(float(a.max()) * 1000, 2))


for s in E.SIDES:
    poly = E.opening_poly(s)
    res = {}
    ye = np.array([y_of(EYE, x, z) for x, z in grid[s]])
    yo = np.array([np.nan if v is None else v for v in orig[s]])
    res["eye_vs_face"] = stat(yo - ye)
    # ring: contour points pushed out / in along the outline normal (2D)
    c = poly.mean(0)
    ring = []
    for p in poly[::4]:
        n = (p - c) / np.linalg.norm(p - c)
        pi, po = p - n * 0.002, p + n * 0.005
        ring.append(y_of(EYE, *pi) - y_of(SKIN, *po))
    res["eye_below_ring"] = stat(ring)
    # iris
    ib = E.TGT[s]["iris_bbox"]
    ic = np.array([E.X((ib[0] + ib[2]) / 2), E.Z((ib[1] + ib[3]) / 2)])
    irx, irz = (ib[2] - ib[0]) / 2 / E.PPM * 0.8, (ib[3] - ib[1]) / 2 / E.PPM * 0.8
    pts = [(x, z) for x, z in grid[s] if ((x - ic[0]) / irx) ** 2 + ((z - ic[1]) / irz) ** 2 < 1]
    src = IRIS if IRIS is not None else EYE
    yi = np.array([y_of(src, x, z) for x, z in pts])
    P = np.array([(x, z, y) for (x, z), y in zip(pts, yi) if not np.isnan(y)])
    if len(P) > 10:
        A = np.c_[P[:, 0], P[:, 1], np.ones(len(P))]
        coef, *_ = np.linalg.lstsq(A, P[:, 2], rcond=None)
        dev = P[:, 2] - A @ coef
        res["iris_sagitta_mm"] = round(float(dev.max() - dev.min()) * 1000, 2)
        yo_i = np.array([np.nan if v is None else v for v, (x, z) in zip(orig[s], grid[s])
                         if ((x - ic[0]) / irx) ** 2 + ((z - ic[1]) / irz) ** 2 < 1])
        res["iris_over_face"] = stat(yo_i - yi)
        if IRIS is not None:
            yw = np.array([y_of(EYE, x, z) for x, z in pts])
            res["iris_over_white_mm"] = stat(yw - yi)
    # lids, per column over the middle 60 % of the opening
    oc, lc = E.cols(s, "opening_cols"), E.cols(s, "lash_cols")
    xs = sorted(oc)
    mid = xs[int(len(xs) * 0.2): int(len(xs) * 0.8)]
    up, lo = [], []
    for x in mid[::3]:
        if x not in lc:
            continue
        zl = float(E.Z(lc[x][1]))
        up.append(y_of(EYE, float(E.X(x)), zl - 0.0008) - y_of(LID, float(E.X(x)), zl + 0.0008))
        zb = float(E.Z(oc[x][1]))
        lo.append(y_of(EYE, float(E.X(x)), zb + 0.0012) - y_of(SKIN, float(E.X(x)), zb - 0.0012))
    res["upper_lid_edge"] = stat(up)
    res["lower_lid_step"] = stat(lo)
    ll = [n for n in names if (n.startswith("Face_LowerLashes") and n.endswith(s))]
    if ll:
        o = bpy.data.objects[ll[0]]
        d = [HEAD.find_nearest(o.matrix_world @ v.co)[3] for v in o.data.vertices]
        res["lower_lash_gap"] = stat(d)
    elif B:
        o = bpy.data.objects[f"Eye_Lash.{s}"]
        lo_box = E.TGT[s]["lower_lash_bbox"]
        vs = [o.matrix_world @ v.co for v in o.data.vertices]
        vs = [v for v in vs if E.X(lo_box[0] - 2) <= v.x <= E.X(lo_box[2] + 2) and E.Z(lo_box[3] + 2) <= v.z <= E.Z(lo_box[1] - 2)]
        res["lower_lash_gap"] = stat([HEAD.find_nearest(v)[3] for v in vs])
    if B:
        sph = E.Spheroid(**json.loads(bpy.data.objects[f"Eye_Ball.{s}"]["mmg_spheroid"]))
        ball = bpy.data.objects[f"Eye_Ball.{s}"]
        bv = np.array([tuple(ball.matrix_world @ v.co) for v in ball.data.vertices])
        sd = E.signed_dist(bv[:, [0, 2]], poly)
        poke = 0
        for p, r in zip(bv, sd):
            if r > 0.004:
                y, _ = E.front_hit(HEAD, p[0], p[2])
                if y is not None and y > p[1] + 1e-5:
                    poke += 1
        res["eyeball_in_front_of_skin_outside_socket"] = poke
        lid = bpy.data.objects[f"Eye_Lids.{s}"]
        inside = {}
        for kname, val in (("Basis", 0), ("Blink", 0.5), ("Blink", 1.0), ("EyeSmile", 1.0), ("Smile", 1.0), ("Surprise", 1.0)):
            E.set_keys("Blink", 0); E.set_keys("EyeSmile", 0); E.set_keys("Smile", 0); E.set_keys("Surprise", 0)
            if kname != "Basis":
                E.set_keys(kname, val)
            vs, _ = E.world_mesh(lid)
            P = np.array([tuple(v) for v in vs])
            q = ((P[:, 0] - sph.c[0]) ** 2 + (P[:, 1] - sph.c[1]) ** 2) / sph.R ** 2 + ((P[:, 2] - sph.c[2]) / sph.C) ** 2
            inside[f"{kname}_{val}"] = int((q < 1 - 1e-6).sum())
        E.set_keys("Blink", 0); E.set_keys("EyeSmile", 0); E.set_keys("Smile", 0); E.set_keys("Surprise", 0)
        res["lid_verts_inside_eyeball"] = inside
    out[s] = res

# sections through the left eye (iris centre): front-most surface per role along +y
ib = E.TGT["L"]["iris_bbox"]
cx, cz = float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2))
OTHER = bvh(("other",))
sec = {"centre": [cx, cz], "vertical": {}, "horizontal": {}}
for rn, b in (("skin", SKIN), ("eye", EYE), ("iris", IRIS), ("lash", bvh(("lash",)))):
    if b is None:
        continue
    sec["vertical"][rn] = [(float(z), y_of(b, cx, z)) for z in np.arange(cz - 0.04, cz + 0.045, 0.00025)]
    sec["horizontal"][rn] = [(float(x), y_of(b, x, cz)) for x in np.arange(cx - 0.05, cx + 0.06, 0.00025)]
sec["orig_skin_vertical"] = [(float(z), y_of(HEAD, cx, z)) for z in np.arange(cz - 0.04, cz + 0.045, 0.00025)] if not B else None
json.dump(sec, open(os.path.join(EXP, "spec", f"eye_section_{tag}.json"), "w"))

# cost: eye related meshes as they go to the FBX (curves converted)
dg = bpy.context.evaluated_depsgraph_get()
eye_objs = [o for o in vis if role(o.name) in ("eye", "iris", "lash") or o.name.startswith("Eye_") or "Lashes" in o.name]
cost = {}
for o in eye_objs:
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    cost[o.name] = dict(tris=sum(len(p.vertices) - 2 for p in me.polygons), verts=len(me.vertices),
                        mats=len([s for s in o.material_slots if s.material]))
    ev.to_mesh_clear()
head = bpy.data.objects["Blockout_Head"]
head.modifiers["TT_Outline"].show_viewport = False
dg.update()
ev = head.evaluated_get(dg)
me = ev.to_mesh()
out["head_tris"] = sum(len(p.vertices) - 2 for p in me.polygons)
ev.to_mesh_clear()
out["eye_cost"] = dict(objects=len(cost), tris=sum(c["tris"] for c in cost.values()), draws=sum(c["mats"] for c in cost.values()),
                       detail=cost)
out["shape_keys"] = {o.name: [k.name for k in o.data.shape_keys.key_blocks[1:]] for o in vis
                     if o.type == "MESH" and o.data.shape_keys}
json.dump(out, open(os.path.join(EXP, "spec", f"eye_checks_{tag}.json"), "w"), indent=1)
print("EYE_CHECKS", json.dumps({k: v for k, v in out.items() if k in ("L", "R", "head_tris")}))
print("EYE_COST", json.dumps({k: v for k, v in out["eye_cost"].items() if k != "detail"}))
