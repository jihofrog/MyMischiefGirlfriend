"""ToonTest_01 step 72 (Blender, background): v6i from v6f_A - view-angle key ViewFar<s>: the lids close over the outer
white up to the iris edge, by the Blink path.

usage: V6I_OUT=<file.blend> [V6I_M=<mm>] [V6I_R0=<iris radii>] [V6I_GO=<rad>] [V6I_GI=<rad>]
       Blender -b MG_ToonTest_01_v6f_A.blend --python t72_eye_v6i_close.py
Basis (the front) and the old keys are not changed. Per column of the lid sheets (column = x of its edge vertex):
  - the upper lid comes down to the iris top edge at that x (r30 iris ellipse, V6I_M mm over the iris), the lower lid up
    to the iris bottom edge; outside the iris (|u| >= iris half-width) both go to a meeting line that starts at the
    iris side at mid height and bends to the Blink closing line toward the corner
  - the fraction f of the Blink key that does it (0..1) is applied to every vertex of the column; the lash band, the
    lower lash and the crease take f of the nearest upper / lower column
  - only on the outer side: f * smoothstep(u / iris half-width from V6I_R0 to V6I_R0 + 0.4)
The iris edge is taken where the eyeball shows the iris for a gaze (the material turns the picture about the vertical
axis through the eyeball origin: texture x = x cos g + y sin g in object space), so there are three keys per eye:
ViewFar<s> (gaze 0), ViewFar<s>_GO (gaze V6I_GO outward), ViewFar<s>_GI (gaze V6I_GI inward); the driver
(eye_v6_common.view_key_values) blends them by the gaze.
Each key on Eye_Lids.<s> and Eye_Lash.<s> = Basis + f (Blink - Basis): per vertex a point of the Blink path,
which t51 blend_lift keeps over the eyeball. Driven from the camera angle (eye_v6_common.view_far_weights) only while
eye <s> is the far eye; with Blink / EyeSmile the driver scales it by (1 - Blink) (1 - EyeSmile). ViewSide<s> (a copy of
the Blink key of that eye) closes the far eye partly from 50 deg on. Then lid and lash
vertices of the ViewFar keys only are moved toward the viewer until every blend with Surprise, Smile, Blink 50 %,
EyeSmile 50 % (driver scaled) stays 0.1 mm over the eyeball.
Writes the .blend and spec/eye_<name>_stats.json.
"""
import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
assert os.path.basename(bpy.data.filepath) == "MG_ToonTest_01_v6f_A.blend"
MARGIN = float(os.environ.get("V6I_M", 0.6)) / 1000
R0 = float(os.environ.get("V6I_R0", 0.2))
GO = float(os.environ.get("V6I_GO", 0.25))
GI = float(os.environ.get("V6I_GI", 0.12))
OUT = os.environ["V6I_OUT"]
O = bpy.data.objects
stats = dict(margin_mm=MARGIN * 1000, outer_ramp_iris_radii=[R0, R0 + 0.4], gaze_out=GO, gaze_in=GI)


def world(o, kb):
    mw = o.matrix_world
    return np.array([tuple(mw @ d.co) for d in o.data.shape_keys.key_blocks[kb].data])


for s in E.SIDES:
    ib = E.TGT[s]["iris_bbox"]
    sg = 1 if s == "L" else -1
    xc, zc = float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2))
    ax, az = abs(float(E.X(ib[2]) - E.X(ib[0]))) / 2, abs(float(E.Z(ib[1]) - E.Z(ib[3]))) / 2
    lids, lash = O[f"Eye_Lids.{s}"], O[f"Eye_Lash.{s}"]
    nc = len(lids.data.vertices) // 14
    Pb, Pk = world(lids, "Basis"), world(lids, "Blink")

    ball = O[f"Eye_Ball.{s}"]
    BALL = E.bvh_of([f"Eye_Ball.{s}"])
    org = np.array(ball.matrix_world.translation)
    ZS = np.arange(zc - 1.3 * az, zc + 1.3 * az, 0.0002)

    def iris_span(x, g):
        """(top, bottom) z of the iris at world x for gaze g, or None"""
        inside = []
        for z in ZS:
            y, _ = E.front_hit(BALL, x, z)
            if y is None:
                continue
            xt = org[0] + (x - org[0]) * np.cos(g) + (y - org[1]) * np.sin(g)
            if ((xt - xc) / ax) ** 2 + ((z - zc) / az) ** 2 < 1:
                inside.append(z)
        return (max(inside), min(inside)) if inside else None

    def fractions(part, g):
        """per column of the upper (part 0) / lower (1) sheet: (u of the column, f) for gaze g"""
        base = part * nc * 7
        idx = base + np.arange(nc) * 7 + 1                       # edge row
        u = sg * (Pb[idx, 0] - xc) / ax
        zb, zk = Pb[idx, 2], Pk[idx, 2]
        # outer end of the iris at this gaze (in u), for the meeting line
        ue = max((sg * (x - xc) / ax for x in np.linspace(xc - 2 * ax, xc + 2 * ax, 81) if iris_span(x, g)), default=1.0)
        f = np.zeros(nc)
        for c in range(nc):
            sp = iris_span(Pb[idx[c], 0], g)
            meet = zc + (zk[c] - zc) * E.smooth((u[c] - ue) / 0.3)
            if part == 0:
                t = sp[0] - MARGIN if sp else meet
                t = max(t, zk[c])
                f[c] = (zb[c] - t) / (zb[c] - zk[c]) if zb[c] - zk[c] > 1e-6 else 1.0
            else:
                t = sp[1] + MARGIN if sp else meet
                t = min(t, zk[c])
                f[c] = (t - zb[c]) / (zk[c] - zb[c]) if zk[c] - zb[c] > 1e-6 else 1.0
            if sp is None and u[c] < ue:                         # inner side of the iris: stays open
                f[c] = 0.0
        f = np.clip(f, 0, 1) * E.smooth((u - R0) / 0.4)
        return u, f

    for suffix, g in (("", 0.0), ("_GO", sg * GO), ("_GI", -sg * GI)):
        uu, fu = fractions(0, g)
        ul, fl = fractions(1, g)
        order_u, order_l = np.argsort(uu), np.argsort(ul)
        fv = np.zeros(len(Pb))
        for part, ff in ((0, fu), (1, fl)):
            for c in range(nc):
                fv[part * nc * 7 + c * 7: part * nc * 7 + c * 7 + 7] = ff[c]
        Lb = world(lash, "Basis")
        nb, nr, cs = int(lash["mmg_band_cols"]), int(lash["mmg_band_rows"]), int(lash["mmg_crease_start"])
        ul_ = sg * (Lb[:, 0] - xc) / ax
        fl_ = np.interp(ul_, uu[order_u], fu[order_u])
        fl_[nb * nr:cs] = np.interp(ul_[nb * nr:cs], ul[order_l], fl[order_l])
        for o, f in ((lids, fv), (lash, fl_)):
            kbs = o.data.shape_keys.key_blocks
            b = np.array([tuple(d.co) for d in kbs["Basis"].data])
            k = np.array([tuple(d.co) for d in kbs["Blink"].data])
            new = b + f[:, None] * (k - b)
            kb = o.shape_key_add(name=f"ViewFar{s}{suffix}", from_mix=False)
            for d, c in zip(kb.data, new):
                d.co = tuple(c)
            o.data.update()
        stats[f"{s}{suffix}"] = dict(gaze=round(g, 3), upper_f=[[round(float(a), 2), round(float(b), 2)] for a, b in zip(uu[order_u][::3], fu[order_u][::3])],
                                     lower_f=[[round(float(a), 2), round(float(b), 2)] for a, b in zip(ul[order_l][::3], fl[order_l][::3])])


    # ViewSide<s>: the whole Blink of this eye, for 60 deg and more (driver: eye_v6_common.view_key_values)
    for o in (lids, lash):
        kbs = o.data.shape_keys.key_blocks
        kb = o.shape_key_add(name=f"ViewSide{s}", from_mix=False)
        for d, c in zip(kb.data, kbs["Blink"].data):
            d.co = c.co.copy()
        o.data.update()


# ------------------------------------------------------------------ ViewFar keys only: clear of the eyeball with the other keys
def ball_y(bvh, P):
    out = np.full(len(P), np.nan)
    for i, p in enumerate(P):
        y, _ = E.front_hit(bvh, p[0], p[2])
        if y is not None:
            out[i] = y
    return out


def lift_view(o, BALL, s, limit=None):
    from mathutils import Vector
    mw, mi = o.matrix_world, o.matrix_world.inverted()
    kbs = o.data.shape_keys.key_blocks
    n = limit or len(kbs[0].data)
    total = np.zeros(n)
    for name in (f"ViewFar{s}", f"ViewFar{s}_GO", f"ViewFar{s}_GI"):
        for _ in range(3):
            K_ = {kb.name: np.array([tuple(mw @ d.co) for d in kb.data])[:n] for kb in kbs}
            P0 = K_["Basis"]
            changed = False
            for t in (0.25, 0.5, 0.75, 1.0):
                for extra in ({}, {"Surprise": 0.5}, {"Surprise": 1.0}, {"Smile": 1.0}, {"Blink": 0.5}, {"EyeSmile": 0.5},
                              {"Smile": 1.0, "EyeSmile": 0.5}):
                    sc = (1 - extra.get("Blink", 0)) * (1 - extra.get("EyeSmile", 0))        # the driver's scaling
                    tv = t * sc
                    mx = dict(extra, **{name: tv})
                    Pm = P0 + sum((v * (K_[k] - P0) for k, v in mx.items() if k in K_), np.zeros_like(P0))
                    need = Pm[:, 1] - (ball_y(BALL, Pm) - 0.0001)
                    need = np.where(np.isfinite(need), need, 0.0)
                    idx = np.nonzero(need > 1e-6)[0]
                    if not len(idx):
                        continue
                    kb = kbs[name]
                    for j in idx:
                        l = min(need[j] / tv, 0.002)
                        p = mw @ kb.data[j].co
                        kb.data[j].co = mi @ Vector((p.x, p.y - l, p.z))
                        total[j] += l
                    K_[name] = np.array([tuple(mw @ d.co) for d in kb.data])[:n]
                    changed = True
            if not changed:
                break
    o.data.update()
    return int((total > 0).sum()), round(float(total.max()) * 1000, 2)


for s in E.SIDES:
    BALL = E.bvh_of([f"Eye_Ball.{s}"])
    lash = O[f"Eye_Lash.{s}"]
    stats[f"view_lift_{s}"] = dict(lids=lift_view(O[f"Eye_Lids.{s}"], BALL, s),
                                   lash=lift_view(lash, BALL, s, int(lash["mmg_crease_start"])))

name = os.path.splitext(OUT)[0].replace("MG_ToonTest_01_", "")
json.dump(stats, open(os.path.join(EXP, "spec", f"eye_{name}_stats.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, OUT))
print("V6I_OK", json.dumps({k: (v if not isinstance(v, dict) else v.get("gaze", v)) for k, v in stats.items()}))
