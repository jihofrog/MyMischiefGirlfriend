"""MainGirlfriend Race3D v2 expressions (Blender, background): prototype emotion keys on a copy of Race3D v1.

usage: Blender -b Models/MainGirlfriend_Race3D_v1.blend --python race3d_v2_expr_build.py -- <out.blend> [force]
Race3D v1 is read only. Only new shape keys (prefix Ex) and new objects are added; every existing key, the v6j eye
structure, the 47 blend shapes and the view-angle keys stay as they are (checked by hash at the end).
  eyes    Eye_Lids / Eye_Lash: ExHappyA (crescent), ExHappyB (closed smile arch), ExAngry, ExSad, ExCry; ExSurprise is
          a copy of the v1 Surprise eye key (opening further pushes the lash band into the rim skin).
          A pose is the Blink motion by a different amount in every column (expr_design.py): lids blended in eyeball
          footpoint space (they stay on the eyeball + their gap), lashes per column like Blink at that amount. Linear
          in-betweens (Unity), Blink combinations and view-key combinations are checked against the eyeball (0.1 mm)
          and the lash against the lids (0.3 mm); only the new key is moved forward where needed. Then every mixed
          state (emotion pairs crossfading, with Blink 0 / 0.5 / 1, gaze 0 / +-0.25, camera 0 / +-35 / +-45) is
          corrected the same way where it is worse than the state without the emotion, over up to 5 passes.
  brows   Face_Brow: ExHappy, ExAngry (inner end down and in, thicker), ExSad (inner end up), ExCry, ExSurprise (up)
  cheeks  Blockout_Head: ExHappy (cheek up under the eye), ExAngry (puffed cheeks); Face_Blush: same keys (larger,
          following the cheek)
  mouth   TT_Mouth_Closed: ExHappy, ExAngry, ExSad, ExCry, ExSurprise (line shapes); new Face_Mouth_ExO (open "o",
          key ExSurprise) and Face_Mouth_ExSmile (open smile, key ExHappy); both grow from a dot on the line, so every
          in-between is a smaller mouth of the same shape (the v1 open mouth MouthOpen breaks up in between)
  tears   new Face_Tear.<s> (bead on the lower lid, keys ExSad = follow, ExCry = bead) and Face_TearStream.<s> (cheek
          stream, key ExTearFlow; structure only), material M_Tear / M_TearHighlight
Writes Models/Race3D/spec/race3d_v2_expr_build.json.
"""
import hashlib
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import expr_common as X  # noqa: E402
import expr_design as D  # noqa: E402

E = X.E
O = bpy.data.objects
args = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(args[0])
assert os.path.basename(bpy.data.filepath) == "MainGirlfriend_Race3D_v1.blend", bpy.data.filepath
assert not os.path.exists(OUT) or "force" in args, f"{OUT} exists"
RACE3D = os.path.dirname(HERE)
stats = dict(source=bpy.data.filepath, eyes={}, checks={})
BALL_CLEAR, LASH_CLEAR = 0.0001, 0.0003
EMOTIONS = ("ExHappy", "ExAngry", "ExSad", "ExCry", "ExSurprise")


def key_hashes():
    h = {}
    for o in O:
        if o.type == "MESH" and o.data.shape_keys:
            for kb in o.data.shape_keys.key_blocks:
                h[f"{o.name}/{kb.name}"] = hashlib.md5(np.array([tuple(d.co) for d in kb.data], np.float32).tobytes()).hexdigest()
    return h


BEFORE = key_hashes()


def bvh_points(o, P):
    """BVH of mesh o with its vertices at world points P"""
    from mathutils.bvhtree import BVHTree
    faces = [tuple(p.vertices) for p in o.data.polygons]
    return BVHTree.FromPolygons([Vector(tuple(map(float, p))) for p in P], faces)


def front_y_bvh(bvh, P):
    return X.ball_y(bvh, P)


# ------------------------------------------------------------------ eyes
BALL = {}
LIDKEY = {}            # (side, name) -> world points of the new lid key (for tears)
for s in E.SIDES:
    sph, fit_res = X.fit_ball(s)
    L = X.Lids(s, sph)
    BALL[s] = E.bvh_of([f"Eye_Ball.{s}"])
    Bw = X.key_world(L.o, "Basis")
    Kb = X.key_world(L.o, "Blink")
    qK, _ = X.foot(sph, Kb)
    E0u, E0l = L.edges("Basis")
    Ebu, Ebl = L.edges("Blink")
    d = dict(x=L.x_px().tolist(), E0u=E0u, E0l=E0l, Ebu=Ebu, Ebl=Ebl, opening=E.TGT[s]["opening"])
    lash = O[f"Eye_Lash.{s}"]
    nb, nr, cs = int(lash["mmg_band_cols"]), int(lash["mmg_band_rows"]), int(lash["mmg_crease_start"])
    LB = X.key_world(lash, "Basis")
    LK = X.key_world(lash, "Blink")
    lid_x = L.x_px()
    band_col = np.array([np.argmin(np.abs(lid_x - E.PX(LB[c * nr + 1, 0]))) for c in range(nb)])
    low_col = np.array([np.argmin(np.abs(lid_x - E.PX(p[0]))) for p in LB[nb * nr:cs]])
    u = D.eye_u(s, lid_x, E.TGT[s]["opening"])
    inside = (u >= 0) & (u <= 1)
    view_keys = {k: X.key_world(L.o, k) for k in (f"ViewFar{s}", f"ViewSide{s}")}
    poses = D.poses(s, d)
    side_stats = dict(sphere=sph.as_dict(), sphere_fit_res_mm=round(fit_res * 1000, 3), poses={})
    built = {}
    for name, (Eu, El) in poses.items():
        cu, cl = D.fractions(Eu, El, d)
        c = np.zeros(L.nv)
        c[L.idx_up.ravel()] = np.repeat(cu, X.ROWS)
        c[L.idx_lo.ravel()] = np.repeat(cl, X.ROWS)
        q = L.q + c[:, None] * (qK - L.q)
        K = X.surf(sph, q[:, 0], q[:, 1], q[:, 2])
        # lash: like Blink by the amount of the nearest lid column (band), lower lid amount (lower lash), mean (crease)
        cl_band = np.clip(cu[band_col], -0.5, 1.0)
        if name.startswith("ExHappy"):
            # the eye tail lifts a little: past the outer corner the band closes less than with Blink
            ub = D.eye_u(s, E.PX(LB[np.arange(nb) * nr + 1, 0]), E.TGT[s]["opening"])
            cl_band = cl_band * (1 - D.HAPPY_TAIL_KEEP * D.smooth((ub - 0.85) / 0.3))
        LKn = LB.copy()
        for k in range(nb):
            sl = slice(k * nr, k * nr + nr)
            LKn[sl] = LB[sl] + cl_band[k] * (LK[sl] - LB[sl])
        cll = np.clip(cl[low_col], -0.5, 1.3)
        LKn[nb * nr:cs] = LB[nb * nr:cs] + cll[:, None] * (LK[nb * nr:cs] - LB[nb * nr:cs])
        cm = float(np.clip(np.median(cu[inside]), -0.5, 1.0))
        LKn[cs:] = LB[cs:] + cm * (LK[cs:] - LB[cs:])
        built[name] = [K, LKn, cu, cl]
    # staged smile: A <-> B in-betweens are checked as well
    pairs = {n: [(Bw, t) for t in (0.25, 0.5, 0.75)] for n in built}
    pairs["ExHappyB"] += [(built["ExHappyA"][0], t) for t in (0.25, 0.5, 0.75)]
    for name, (K, LKn, cu, cl) in built.items():
        # lids: in-betweens from the Basis (and from A for B), with Blink (emotions scale by 1 - Blink), with view keys
        lift = np.zeros(L.nv)
        mixes = []
        for P0, t in pairs[name]:
            mixes.append((P0 + t * (K - P0), t))
        for b in (0.25, 0.5, 0.75):
            mixes.append((Bw + b * (Kb - Bw) + (1 - b) * (K - Bw), 1 - b))
        if name not in ("ExHappyA", "ExHappyB"):
            for Kv in view_keys.values():
                mixes.append((Bw + (Kv - Bw) + (K - Bw), 1.0))
        for Pm, w in mixes:
            yb = X.ball_y(BALL[s], Pm)
            need = Pm[:, 1] - (yb - BALL_CLEAR)
            lift = np.maximum(lift, np.where(np.isfinite(need), need / w, 0.0))
        lift[lift < 1e-7] = 0.0
        K[:, 1] -= lift
        # lash 0.3 mm in front of the lid sheets in the same blends
        push = np.zeros(len(LKn))
        for t in (0.25, 0.5, 0.75, 1.0):
            lid_t = Bw + t * (K - Bw)
            bvh = bvh_points(L.o, lid_t)
            la = LB + t * (LKn - LB)
            ly = front_y_bvh(bvh, la)
            need = la[:, 1] - (ly - LASH_CLEAR)
            ok = np.isfinite(need) & (need > 0)
            ok[cs:] = False                                   # crease lines lie on the skin above the lid
            push = np.maximum(push, np.where(ok, need / t, 0.0))
        LKn[:, 1] -= push
        X.set_key(L.o, name, K)
        X.set_key(lash, name, LKn)
        LIDKEY[(s, name)] = K
        side_stats["poses"][name] = dict(
            cu=[round(float(cu[inside].min()), 3), round(float(cu[inside].max()), 3)],
            cl=[round(float(cl[inside].min()), 3), round(float(cl[inside].max()), 3)],
            lid_lift_verts=int((lift > 0).sum()), lid_lift_max_mm=round(float(lift.max()) * 1000, 3),
            lash_push_verts=int((push > 0).sum()), lash_push_max_mm=round(float(push.max()) * 1000, 3))
        print("EYE", s, name, side_stats["poses"][name])
    # Surprise: the v1 Surprise eye key as it is (opening the lids further pushes the lash band into the rim skin)
    for ob in (L.o, lash):
        X.set_key(ob, "ExSurprise", X.key_world(ob, "Surprise"))
    side_stats["poses"]["ExSurprise"] = "copy of the v1 Surprise key (lids, lash)"
    stats["eyes"][s] = side_stats

# ------------------------------------------------------------------ mixed states: emotions together, with Blink, gaze, view keys
import expr_mix as MX  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

EXK = ("ExHappyA", "ExHappyB", "ExAngry", "ExSad", "ExCry", "ExSurprise")
CORR_PRESETS = [{"happy": 0.3}, {"happy": 0.6}, {"happy": 0.8}, {"happy": 1.0}, {"angry": 0.5}, {"angry": 1.0}, {"sad": 0.5},
                {"sad": 1.0}, {"sad": 1.0, "cry": 0.5}, {"sad": 1.0, "cry": 1.0}, {"surprise": 0.5}, {"surprise": 1.0}]
_seq = [{}, {"happy": 1.0}, {"angry": 1.0}, {"sad": 1.0, "cry": 0.6}, {"surprise": 1.0}]
_names = ["happy", "angry", "sad", "surprise"]
for i, a in enumerate(_names):                      # every pair of emotions crossfading (any transition order)
    for b in _names[i + 1:]:
        A = {"happy": 1.0} if a == "happy" else ({"sad": 1.0, "cry": 0.6} if a == "sad" else {a: 1.0})
        B = {"happy": 1.0} if b == "happy" else ({"sad": 1.0, "cry": 0.6} if b == "sad" else {b: 1.0})
        CORR_PRESETS += [MX.lerp_state(A, B, k / 8) for k in range(1, 8)]
CORR_PRESETS += [MX.lerp_state({}, p, k / 4) for p in ({"happy": 1.0}, {"angry": 1.0}, {"sad": 1.0, "cry": 0.6}, {"surprise": 1.0}) for k in (1, 2, 3)]
corr_stats = {}
for s in E.SIDES:
    lids, lash = O[f"Eye_Lids.{s}"], O[f"Eye_Lash.{s}"]
    nb, nr = int(lash["mmg_band_cols"]), int(lash["mmg_band_rows"])
    faces = [tuple(p.vertices) for p in lids.data.polygons]
    ball = BALL[s]
    hist = []
    for it in range(5):
        Kl = {k.name: X.key_world(lids, k.name) for k in lids.data.shape_keys.key_blocks}
        Ks = {k.name: X.key_world(lash, k.name) for k in lash.data.shape_keys.key_blocks}
        req_l = {k: np.zeros(len(Kl["Basis"])) for k in EXK}
        req_s = {k: np.zeros(len(Ks["Basis"])) for k in EXK}
        nbad = 0

        def mix(v):
            Pl = Kl["Basis"] + sum(v.get(k, 0.0) * (Kl[k] - Kl["Basis"]) for k in Kl if k != "Basis")
            Ps = Ks["Basis"] + sum(v.get(k, 0.0) * (Ks[k] - Ks["Basis"]) for k in Ks if k != "Basis")
            gap = X.ball_y(ball, Pl) - Pl[:, 1]
            bvh = BVHTree.FromPolygons([Vector(tuple(map(float, p))) for p in Pl], faces)
            band = Ps[:nb * nr]
            ly, yb2 = X.ball_y(bvh, band), X.ball_y(ball, band)
            over = np.isfinite(ly) & np.isfinite(yb2) & (ly < yb2)
            sep = np.full(len(Ps), np.inf)
            sep[:nb * nr] = np.where(over, ly - band[:, 1], np.inf)
            return np.where(np.isfinite(gap), gap, np.inf), sep

        for b in (0.0, 0.5, 1.0):
            for gz in (0.0, 0.25, -0.25):
                for yaw in (0, 35, -35, 45, -45):
                    g0, s0 = mix(MX.compose({"blink": b, "gaze": gz}, E.view_key_values, yaw)["eye"])
                    for st0 in CORR_PRESETS:
                        v = MX.compose(dict(st0, blink=b, gaze=gz), E.view_key_values, yaw)["eye"]
                        W = sum(v.get(k, 0.0) for k in EXK)
                        if W < 1e-6:
                            continue
                        g, sp = mix(v)
                        bad = (g < BALL_CLEAR) & (g < g0 - 2e-5)
                        badl = (sp < LASH_CLEAR) & (sp < s0 - 2e-5)
                        nbad += int(bad.sum() + badl.sum())
                        need_l = np.where(bad, (BALL_CLEAR + 2e-5 - g) / W, 0.0)
                        need_s = np.where(badl, (LASH_CLEAR + 2e-5 - sp) / W, 0.0)
                        for k in EXK:
                            if v.get(k, 0.0) > 1e-6:
                                req_l[k] = np.maximum(req_l[k], need_l)
                                req_s[k] = np.maximum(req_s[k], need_s)
        hist.append(nbad)
        print("CORRECT", s, "pass", it, "points under the limits", nbad)
        if nbad == 0:
            break
        for k in EXK:
            if req_l[k].any():
                P = Kl[k].copy()
                P[:, 1] -= req_l[k]
                X.set_key(lids, k, P)
            if req_s[k].any():
                P = Ks[k].copy()
                P[:, 1] -= req_s[k]
                X.set_key(lash, k, P)
    corr_stats[s] = dict(passes=len(hist), points_per_pass=hist, states=len(CORR_PRESETS) * 45)
stats["mixed_state_correction"] = corr_stats

# ------------------------------------------------------------------ brows
HEAD = O["Blockout_Head"]
HEAD_BVH = E.bvh_of(["Blockout_Head"])
for s in E.SIDES:
    o = O[f"Face_Brow.{s}"]
    B0 = X.world(o)
    off = np.array([E.front_hit(HEAD_BVH, p[0], p[2])[0] - p[1] for p in B0])
    xin = B0[:, 0].min() if s == "L" else B0[:, 0].max()
    t_in = 1 - np.abs(B0[:, 0] - xin) / np.ptp(B0[:, 0])          # 1 at the inner end
    arch = 4 * t_in * (1 - t_in)
    to_c = -1.0 if s == "L" else 1.0                             # toward the face centre
    # centre line of the brow ribbon (per x bin): the thickness scales about it
    bins = np.clip(((B0[:, 0] - B0[:, 0].min()) / np.ptp(B0[:, 0]) * 24).astype(int), 0, 23)
    zc = np.array([(B0[bins == b, 2].min() + B0[bins == b, 2].max()) / 2 if (bins == b).any() else np.nan for b in range(24)])
    ok = np.isfinite(zc)
    zc = np.interp(np.arange(24), np.nonzero(ok)[0], zc[ok])[bins]
    moves = {   # (dx toward the centre, dz, thickness factor)
        "ExHappy": (0.0 * t_in, 0.0012 + 0.0006 * arch, 1.0 + 0.0 * t_in),
        "ExAngry": (0.0015 * t_in, -0.0055 * t_in ** 1.2 + 0.0012 * (1 - t_in), 1.0 + 0.8 * t_in),
        "ExSad": (0.0006 * t_in, 0.0050 * t_in ** 1.3 - 0.0015 * (1 - t_in), 1.25 + 0.0 * t_in),
        "ExCry": (0.0 * t_in, 0.0012 * t_in, 1.1 + 0.0 * t_in),
        "ExSurprise": (0.0 * t_in, 0.0042 + 0.0012 * arch + 0.0008 * t_in, 1.15 + 0.0 * t_in),
    }
    for name, (dx, dz, k) in moves.items():
        co = B0.copy()
        co[:, 2] = zc + (B0[:, 2] - zc) * k
        co[:, 0] += to_c * dx
        co[:, 2] += dz
        co[:, 1] = np.array([E.front_hit(HEAD_BVH, p[0], p[2])[0] for p in co]) - off
        X.set_key(o, name, co)

# ------------------------------------------------------------------ cheeks (head) and blush
H0 = X.world(HEAD)
hn = np.array([tuple((HEAD.matrix_world.to_3x3() @ v.normal).normalized()) for v in HEAD.data.vertices])
front = (H0[:, 1] < -0.06) & (hn[:, 1] < -0.2)
head_keys = {}
co = H0.copy()
for s in E.SIDES:
    poly = E.opening_poly(s)
    zc = poly[:, 1].mean()
    sd = E.signed_dist(H0[:, [0, 2]], poly)
    f = E.smooth(sd / 0.002) * (1 - E.smooth((sd - 0.002) / 0.016)) * E.smooth((zc - H0[:, 2]) / 0.012 + 0.2) * front
    co[:, 2] += 0.0013 * f
    co[:, 1] -= 0.0006 * f
head_keys["ExHappy"] = co
co = H0.copy()
for s in E.SIDES:
    bl = X.world(O[f"Face_Blush.{s}"])
    cxz = bl[:, [0, 2]].mean(0)
    r = np.linalg.norm(H0[:, [0, 2]] - cxz, axis=1)
    f = E.smooth(1 - r / 0.026) * front
    co += hn * (0.0018 * f)[:, None]
    co[:, 2] += 0.0004 * f
head_keys["ExAngry"] = co
for name, co in head_keys.items():
    X.set_key(HEAD, name, co)
head_bvh = {name: bvh_points(HEAD, co) for name, co in head_keys.items()}
for s in E.SIDES:
    o = O[f"Face_Blush.{s}"]
    B0 = X.world(o)
    off = np.array([(E.front_hit(HEAD_BVH, p[0], p[2])[0] or p[1]) - p[1] for p in B0])
    cxz = B0[:, [0, 2]].mean(0)
    for name, (scale, up, bvh) in {"ExHappy": (1.10, 0.0010, head_bvh["ExHappy"]), "ExAngry": (1.40, 0.0004, head_bvh["ExAngry"]),
                                   "ExSad": (1.15, 0.0004, HEAD_BVH), "ExCry": (1.25, 0.0008, HEAD_BVH),
                                   "ExSurprise": (0.92, 0.0, HEAD_BVH)}.items():
        co = B0.copy()
        co[:, [0, 2]] = cxz + (B0[:, [0, 2]] - cxz) * scale
        co[:, 2] += up
        ys = []
        for p, of in zip(co, off):
            y, _ = E.front_hit(bvh, p[0], p[2])
            ys.append((y if y is not None else p[1] + of) - of)
        co[:, 1] = ys
        X.set_key(o, name, co)

# ------------------------------------------------------------------ mouth line shapes
ml = O["TT_Mouth_Closed"]
M0 = X.world(ml)
order = np.argsort(M0[:, 0], kind="stable")
pairs_ = order.reshape(-1, 2)                                      # 13 columns of (top, bottom)
cen = np.array([M0[p].mean(0) for p in pairs_])
half = np.array([(M0[p[0]] - M0[p[1]]) / 2 for p in pairs_])       # top - centre (per column)
cx0, hw0 = cen[:, 0].mean(), (cen[:, 0].max() - cen[:, 0].min()) / 2
tcol = (cen[:, 0] - cx0) / hw0
offm = np.array([E.front_hit(HEAD_BVH, p[0], p[2])[0] - p[1] for p in M0])
PXM = 1.0 / E.PPM


def mouth_shape(hw_px, dz_fn, thick):
    co = M0.copy()
    for i, (a, b) in enumerate(pairs_):
        t = tcol[i]
        c = np.array([cx0 + t * hw_px * PXM, cen[i, 1], cen[i, 2] + (cen[i, 2] - cen[:, 2].mean()) * 0.0 + dz_fn(t) * PXM])
        co[a] = c + half[i] * thick
        co[b] = c - half[i] * thick
    co[:, 1] = np.array([E.front_hit(HEAD_BVH, p[0], p[2])[0] for p in co]) - offm
    return co


hw_px0 = hw0 * E.PPM
mouth = {
    "ExHappy": mouth_shape(hw_px0 * 1.18, lambda t: 3.2 * t * t, 1.1),
    "ExAngry": mouth_shape(hw_px0 * 0.72, lambda t: 4.6 * (1 - t * t) ** 1.3 - 2.2, 1.45),
    "ExSad": mouth_shape(hw_px0 * 0.60, lambda t: 3.2 * (1 - t * t) - 1.4, 1.2),
    "ExCry": mouth_shape(hw_px0 * 0.78, lambda t: 2.1 * (1 - t * t) - 1.2 + 1.0 * np.sin(3 * np.pi * t), 1.25),
    "ExSurprise": mouth_shape(hw_px0 * 0.12, lambda t: -2.0, 0.6),
}
for name, co in mouth.items():
    X.set_key(ml, name, co)
stats["mouth"] = dict(half_width_px=round(float(hw_px0), 2), columns=int(len(pairs_)))

# ------------------------------------------------------------------ open "o" mouth
coll = ml.users_collection[0]


def emission_mat(name, rgb, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*E.srgb(rgb)[:3], 1)
    if alpha >= 1.0:
        nt.links.new(em.outputs[0], out.inputs[0])
    else:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = alpha
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs[0])
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try:
                setattr(m, attr, val)
            except (AttributeError, TypeError):
                pass
    return m


cxm, czm = cen[:, 0].mean(), cen[:, 2].mean()


def ellipse_ring(rx, ry, cx, cz, n=28):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([cx + rx * np.cos(a), cz + ry * np.sin(a)], 1)


def o_mouth(rx_px, ry_px, dz_px):
    cz = czm - dz_px * PXM
    rx, ry = rx_px * PXM, ry_px * PXM
    rim_w = 1.5 * PXM
    pts, gaps = [], []
    # fill: centre + ring
    pts.append((cxm, cz)); gaps.append(0.00020)
    for p in ellipse_ring(rx, ry, cxm, cz):
        pts.append(tuple(p)); gaps.append(0.00020)
    # rim: inner / outer rings
    for p in ellipse_ring(rx - rim_w * 0.3, ry - rim_w * 0.3, cxm, cz):
        pts.append(tuple(p)); gaps.append(0.00035)
    for p in ellipse_ring(rx + rim_w * 0.7, ry + rim_w * 0.7, cxm, cz):
        pts.append(tuple(p)); gaps.append(0.00035)
    # tongue: lower part of the inside
    tz = cz - ry * 0.52
    pts.append((cxm, tz)); gaps.append(0.00028)
    for p in ellipse_ring(rx * 0.58, ry * 0.36, cxm, tz):
        pts.append(tuple(p)); gaps.append(0.00028)
    P = []
    for (x, z), g in zip(pts, gaps):
        y, _ = E.front_hit(HEAD_BVH, x, z)
        P.append((x, y - g, z))
    return np.array(P)


n = 28
faces, mats = [], []
for i in range(n):                                   # fill fan
    faces.append((0, 1 + i, 1 + (i + 1) % n)); mats.append(0)
ri, ro = 1 + n, 1 + 2 * n
for i in range(n):                                   # rim strip
    j = (i + 1) % n
    faces.append((ri + i, ro + i, ro + j, ri + j)); mats.append(1)
tc = 1 + 3 * n
for i in range(n):                                   # tongue fan
    faces.append((tc, tc + 1 + i, tc + 1 + (i + 1) % n)); mats.append(2)
Pb = o_mouth(0.8, 0.8, 2.0)
om = E.mesh_object("Face_Mouth_ExO", Pb, faces, coll)
for m in (emission_mat("M_Ex_MouthInside", (150, 60, 60)), emission_mat("M_Ex_MouthRim", (150, 70, 62)), emission_mat("M_Ex_Tongue", (230, 120, 120))):
    om.data.materials.append(m)
for p, mi in zip(om.data.polygons, mats):
    p.material_index = mi
X.set_key(om, "ExSurprise", o_mouth(8.0, 10.0, 6.0))
om.hide_render = True

# ------------------------------------------------------------------ open smile mouth (D shape, grows from the line)
NI, NJ = 24, 10


def smile_mouth(w_px, depth_px, corner_px, top_px):
    """grid NI x (NJ + 1) inside (teeth / inside / tongue by depth), then the lip line strip along the top edge"""
    pts, gaps = [], []
    for i in range(NI):
        t = -1 + 2 * i / (NI - 1)
        x = cxm + t * w_px * PXM
        ztop = czm - top_px * PXM + corner_px * t * t * PXM
        dep = depth_px * (1 - t * t) ** 0.8 * PXM
        for j in range(NJ + 1):
            pts.append((x, ztop - j / NJ * dep))
            gaps.append(0.00022)
    for i in range(NI):
        t = -1 + 2 * i / (NI - 1)
        x = cxm + t * (w_px + 0.6) * PXM
        ztop = czm - top_px * PXM + corner_px * t * t * PXM
        pts.append((x, ztop + 0.9 * PXM))
        gaps.append(0.00035)
        pts.append((x, ztop - 0.5 * PXM))
        gaps.append(0.00035)
    P = []
    for (x, z), g in zip(pts, gaps):
        y, _ = E.front_hit(HEAD_BVH, x, z)
        P.append((x, y - g, z))
    return np.array(P)


faces, mats = [], []
for i in range(NI - 1):
    for j in range(NJ):
        a, b = i * (NJ + 1) + j, (i + 1) * (NJ + 1) + j
        faces.append((a, b, b + 1, a + 1))
        v = (j + 0.5) / NJ
        t = -1 + 2 * (i + 0.5) / (NI - 1)
        mats.append(2 if v < 0.16 else (1 if (v > 0.62 and abs(t) < 0.8) else 0))
L0 = NI * (NJ + 1)
for i in range(NI - 1):
    a, b = L0 + 2 * i, L0 + 2 * (i + 1)
    faces.append((a, b, b + 1, a + 1))
    mats.append(3)
sm = E.mesh_object("Face_Mouth_ExSmile", smile_mouth(3.0, 0.4, 0.5, 0.0), faces, coll)
for m in (bpy.data.materials["M_Ex_MouthInside"], bpy.data.materials["M_Ex_Tongue"], emission_mat("M_Ex_Teeth", (250, 248, 248)),
          bpy.data.materials["M_Ex_MouthRim"]):
    sm.data.materials.append(m)
for p, mi in zip(sm.data.polygons, mats):
    p.material_index = mi
X.set_key(sm, "ExHappy", smile_mouth(16.0, 19.0, 4.5, -0.5))
sm.hide_render = True

# ------------------------------------------------------------------ tears (bead on the lower lid + cheek stream)
tear_mat, hl_mat = emission_mat("M_Tear", (196, 228, 255), 0.55), emission_mat("M_TearHighlight", (255, 255, 255), 0.9)
for s in E.SIDES:
    sph, _ = X.fit_ball(s)
    L = X.Lids(s, sph)
    u = D.eye_u(s, L.x_px(), E.TGT[s]["opening"])
    cols = np.nonzero((u >= 0.12) & (u <= 0.92))[0]
    cols = cols[np.argsort(u[cols])]
    ut = (u[cols] - 0.12) / 0.80
    thick = 0.0060 * np.sin(np.pi * ut) ** 0.6           # the eye is about 60 mm tall
    edge_rows = L.idx_lo[cols, 1]

    def bead(Kl, full):
        qE, _ = X.foot(sph, Kl[edge_rows])
        rows = []
        for f, gextra in ((-0.18, 0.00020), (0.0, 0.00035), (0.5, 0.00045), (1.0, 0.00030)):
            dz = (thick * f) if full else np.zeros(len(cols))
            rows.append(X.surf(sph, qE[:, 0], qE[:, 1] + dz, qE[:, 2] + gextra))
        hl = []
        for f in (0.62, 0.78):
            dz = (thick * f) if full else np.zeros(len(cols))
            hl.append(X.surf(sph, qE[:, 0], qE[:, 1] + dz, qE[:, 2] + 0.00052))
        return np.concatenate([np.stack(rows, 1).reshape(-1, 3), np.stack(hl, 1).reshape(-1, 3)])

    nc_ = len(cols)
    f_body = E.grid_faces(nc_, 4)
    f_hl = [tuple(i + nc_ * 4 for i in q) for q in E.grid_faces(nc_, 2)]
    B_lid = X.key_world(L.o, "Basis")
    to = E.mesh_object(f"Face_Tear.{s}", bead(B_lid, False), f_body + f_hl, coll)
    to.data.materials.append(tear_mat)
    to.data.materials.append(hl_mat)
    hl_lo, hl_hi = np.searchsorted(ut, 0.28), np.searchsorted(ut, 0.72)
    for k, p in enumerate(to.data.polygons):
        if k >= len(f_body):
            col = (k - len(f_body))
            p.material_index = 1
            if not (hl_lo <= col < hl_hi):
                p.material_index = 0
    X.set_key(to, "ExSad", bead(LIDKEY[(s, "ExSad")], False))
    X.set_key(to, "ExCry", bead(LIDKEY[(s, "ExCry")], True))
    to.hide_render = True
    # stream: from the lower lid at u 0.72 down the cheek (structure for a later flow animation)
    c0 = cols[np.argmin(np.abs(ut - 0.75))]
    start = LIDKEY[(s, "ExCry")][L.idx_lo[c0, 1]]
    n_seg, length, wdt = 10, 0.016, 0.0022
    out_sign = 1.0 if s == "L" else -1.0
    path = []
    for i in range(n_seg + 1):
        t = i / n_seg
        x = start[0] + out_sign * 0.002 * t
        z = start[2] - length * t
        y, _ = E.front_hit(HEAD_BVH, x, z)
        path.append((x, (y if y is not None else start[1]) - 0.0003, z))
    path = np.array(path)
    full = []
    for i, p in enumerate(path):
        w = wdt * (1 - 0.6 * i / n_seg)
        full += [p + np.array([-w / 2, 0, 0]), p + np.array([w / 2, 0, 0])]
    full = np.array(full)
    collapsed = np.repeat(full[:2], n_seg + 1, axis=0).reshape(-1, 2, 3).reshape(-1, 3)
    so = E.mesh_object(f"Face_TearStream.{s}", collapsed, [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(n_seg)], coll)
    so.data.materials.append(tear_mat)
    X.set_key(so, "ExTearFlow", full)
    so.hide_render = True

# ------------------------------------------------------------------ checks and save
AFTER = key_hashes()
changed = [k for k, v in BEFORE.items() if AFTER.get(k) != v]
added = sorted(k for k in AFTER if k not in BEFORE)
stats["checks"] = dict(existing_keys=len(BEFORE), existing_keys_changed=changed, keys_added=len(added), added=added)
print("KEYS existing", len(BEFORE), "changed", changed, "added", len(added))
for o in O:
    if o.type == "MESH" and o.data.shape_keys:
        for kb in o.data.shape_keys.key_blocks[1:]:
            kb.value = 0.0
sc = bpy.context.scene
sc["mmg_baseline"] = "MainGirlfriend_Race3D_v2_Expressions (experiment, from Race3D_v1)"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True)
if os.path.exists(OUT + "1"):
    os.remove(OUT + "1")
json.dump(stats, open(os.path.join(RACE3D, "spec", "race3d_v2_expr_build.json"), "w"), indent=1)
print("V2_BUILD_DONE", OUT)
