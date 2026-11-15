"""ToonTest_01 step 70 (Blender, background): v6i from v6f_A - view-angle correction keys ViewFarL / ViewFarR.

usage: V6I_K=<0..1> V6I_OUT=<file.blend> Blender -b MG_ToonTest_01_v6f_A.blend --python t70_eye_v6i.py
Basis (the front) and the old keys are not changed. ViewFar<s> folds the outer part of eye <s> toward the iris, for the
time that eye is the far eye (weight: eye_v6_common.view_far_weights, 0 below 20 deg, 1 from 40 deg). It is stored as
N stage keys ViewFar<s>_1..N (eye_v6_common.view_stage_values), each the step to the true shape at i / N, so in-between
weights follow the curved path instead of a straight line through the eyeball:
  - per row of the r30 opening, u (distance from the iris centre toward the outer corner) -> K u up to the outer opening
    edge U(z), so the upper and lower lid lines meet K U from the iris centre; past the corner the shift fades out over
    FADE_U (skin of the eye tail and temple stretches), above / below the eye over FADE_Z
  - the lid sheets, the lash mesh (band, lower lash, crease) and the head skin take the same displacement at the same
    (x, z): sideways shift, then the depth of the front surface of eyeball + head at the new place minus the old one,
    plus LIFT toward the viewer where something moved (the head skin of the eye tail lands on the eyeball 0.2 mm over
    it). Being the same field for every object, their front-to-back order stays as in Basis.
  - the eyeball is not changed (no step, gaze texture as before).
Then, in the stage keys only, the lid sheets and the lash are lifted until every blend of ViewFar (0.1 steps) with Blink,
EyeSmile, Smile + EyeSmile, Surprise stays 0.1 mm over the eyeball. Writes the .blend and spec/eye_<name>_stats.json.
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
assert os.path.basename(bpy.data.filepath) == "MG_ToonTest_01_v6f_A.blend"
K = float(os.environ.get("V6I_K", 0.55))
N = int(os.environ.get("V6I_N", 3))
OUT = os.environ["V6I_OUT"]
FADE_U = 0.030
FADE_Z0, FADE_Z1 = 0.006, 0.018
LIFT = 0.0002
O = bpy.data.objects
stats = dict(k=K, stages=N, fade_u_mm=FADE_U * 1000, fade_z_mm=[FADE_Z0 * 1000, FADE_Z1 * 1000], lift_mm=LIFT * 1000)


def sm(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def ball_y(bvh, P):
    out = np.full(len(P), np.nan)
    for i, p in enumerate(P):
        y, _ = E.front_hit(bvh, p[0], p[2])
        if y is not None:
            out[i] = y
    return out


class Field:
    def __init__(self, s):
        ib = E.TGT[s]["iris_bbox"]
        self.sg = 1 if s == "L" else -1
        self.xc = float(E.X((ib[0] + ib[2]) / 2))
        poly = E.opening_poly(s)
        self.z0, self.z1 = poly[:, 1].min(), poly[:, 1].max()
        zs = np.linspace(self.z0, self.z1, 160)
        u = np.arange(0.0, 0.09, 0.0001)
        U = []
        for z in zs:
            inside = E.signed_dist(np.stack([self.xc + self.sg * u, np.full_like(u, z)], 1), poly) < 0
            U.append(u[np.nonzero(inside)[0].max()] if inside.any() else 0.0)
        self.zs, self.U = zs, np.array(U)
        self.S = E.bvh_of([f"Eye_Ball.{s}", "Blockout_Head"])

    def shift(self, P):
        """inward shift (m, >= 0) of world points P"""
        u = self.sg * (P[:, 0] - self.xc)
        z = P[:, 2]
        U = np.interp(np.clip(z, self.z0, self.z1), self.zs, self.U)
        d = np.where(u <= U, (1 - K) * np.maximum(u, 0), (1 - K) * U * (1 - sm((u - U) / FADE_U)))
        dz = np.maximum(self.z0 - z, z - self.z1)
        wz = 1 - sm((dz - FADE_Z0) / (FADE_Z1 - FADE_Z0))
        return d * wz

    def move(self, P, t=1.0):
        d = self.shift(P) * t
        Q = P.copy()
        m = d > 1e-7
        if not m.any():
            return Q, m
        Q[m, 0] -= self.sg * d[m]
        y0 = ball_y(self.S, P[m])
        y1 = ball_y(self.S, Q[m])
        dy = np.where(np.isfinite(y0) & np.isfinite(y1), y1 - y0, 0.0)
        Q[m, 1] += dy - LIFT * sm(d[m] / 0.001)
        return Q, m


def add_keys(o, name, f):
    if o.data.shape_keys is None:
        o.shape_key_add(name="Basis", from_mix=False)
    mw, mi = o.matrix_world, o.matrix_world.inverted()
    basis = o.data.shape_keys.key_blocks[0]
    P = np.array([tuple(mw @ d.co) for d in basis.data])
    prev, moved, mx = P, np.zeros(len(P), bool), 0.0
    for i in range(1, N + 1):
        Q, m = f.move(P, i / N)
        kb = o.shape_key_add(name=f"{name}_{i}", from_mix=False)
        D = Q - prev
        for j in np.nonzero(np.abs(D).max(1) > 1e-9)[0]:
            kb.data[j].co = mi @ Vector(tuple(P[j] + D[j]))
        prev, moved = Q, moved | m
        mx = max(mx, float(np.abs(Q - P).max()))
    o.data.update()
    return int(moved.sum()), mx * 1000


for s in E.SIDES:
    f = Field(s)
    key = f"ViewFar{s}"
    st = {n: add_keys(O[n], key, f) for n in (f"Eye_Lids.{s}", f"Eye_Lash.{s}", "Blockout_Head")}
    stats[key] = dict(moved_verts_maxmm={k: [v[0], round(v[1], 2)] for k, v in st.items()},
                      corner_shift_mm=round(float((1 - K) * f.U.max()) * 1000, 2))
bpy.context.view_layer.update()


# ------------------------------------------------------------------ key blends clear of the eyeball (stage keys only)
def stage_vals(vf, w):
    return {f"{vf}_{i}": float(np.clip(N * w - (i - 1), 0, 1)) for i in range(1, N + 1)}


def lift_stages(o, BALL, vf, limit=None):
    mw, mi = o.matrix_world, o.matrix_world.inverted()
    kbs = o.data.shape_keys.key_blocks
    n = limit or len(kbs[0].data)
    base = [{}, {"Blink": 0.25}, {"Blink": 0.5}, {"Blink": 0.75}, {"Blink": 1.0}, {"EyeSmile": 0.5}, {"EyeSmile": 1.0},
            {"Smile": 1.0, "EyeSmile": 1.0}, {"Smile": 0.5, "EyeSmile": 0.5}, {"Surprise": 0.5}, {"Surprise": 1.0}, {"Smile": 1.0}]
    total = np.zeros(n)
    for _ in range(4):
        K_ = {kb.name: np.array([tuple(mw @ d.co) for d in kb.data])[:n] for kb in kbs}
        P0 = K_["Basis"]
        changed = False
        for w in np.linspace(0.1, 1.0, 10):
            sv = stage_vals(vf, w)
            last = f"{vf}_{min(N, int(np.ceil(N * w - 1e-9)))}"
            for b in base:
                mx = dict(b, **sv)
                Pm = P0 + sum((t * (K_[k] - P0) for k, t in mx.items() if k in K_), np.zeros_like(P0))
                ys = ball_y(BALL, Pm)
                need = Pm[:, 1] - (ys - 0.0001)
                need = np.where(np.isfinite(need), need, 0.0)
                need[need < 1e-6] = 0.0
                if not need.any():
                    continue
                # push the last active stage key forward by need / its value (later stages carry it on as a delta)
                val = sv[last]
                kb = kbs[last]
                for j in np.nonzero(need)[0]:
                    l = min(need[j] / max(val, 0.1), 0.002)
                    p = mw @ kb.data[j].co
                    kb.data[j].co = mi @ Vector((p.x, p.y - l, p.z))
                    total[j] += l
                K_[last] = np.array([tuple(mw @ d.co) for d in kb.data])[:n]
                changed = True
        if not changed:
            break
    o.data.update()
    return int((total > 0).sum()), round(float(total.max()) * 1000, 2)


for s in ([] if os.environ.get("V6I_NOLIFT") == "1" else E.SIDES):      # V6I_NOLIFT=1: diagnosis only
    BALL = E.bvh_of([f"Eye_Ball.{s}"])
    vf = f"ViewFar{s}"
    lash = O[f"Eye_Lash.{s}"]
    stats[f"lift_{s}"] = dict(lids=lift_stages(O[f"Eye_Lids.{s}"], BALL, vf),
                              lash=lift_stages(lash, BALL, vf, int(lash["mmg_crease_start"])))

name = os.path.splitext(OUT)[0].replace("MG_ToonTest_01_", "")
json.dump(stats, open(os.path.join(EXP, "spec", f"eye_{name}_stats.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, OUT))
print("V6I_OK", json.dumps(stats))
