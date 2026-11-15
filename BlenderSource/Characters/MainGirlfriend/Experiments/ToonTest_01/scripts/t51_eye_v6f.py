"""ToonTest_01 step 51 (Blender, background): v6f candidates from v6d_3 (the source .blend is not changed).

usage: V6F_A=1 [V6F_B=1] [V6F_CAP=52] V6F_OUT=<file.blend> Blender -b MG_ToonTest_01_v6d_3.blend --python t51_eye_v6f.py
Every change moves vertices along y only (the front view keeps its outlines), in every shape key with its own x / z,
the same way on both eyes. Heights are measured along y above the eyeball surface.
  A  lid boundary: the lid sheet edge sits closer to the eyeball (skirt 1.1 -> 0.35 mm, edge 1.5 -> 0.7 mm, back to the
     old height over two rows under the rim), the bottom rows of the lash band follow (1 mm lower, kept 0.3 mm above the
     lid sheet under them) and the lower lash inside the socket too: less lid / skin between lashes and eyeball when the
     view turns.
  B  A + outer wrap: the eyeball surface between the iris and the outer corner turns outward too steeply (61-64 deg at
     the corner, so at 35 / 45 deg its far side horizon is 7 / 17 mm inside the opening and the bare socket rim shows
     between eyeball and lashes). Per height, the slope toward the outer corner is capped (V6F_CAP deg, corner depth
     kept, the depth difference taken up between the iris and the cap zone): the middle of the outer half goes back up
     to a few mm, the iris and the corner stay. Lids, lash rows on the eyeball and the socket skin behind the eyeball
     follow; the rim and the face do not move.
Writes the .blend and spec/eye_<name>_stats.json.
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
assert os.path.basename(bpy.data.filepath) == "MG_ToonTest_01_v6d_3.blend"
DO_A = os.environ.get("V6F_A", "1") == "1"
DO_B = os.environ.get("V6F_B", "0") == "1"
CAP = float(os.environ.get("V6F_CAP", 56))
LASH = os.environ.get("V6F_LASH", "1") == "1"
FWD = float(os.environ.get("V6F_FWD", 0.0))         # B: share of the outer depth taken by bringing the corner forward        # A: lower the lash rows on the eyeball too
OUT = os.environ["V6F_OUT"]
O = bpy.data.objects
stats = dict(a=DO_A, b=DO_B, cap_deg=CAP if DO_B else None, lash=LASH, fwd=FWD if DO_B else None)


def blocks(o):
    return list(o.data.shape_keys.key_blocks) if o.data.shape_keys else []


def set_y(o, fn):
    """y = fn(world points, block name) for the mesh and every shape key"""
    mw, mi = o.matrix_world, o.matrix_world.inverted()
    srcs = [(kb.name, kb.data) for kb in blocks(o)] + [("__mesh__", o.data.vertices)]
    for name, src in srcs:
        P = np.array([tuple(mw @ v.co) for v in src])
        Y = fn(P, name)
        for v, p, y in zip(src, P, Y):
            if abs(y - p[1]) > 1e-9:
                v.co = mi @ Vector((p[0], y, p[2]))
    o.data.update()


def ball_y(bvh, P):
    out = np.full(len(P), np.nan)
    for i, p in enumerate(P):
        y, _ = E.front_hit(bvh, p[0], p[2])
        if y is not None:
            out[i] = y
    return out


def blend_lift(s, BALL):
    """in-between key values move the lid edges on straight lines across the curved eyeball: lift a vertex (in every
    key) until no blend of the keys (0.25 / 0.5 / 0.75, Smile + EyeSmile together) is within 0.1 mm of the surface"""
    lids = O[f"Eye_Lids.{s}"]
    mw, mi = lids.matrix_world, lids.matrix_world.inverted()
    kbs = lids.data.shape_keys.key_blocks
    K = {kb.name: np.array([tuple(mw @ d.co) for d in kb.data]) for kb in kbs}
    P0 = K["Basis"]
    mixes = [{k: t} for k in K if k != "Basis" for t in (0.25, 0.5, 0.75)]
    mixes += [{"Smile": t, "EyeSmile": t} for t in (0.5, 1.0)] + [{"Smile": 1.0, "EyeSmile": 0.5}, {"Smile": 0.5, "EyeSmile": 1.0}]
    lift = np.zeros(len(P0))
    for mx in mixes:
        Pm = P0 + sum(t * (K[k] - P0) for k, t in mx.items())
        ys = ball_y(BALL, Pm)
        need = Pm[:, 1] - (ys - 0.0001)              # > 0: this blend is less than 0.1 mm above the eyeball
        lift = np.maximum(lift, np.where(np.isfinite(need), need, 0.0))
    lift[lift < 1e-6] = 0.0
    for kb in kbs:
        for d, l in zip(kb.data, lift):
            if l > 0:
                p = mw @ d.co
                d.co = mi @ Vector((p.x, p.y - l, p.z))
    for v, d in zip(lids.data.vertices, kbs["Basis"].data):
        v.co = d.co.copy()
    lids.data.update()
    stats.setdefault("lid_lift_for_blends", []).append(dict(side=s, verts=int((lift > 0).sum()), max_mm=round(float(lift.max()) * 1000, 2)))


# ------------------------------------------------------------------ A: lid boundary
if DO_A:
    for s in E.SIDES:
        BALL = E.bvh_of([f"Eye_Ball.{s}"])
        lids, lash = O[f"Eye_Lids.{s}"], O[f"Eye_Lash.{s}"]
        nc = len(lids.data.vertices) // 14
        row = np.arange(len(lids.data.vertices)) % 7
        target = {0: 0.00035, 1: 0.0007, 2: 0.0010, 3: 0.0013}

        def lid_fn(P, name):
            yb = ball_y(BALL, P)
            h = yb - P[:, 1]
            Y = P[:, 1].copy()
            for r, t in target.items():
                k = (row == r) & np.isfinite(h) & (h > t)
                Y[k] = yb[k] - t
            return Y
        set_y(lids, lid_fn)
        blend_lift(s, BALL)
        LIDB = E.bvh_of([f"Eye_Lids.{s}"])          # the new sheets (Basis): the lash must stay in front of them
        nb, nr, cs = int(lash["mmg_band_cols"]), int(lash["mmg_band_rows"]), int(lash["mmg_crease_start"])
        nv = len(lash.data.vertices)
        brow = np.full(nv, -1)
        brow[:nb * nr] = np.arange(nb * nr) % nr
        drop = np.zeros(nv)
        drop[brow == 0] = 0.0008                     # skirt
        drop[brow == 1] = 0.0010
        drop[brow == 2] = 0.0007
        drop[brow == 3] = 0.0003
        drop[nb * nr:cs] = 0.0010                    # lower lash
        lid_poses = {}

        def lash_fn(P, name):
            yb = ball_y(BALL, P)
            h = yb - P[:, 1]
            Y = P[:, 1].copy()
            # only where the lash lies over the eyeball inside the socket (not on the rim / face skin)
            ins = np.isfinite(h) & (h < 0.0028) & (drop > 0)
            ys = ball_y(LIDB, P)                     # lid sheet in front of the eyeball at this x, z (if any)
            for i in np.nonzero(ins)[0]:
                y_new = P[i, 1] + drop[i]
                lim = yb[i] - 0.0002                 # never onto the eyeball
                if np.isfinite(ys[i]) and ys[i] < yb[i] - 1e-5:
                    lim = min(lim, ys[i] - 0.0003)   # stay 0.3 mm in front of the lid sheet
                Y[i] = min(y_new, max(P[i, 1], lim))
            return Y
        if LASH:
            set_y(lash, lash_fn)
    stats["A"] = dict(lid_height_mm={"skirt": 0.35, "edge": 0.7, "row2": 1.0, "row3": 1.3},
                      lash_drop_mm=dict(skirt=0.8, row1=1.0, row2=0.7, row3=0.3, lower_lash=1.0))

# ------------------------------------------------------------------ B: outer wrap (slope cap toward the outer corner)
if DO_B:
    cap = math.tan(math.radians(CAP))
    FIELD = {}
    for s in E.SIDES:
        sg = 1 if s == "L" else -1
        BALL = E.bvh_of([f"Eye_Ball.{s}"])
        lids = O[f"Eye_Lids.{s}"]
        nc = len(lids.data.vertices) // 14
        V = np.array([tuple(lids.matrix_world @ kv.co) for kv in lids.data.shape_keys.key_blocks["Basis"].data])
        up, lo = V[:nc * 7].reshape(nc, 7, 3)[:, 1], V[nc * 7:].reshape(nc, 7, 3)[:, 1]
        ib = E.TGT[s]["iris_bbox"]
        xc, zc = float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2))
        opn = [(sg * (u[0] - xc), l[2], u[2]) for u, l in zip(up, lo) if u[2] - l[2] > 0.0005]
        z_lo, z_hi = min(o[1] for o in opn), max(o[2] for o in opn)
        us = np.arange(-0.01, 0.07, 0.001)
        zs = np.arange(z_lo - 0.008, z_hi + 0.008, 0.001)
        D = np.zeros((len(zs), len(us)))
        U0 = 0.008                                   # iris side: unchanged up to here
        for i, z in enumerate(zs):
            zz = min(max(z, z_lo + 0.001), z_hi - 0.001)
            oc = [o[0] for o in opn if o[1] < zz < o[2]]
            if not oc:
                continue
            uc = max(oc)                             # outer end of the opening at this height
            yb = ball_y(BALL, np.stack([xc + sg * us, np.zeros_like(us), np.full_like(us, z)], 1))
            if not np.isfinite(yb).all():
                ok = np.isfinite(yb)
                if ok.sum() < 10:
                    continue
                yb = np.interp(us, us[ok], yb[ok])
            sl = np.gradient(yb, 0.001)              # + = going back toward the outer side
            zone = (us >= U0) & (us <= uc + 0.002)
            excess = np.where(zone, np.maximum(sl - cap, 0.0), 0.0)
            deficit = excess.sum() * 0.001
            if deficit <= 0:
                continue
            room = np.where(zone & (sl < cap), cap - sl, 0.0) * np.clip((us - U0) / 0.006, 0, 1)
            add = np.zeros_like(sl)
            if room.sum() > 0:
                add = np.minimum(room / (room.sum() * 0.001) * deficit * (1 - FWD), room)
            sl2 = sl - excess + add
            y2 = yb[0] + np.concatenate([[0], np.cumsum((sl2[1:] + sl2[:-1]) / 2 * 0.001)])
            d = y2 - yb                               # + = back, - = forward (corner share FWD)
            ic = int(np.argmin(np.abs(us - uc)))
            # past the corner (under the rim): back to the old surface over 4 mm (6 mm when the corner came forward)
            fade = 0.004 if FWD <= 0 else 0.006
            past = us > uc
            d[past] = d[ic] * np.clip(1 - (us[past] - uc) / fade, 0, 1)
            if FWD <= 0:
                d = np.maximum(d, 0.0)
            # above / below the opening: fade over 6 mm
            w = np.clip(1 - max(z_lo - z, z - z_hi, 0) / 0.006, 0, 1)
            D[i] = d * w
        k = np.exp(-0.5 * (np.arange(-6, 7) / 2.0) ** 2)
        k /= k.sum()
        D = np.apply_along_axis(lambda v: np.convolve(np.pad(v, 6, mode="edge"), k, mode="valid"), 0, D)
        D = np.apply_along_axis(lambda v: np.convolve(np.pad(v, 6, mode="edge"), k, mode="valid"), 1, D)
        FIELD[s] = (sg, xc, us, zs, D)
        stats[f"B_back_mm_max_{s}"] = round(float(D.max()) * 1000, 2)
        stats[f"B_forward_mm_max_{s}"] = round(float(-D.min()) * 1000, 2)

    def field(P):
        out = np.zeros(len(P))
        for s, (sg, xc, us, zs, D) in FIELD.items():
            u = sg * (P[:, 0] - xc)
            ok = (u > us[0]) & (u < us[-1]) & (P[:, 2] > zs[0]) & (P[:, 2] < zs[-1])
            k = np.nonzero(ok)[0]
            fu, fz = (u[k] - us[0]) / 0.001, (P[k, 2] - zs[0]) / 0.001
            i0, j0 = np.clip(np.floor(fz).astype(int), 0, len(zs) - 2), np.clip(np.floor(fu).astype(int), 0, len(us) - 2)
            tz, tu = fz - i0, fu - j0
            out[k] += (D[i0, j0] * (1 - tz) * (1 - tu) + D[i0 + 1, j0] * tz * (1 - tu) + D[i0, j0 + 1] * (1 - tz) * tu
                       + D[i0 + 1, j0 + 1] * tz * tu)
        return out

    BALLS = {s: E.bvh_of([f"Eye_Ball.{s}"]) for s in E.SIDES}

    def ball_any(P):
        y = np.full(len(P), np.nan)
        for s in E.SIDES:
            yy = ball_y(BALLS[s], P)
            m = np.isfinite(yy) & ~np.isfinite(y)
            y[m] = yy[m]
        return y

    # the eyeball, the lid sheets, lash rows lying on the eyeball (h < 2.8 mm, fading to 3.4 mm) and the socket skin
    # behind the eyeball move back together; skin and lashes on the rim / face stay
    for s in E.SIDES:
        set_y(O[f"Eye_Ball.{s}"], lambda P, n: P[:, 1] + field(P))
        set_y(O[f"Eye_Lids.{s}"], lambda P, n: P[:, 1] + field(P))

        def lash_fn(P, n):
            h = ball_any(P) - P[:, 1]
            w = np.where(np.isfinite(h), np.clip((0.0034 - h) / 0.0006, 0, 1), 0.0)
            d = field(P)
            return P[:, 1] + np.where(d < 0, d, d * w)            # forward: everything over the corner comes along
        set_y(O[f"Eye_Lash.{s}"], lash_fn)

    def head_fn(P, n):
        h = ball_any(P) - P[:, 1]                      # + = skin in front of the eyeball
        w = np.where(np.isfinite(h), np.clip((0.0005 - h) / 0.0015, 0, 1), 0.0)   # behind the eyeball: 1, rim: 0
        d = field(P)
        return P[:, 1] + np.where(d < 0, d, d * w)
    set_y(O["Blockout_Head"], head_fn)

if DO_B:
    for s in E.SIDES:
        blend_lift(s, E.bvh_of([f"Eye_Ball.{s}"]))

# ------------------------------------------------------------------ hair penetration (face band) after the change
HEADB = E.bvh_of(["Blockout_Head"])


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


pen = 0
for o in bpy.data.collections["hair_bob_01"].objects:
    if o.type != "MESH" or o.name.endswith("_ref"):
        continue
    src = O["hair_bob_01__Volume_outer_ref"] if o.name == "hair_bob_01__Volume" else o
    for v in src.data.vertices:
        p = src.matrix_world @ v.co
        if abs(p.x) > 0.16 or p.z < 1.28 or p.z > 1.52 or p.y > 0.0:
            continue
        loc, nrm, _, _ = HEADB.find_nearest(p, 0.05)
        if loc is not None and (p - loc).dot(nrm) < -1e-4 and inside(HEADB, p):
            pen += 1
stats["hair_penetration_face_band"] = pen

name = os.path.splitext(OUT)[0].replace("MG_ToonTest_01_", "")
json.dump(stats, open(os.path.join(EXP, "spec", f"eye_{name}_stats.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, OUT))
print("V6F_OK", json.dumps(stats))
