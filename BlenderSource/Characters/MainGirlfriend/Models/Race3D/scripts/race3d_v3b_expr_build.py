"""MainGirlfriend Race3D v3b expressions (Blender, background): v3 plus the fixes of the checks pass, on a copy of v1.

usage: Blender -b Models/MainGirlfriend_Race3D_v1.blend --python race3d_v3b_expr_build.py -- <out.blend> [force]
v1, v2, v3 and v6j files are read only (v3 = race3d_v3_expr_build.py, kept as the "before"). Same method as v3, plus:
  Happy C   eye key ExHappyC (Happy 0.85): A -> C keeps both lid curves, C -> B closes the slit (expr_design_v3b)
  Angry 2   candidate keys ExAngry2 (eyes, brows, brow cards, cheeks, blush) next to the kept ExAngry
  sparkle   the Surprise star / dot as a texture layer of the eyeball material (image eye_sparkle_<s>.png in the eye
            texture space, value node "Sparkle"): it follows the gaze and the iris scale like the painted highlights;
            no sparkle meshes
  stream    7.5 mm wide, 48 mm long (to the middle of the cheek), five columns across, 0.5 mm in front of the front-most
            surface of the Cry poses (cheek, lower lid, lash band, tear bead), darker blue outline
Writes Models/Race3D/spec/race3d_v3b_expr_build.json.
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
import expr_design_v3b as D  # noqa: E402

E = X.E
O = bpy.data.objects
args = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(args[0])
assert os.path.basename(bpy.data.filepath) == "MainGirlfriend_Race3D_v1.blend", bpy.data.filepath
assert not os.path.exists(OUT) or "force" in args, f"{OUT} exists"
RACE3D = os.path.dirname(HERE)
stats = dict(source=bpy.data.filepath, eyes={}, checks={})
BALL_CLEAR, LASH_CLEAR = 0.0001, 0.0003
SURPRISE_GAIN = 1.6
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
    pairs["ExHappyC"] += [(built["ExHappyA"][0], t) for t in (0.25, 0.5, 0.75)]
    pairs["ExHappyB"] += [(built["ExHappyC"][0], t) for t in (0.25, 0.5, 0.75)]
    for name, (K, LKn, cu, cl) in built.items():
        # lids: in-betweens from the Basis (and from A for B), with Blink (emotions scale by 1 - Blink), with view keys
        lift = np.zeros(L.nv)
        mixes = []
        for P0, t in pairs[name]:
            mixes.append((P0 + t * (K - P0), t))
        for b in (0.25, 0.5, 0.75):
            mixes.append((Bw + b * (Kb - Bw) + (1 - b) * (K - Bw), 1 - b))
        if name not in ("ExHappyA", "ExHappyB", "ExHappyC"):
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
    # Surprise: the v1 Surprise eye key x SURPRISE_GAIN (upper lid further open); where the lash band then lies on the
    # rim skin it is kept 0.4 mm in front of it (v2 showed the skin through the band as white stripes)
    head_bvh0 = E.bvh_of(["Blockout_Head"])
    for ob in (L.o, lash):
        B0, KS = X.key_world(ob, "Basis"), X.key_world(ob, "Surprise")
        P = B0 + SURPRISE_GAIN * (KS - B0)
        if ob is lash:
            hy = X.ball_y(head_bvh0, P)
            by = X.ball_y(BALL[s], P)
            on_skin = np.isfinite(hy) & (~np.isfinite(by) | (hy < by))
            P[:, 1] = np.where(on_skin, np.minimum(P[:, 1], hy - 0.0004), P[:, 1])
            side_stats["surprise_lash_on_skin"] = int(on_skin.sum())
        X.set_key(ob, "ExSurprise", P)
    side_stats["poses"]["ExSurprise"] = f"v1 Surprise key x {SURPRISE_GAIN}"
    stats["eyes"][s] = side_stats

# ------------------------------------------------------------------ mixed states: emotions together, with Blink, gaze, view keys
import expr_mix_v3b as MX  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

EXK = ("ExHappyA", "ExHappyC", "ExHappyB", "ExAngry", "ExAngry2", "ExSad", "ExCry", "ExSurprise")
CORR_PRESETS = [{"happy": 0.3}, {"happy": 0.6}, {"happy": 0.7}, {"happy": 0.8}, {"happy": 0.85}, {"happy": 0.9}, {"happy": 1.0},
                {"angry2": 0.5}, {"angry2": 1.0}, {"angry": 0.5}, {"angry": 1.0}, {"sad": 0.5},
                {"sad": 1.0}, {"sad": 1.0, "cry": 0.5}, {"sad": 1.0, "cry": 1.0}, {"surprise": 0.5}, {"surprise": 1.0}]
_seq = [{}, {"happy": 1.0}, {"angry": 1.0}, {"sad": 1.0, "cry": 0.6}, {"surprise": 1.0}]
_names = ["happy", "angry", "sad", "surprise"]
for i, a in enumerate(_names):                      # every pair of emotions crossfading (any transition order)
    for b in _names[i + 1:]:
        A = {"happy": 1.0} if a == "happy" else ({"sad": 1.0, "cry": 0.6} if a == "sad" else {a: 1.0})
        B = {"happy": 1.0} if b == "happy" else ({"sad": 1.0, "cry": 0.6} if b == "sad" else {b: 1.0})
        CORR_PRESETS += [MX.lerp_state(A, B, k / 8) for k in range(1, 8)]
CORR_PRESETS += [MX.lerp_state({}, p, k / 4) for p in ({"happy": 1.0}, {"angry": 1.0}, {"sad": 1.0, "cry": 0.6}, {"surprise": 1.0}) for k in (1, 2, 3)]
CORR_PRESETS += [{"happy": 0.125}, {"happy": 0.375}]
CORR_PRESETS += [{"happy": 0.5, "surprise": 0.5}, {"angry2": 1.0, "sad": 0.5}, {"angry2": 0.5, "sad": 0.5}]
CORR_PRESETS += [MX.lerp_state({"angry2": 1.0}, p, k / 4) for p in ({"happy": 1.0}, {"sad": 1.0, "cry": 0.6}, {"surprise": 1.0}) for k in (1, 2, 3)]
CORR_YAWS = (0, 35, -35, 45, -45, 60, -60)
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
                for yaw in CORR_YAWS:
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
    corr_stats[s] = dict(passes=len(hist), points_per_pass=hist, states=len(CORR_PRESETS) * 9 * len(CORR_YAWS))
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
        "ExAngry": (0.0028 * t_in, -0.0072 * t_in ** 1.1 + 0.0024 * (1 - t_in) ** 1.5, 1.0 + 1.0 * t_in),
        "ExAngry2": (0.0036 * t_in, -0.0090 * t_in ** 1.1 + 0.0032 * (1 - t_in) ** 1.5, 1.0 + 1.3 * t_in),
        "ExSad": (0.0010 * t_in, 0.0062 * t_in ** 1.2 - 0.0018 * (1 - t_in), 1.2 + 0.0 * t_in),
        "ExCry": (0.0 * t_in, 0.0012 * t_in, 1.1 + 0.0 * t_in),
        "ExSurprise": (0.0 * t_in, 0.0055 + 0.0015 * arch + 0.0006 * t_in, 1.1 + 0.0 * t_in),
    }
    for name, (dx, dz, k) in moves.items():
        co = B0.copy()
        co[:, 2] = zc + (B0[:, 2] - zc) * k
        co[:, 0] += to_c * dx
        co[:, 2] += dz
        co[:, 1] = np.array([E.front_hit(HEAD_BVH, p[0], p[2])[0] for p in co]) - off
        X.set_key(o, name, co)

# brow cards: copies of the brows (same keys) drawn over the bangs only while an emotion shows them (Unity: a card
# mesh with a stencil "over hair" shader and a reveal alpha from the controller)
card_mat = bpy.data.materials.get("M_BrowCard") or bpy.data.materials.new("M_BrowCard")
card_mat.use_nodes = True
_nt = card_mat.node_tree
_nt.nodes.clear()
_em = _nt.nodes.new("ShaderNodeEmission")
_em.inputs["Color"].default_value = (*E.srgb((78, 38, 34))[:3], 1)
_nt.links.new(_em.outputs[0], _nt.nodes.new("ShaderNodeOutputMaterial").inputs[0])
for s in E.SIDES:
    src = O[f"Face_Brow.{s}"]
    card = src.copy()
    card.data = src.data.copy()
    card.name = card.data.name = f"Face_BrowCard.{s}"
    src.users_collection[0].objects.link(card)
    card.data.materials.clear()
    card.data.materials.append(card_mat)
    card.hide_render = True

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
    co[:, 2] += 0.0010 * f
    co[:, 1] -= 0.0002 * f
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
head_keys["ExAngry2"] = H0 + 1.25 * (co - H0)
for name, co in head_keys.items():
    X.set_key(HEAD, name, co)
head_bvh = {name: bvh_points(HEAD, co) for name, co in head_keys.items()}
for s in E.SIDES:
    o = O[f"Face_Blush.{s}"]
    B0 = X.world(o)
    off = np.array([(E.front_hit(HEAD_BVH, p[0], p[2])[0] or p[1]) - p[1] for p in B0])
    cxz = B0[:, [0, 2]].mean(0)
    for name, (scale, up, bvh) in {"ExHappy": (1.10, 0.0010, head_bvh["ExHappy"]), "ExAngry": (1.40, 0.0004, head_bvh["ExAngry"]),
                                   "ExAngry2": (1.45, 0.0004, head_bvh["ExAngry2"]),
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
    "ExAngry": mouth_shape(hw_px0 * 0.66, lambda t: 3.0 * (1 - t * t) ** 1.3 - 1.4, 1.35),
    "ExSad": mouth_shape(hw_px0 * 0.62, lambda t: 3.4 * (1 - t * t) - 1.5 + 0.45 * np.sin(3 * np.pi * t), 1.2),
    "ExCry": mouth_shape(hw_px0 * 0.78, lambda t: 2.1 * (1 - t * t) - 1.2 + 1.0 * np.sin(3 * np.pi * t), 1.25),
    "ExSurprise": mouth_shape(hw_px0 * 0.12, lambda t: -2.0, 0.6),
}
for name, co in mouth.items():
    X.set_key(ml, name, co)
stats["mouth"] = dict(half_width_px=round(float(hw_px0), 2), columns=int(len(pairs_)))

# ------------------------------------------------------------------ open "o" mouth
coll = ml.users_collection[0]


def facing_front(faces, P):
    """faces wound toward the camera side (-y) at the points P of the pose that shows them (Unity culls back faces)"""
    out = []
    for f in faces:
        a, b, c = (np.asarray(P[i], float) for i in f[:3])
        out.append(tuple(reversed(f)) if np.cross(b - a, c - a)[1] > 0 else tuple(f))
    return out


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
faces = facing_front(faces, smile_mouth(16.0, 19.0, 4.5, -0.5))
sm = E.mesh_object("Face_Mouth_ExSmile", smile_mouth(3.0, 0.4, 0.5, 0.0), faces, coll)
for m in (bpy.data.materials["M_Ex_MouthInside"], bpy.data.materials["M_Ex_Tongue"], emission_mat("M_Ex_Teeth", (250, 248, 248)),
          bpy.data.materials["M_Ex_MouthRim"]):
    sm.data.materials.append(m)
for p, mi in zip(sm.data.polygons, mats):
    p.material_index = mi
X.set_key(sm, "ExHappy", smile_mouth(16.0, 19.0, 4.5, -0.5))
sm.hide_render = True

# ------------------------------------------------------------------ tears: bead on the lower lid + cheek stream with a flow mask
tear_mat, hl_mat = emission_mat("M_Tear", (190, 224, 255), 0.6), emission_mat("M_TearHighlight", (255, 255, 255), 0.9)


def stream_material():
    """light blue tear with a white line along it; alpha = (v < Flow, soft end) x (soft edges across u).
    The value node "Flow" (0..1) is the animation parameter; UV u runs across the stream, v from the eye down."""
    m = bpy.data.materials.get("M_TearStream") or bpy.data.materials.new("M_TearStream")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, Lk = nt.nodes.new, nt.links.new
    out = N("ShaderNodeOutputMaterial")
    uv = N("ShaderNodeUVMap")
    sep = N("ShaderNodeSeparateXYZ")
    Lk(uv.outputs[0], sep.inputs[0])
    flow = N("ShaderNodeValue")
    flow.name = flow.label = "Flow"
    flow.outputs[0].default_value = 1.0
    lo = N("ShaderNodeMath"); lo.operation = "SUBTRACT"; lo.inputs[1].default_value = 0.08
    Lk(flow.outputs[0], lo.inputs[0])
    mr = N("ShaderNodeMapRange"); mr.clamp = True
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0, 0.0
    Lk(sep.outputs[1], mr.inputs["Value"]); Lk(lo.outputs[0], mr.inputs["From Min"]); Lk(flow.outputs[0], mr.inputs["From Max"])
    c2 = N("ShaderNodeMath"); c2.operation = "MULTIPLY_ADD"; c2.inputs[1].default_value = 2.0; c2.inputs[2].default_value = -1.0
    Lk(sep.outputs[0], c2.inputs[0])
    ab = N("ShaderNodeMath"); ab.operation = "ABSOLUTE"; Lk(c2.outputs[0], ab.inputs[0])
    pw = N("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 6.0; Lk(ab.outputs[0], pw.inputs[0])
    edge = N("ShaderNodeMath"); edge.operation = "SUBTRACT"; edge.inputs[0].default_value = 1.0; Lk(pw.outputs[0], edge.inputs[1])
    a1 = N("ShaderNodeMath"); a1.operation = "MULTIPLY"; Lk(mr.outputs[0], a1.inputs[0]); Lk(edge.outputs[0], a1.inputs[1])
    a2 = N("ShaderNodeMath"); a2.operation = "MULTIPLY"; a2.inputs[1].default_value = 0.85; Lk(a1.outputs[0], a2.inputs[0])
    # white line along the stream (u around 0.38)
    d = N("ShaderNodeMath"); d.operation = "SUBTRACT"; d.inputs[1].default_value = 0.38; Lk(sep.outputs[0], d.inputs[0])
    da = N("ShaderNodeMath"); da.operation = "ABSOLUTE"; Lk(d.outputs[0], da.inputs[0])
    hl = N("ShaderNodeMapRange"); hl.clamp = True
    hl.inputs["From Min"].default_value, hl.inputs["From Max"].default_value = 0.04, 0.14
    hl.inputs["To Min"].default_value, hl.inputs["To Max"].default_value = 1.0, 0.0
    Lk(da.outputs[0], hl.inputs["Value"])
    # body: light blue in the middle, a darker blue outline at the edges (readable on the light skin), white line
    ol = N("ShaderNodeMapRange"); ol.clamp = True
    ol.inputs["From Min"].default_value, ol.inputs["From Max"].default_value = 0.55, 0.85
    Lk(ab.outputs[0], ol.inputs["Value"])
    body = N("ShaderNodeMix"); body.data_type = "RGBA"
    body.inputs[6].default_value = (*E.srgb((176, 214, 250))[:3], 1)
    body.inputs[7].default_value = (*E.srgb((96, 150, 222))[:3], 1)
    Lk(ol.outputs[0], body.inputs[0])
    mix = N("ShaderNodeMix"); mix.data_type = "RGBA"
    Lk(body.outputs[2], mix.inputs[6])
    mix.inputs[7].default_value = (1, 1, 1, 1)
    Lk(hl.outputs[0], mix.inputs[0])
    em = N("ShaderNodeEmission"); Lk(mix.outputs[2], em.inputs["Color"])
    tr = N("ShaderNodeBsdfTransparent")
    ms = N("ShaderNodeMixShader"); Lk(a2.outputs[0], ms.inputs[0]); Lk(tr.outputs[0], ms.inputs[1]); Lk(em.outputs[0], ms.inputs[2])
    Lk(ms.outputs[0], out.inputs[0])
    for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
        try:
            setattr(m, attr, val)
        except (AttributeError, TypeError):
            pass
    return m


smat = stream_material()
STREAM_LIFT = 0.0005
for s in E.SIDES:
    sph, _ = X.fit_ball(s)
    L = X.Lids(s, sph)
    u = D.eye_u(s, L.x_px(), E.TGT[s]["opening"])
    cols = np.nonzero((u >= 0.12) & (u <= 0.92))[0]
    cols = cols[np.argsort(u[cols])]
    ut = (u[cols] - 0.12) / 0.80
    thick = 0.0060 * np.sin(np.pi * ut) ** 0.6           # the eye is about 60 mm tall
    thick = np.maximum(thick, 0.0018 * (ut > 0.70) * (ut < 0.95))   # the bead stays full where the stream starts
    edge_rows = L.idx_lo[cols, 1]

    def bead(Kl, amount):
        qE, _ = X.foot(sph, Kl[edge_rows])
        rows = []
        for f, gextra in ((-0.18, 0.00020), (0.0, 0.00035), (0.5, 0.00045), (1.0, 0.00030)):
            rows.append(X.surf(sph, qE[:, 0], qE[:, 1] + thick * f * amount, qE[:, 2] + gextra))
        hl = []
        for f in (0.62, 0.78):
            hl.append(X.surf(sph, qE[:, 0], qE[:, 1] + thick * f * amount, qE[:, 2] + 0.00052))
        return np.concatenate([np.stack(rows, 1).reshape(-1, 3), np.stack(hl, 1).reshape(-1, 3)])

    nc_ = len(cols)
    f_body = E.grid_faces(nc_, 4)
    f_hl = [tuple(i + nc_ * 4 for i in q) for q in E.grid_faces(nc_, 2)]
    B_lid = X.key_world(L.o, "Basis")
    to = E.mesh_object(f"Face_Tear.{s}", bead(B_lid, 0.0), facing_front(f_body + f_hl, bead(LIDKEY[(s, "ExCry")], 1.0)), coll)
    to.data.materials.append(tear_mat)
    to.data.materials.append(hl_mat)
    hl_lo, hl_hi = np.searchsorted(ut, 0.28), np.searchsorted(ut, 0.72)
    for k, p in enumerate(to.data.polygons):
        if k >= len(f_body):
            col = (k - len(f_body))
            p.material_index = 1 if hl_lo <= col < hl_hi else 0
    X.set_key(to, "ExSad", bead(LIDKEY[(s, "ExSad")], 0.30))        # Sad: a thin wet line (welling up)
    X.set_key(to, "ExCry", bead(LIDKEY[(s, "ExCry")], 1.0))
    to.hide_render = True
    # stream: starts on the bead near the outer part of the lower lid (Cry pose) and runs down the cheek
    c0 = cols[np.argmin(np.abs(ut - 0.80))]
    start = X.key_world(L.o, "ExCry")[L.idx_lo[c0, 1]]
    n_seg, length, n_col = 60, 0.048, 5                         # down to the middle of the cheek
    out_sign = 1.0 if s == "L" else -1.0
    # front-most surface in the Cry poses (Cry alone and Sad + Cry, after the mixed-state correction): cheek skin, the
    # lower lid sheet, the lash band and the tear bead - the stream runs over all of them, never under
    lash = O[f"Eye_Lash.{s}"]
    occluders = [HEAD_BVH]
    for o, keysets in ((L.o, (("ExCry",), ("ExSad", "ExCry"))), (lash, (("ExCry",), ("ExSad", "ExCry"))), (to, (("ExCry",),))):
        B0 = X.key_world(o, "Basis")
        for ks in keysets:
            occluders.append(bvh_points(o, B0 + sum(X.key_world(o, k) - B0 for k in ks)))

    def front_y(x, z):
        ys = [y for y, _ in (E.front_hit(b, x, z) for b in occluders) if y is not None]
        return min(ys) if ys else start[1]

    grid_x, grid_z = np.zeros((n_seg + 1, n_col)), np.zeros(n_seg + 1)
    grid_y = np.zeros((n_seg + 1, n_col))
    for i in range(n_seg + 1):
        t = i / n_seg
        xc = start[0] + out_sign * 0.0045 * t ** 1.4             # drifts a little outward over the cheek
        zc = start[2] + 0.0014 - length * t                       # starts on the bead
        w = 0.0075 * (1 - 0.35 * t) + 0.0020 * np.exp(-(t / 0.08) ** 2)   # drop at the start, then narrower
        grid_z[i] = zc
        for j in range(n_col):
            grid_x[i, j] = xc + (j / (n_col - 1) - 0.5) * w
            grid_y[i, j] = front_y(grid_x[i, j], zc)
    # in front of the surface inside the quads too: sample every quad and move its corners forward only where needed
    yy = grid_y - STREAM_LIFT
    ab = np.linspace(0.0, 1.0, 5)
    for _ in range(4):
        need = np.zeros_like(yy)
        for i in range(n_seg):
            for j in range(n_col - 1):
                for a in ab:
                    for b in ab:
                        x = (grid_x[i, j] * (1 - a) + grid_x[i, j + 1] * a) * (1 - b) + (grid_x[i + 1, j] * (1 - a) + grid_x[i + 1, j + 1] * a) * b
                        z = grid_z[i] * (1 - b) + grid_z[i + 1] * b
                        y = (yy[i, j] * (1 - a) + yy[i, j + 1] * a) * (1 - b) + (yy[i + 1, j] * (1 - a) + yy[i + 1, j + 1] * a) * b
                        d = y - (front_y(x, z) - 0.0003)
                        if d > 0:
                            for ii, jj in ((i, j), (i, j + 1), (i + 1, j), (i + 1, j + 1)):
                                need[ii, jj] = max(need[ii, jj], d)
        if not need.any():
            break
        yy -= need
    pts, uvs = [], []
    for i in range(n_seg + 1):
        for j in range(n_col):
            pts.append((grid_x[i, j], yy[i, j], grid_z[i]))
            uvs.append((j / (n_col - 1), i / n_seg))
    sfaces = [(n_col * i + j, n_col * i + j + 1, n_col * (i + 1) + j + 1, n_col * (i + 1) + j) for i in range(n_seg) for j in range(n_col - 1)]
    so = E.mesh_object(f"Face_TearStream.{s}", np.array(pts), facing_front(sfaces, pts), coll, uvs=uvs)
    so.data.materials.append(smat)
    so.hide_render = True

# ------------------------------------------------------------------ eye sparkle (Surprise): a texture layer of the eyeball
# A star and a dot painted into an image in the eye texture space (same projection as the painted eye), mixed to white by
# the value node "Sparkle". It turns with the gaze and scales with the iris like the painted highlights (Unity: a second
# texture in the eyeball shader sampled with the same projected uv).
TEXD = os.path.join(RACE3D, "experiments", "textures")
os.makedirs(TEXD, exist_ok=True)
sparkle_stats = {}
for s in E.SIDES:
    ob = O[f"Eye_Ball.{s}"]
    m = ob.material_slots[0].material.copy()
    m.name = f"MG6d_EyeBall_{s}_sparkle"
    ob.material_slots[0].material = m
    nt = m.node_tree
    proj = {}
    for l in nt.links:
        if l.from_node.type == "SEPXYZ" and l.to_node.type == "MATH" and l.to_node.operation == "MULTIPLY_ADD":
            proj[l.from_socket.name] = l.to_node
    su, tu = proj["X"].inputs[1].default_value, proj["X"].inputs[2].default_value
    sv, tv = proj["Z"].inputs[1].default_value, proj["Z"].inputs[2].default_value
    comb = next(n for n in nt.nodes if n.type == "COMBXYZ")
    eye_img = next(l.to_node for l in nt.links if l.from_node == comb and l.to_node.type == "TEX_IMAGE").image
    W, H = eye_img.size
    ib = E.TGT[s]["iris_bbox"]
    cx, cz = float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2))
    rx, rz = abs(float(E.X(ib[2]) - E.X(ib[0]))) / 2, abs(float(E.Z(ib[1]) - E.Z(ib[3]))) / 2
    mi = ob.matrix_world.inverted()
    img = np.zeros((H, W, 4), np.float32)
    ss = 4                                            # supersampling per pixel

    def paint(wx, wz, r, spikes):
        c = mi @ Vector((wx, 0.0, wz))
        u0, v0 = c.x * su + tu, c.z * sv + tv
        ru, rv = abs(r * su), abs(r * 1.15 * sv)
        x0, x1 = int((u0 - ru) * W) - 2, int((u0 + ru) * W) + 2
        y0, y1 = int((v0 - rv) * H) - 2, int((v0 + rv) * H) + 2
        for y in range(max(y0, 0), min(y1, H)):
            for x in range(max(x0, 0), min(x1, W)):
                cov = 0
                for a in range(ss):
                    for b in range(ss):
                        du = ((x + (a + 0.5) / ss) / W - u0) / ru
                        dv = ((y + (b + 0.5) / ss) / H - v0) / rv
                        rr = np.hypot(du, dv)
                        if spikes:
                            ang = np.arctan2(du, dv)
                            # 4-point star: radius 1 on the axes, 0.30 between them
                            lim = 0.30 + 0.70 * abs(np.cos(2 * ang)) ** 6
                            cov += rr <= lim
                        else:
                            cov += rr <= 1.0
                img[y, x, :3] = 1.0
                img[y, x, 3] = max(img[y, x, 3], cov / (ss * ss))

    paint(cx - 0.40 * rx, cz + 0.30 * rz, 0.26 * rx, True)
    paint(cx + 0.42 * rx, cz - 0.40 * rz, 0.09 * rx, False)
    sp = bpy.data.images.new(f"eye_sparkle_{s}.png", W, H, alpha=True)
    sp.pixels[:] = img.ravel()
    path = os.path.join(TEXD, f"eye_sparkle_{s}.png")
    sp.filepath_raw = path
    sp.file_format = "PNG"
    sp.save()
    sp.filepath = path
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = sp
    tex.extension = "CLIP"
    nt.links.new(comb.outputs[0], tex.inputs[0])
    val = nt.nodes.new("ShaderNodeValue")
    val.name = val.label = "Sparkle"
    val.outputs[0].default_value = 0.0
    fac = nt.nodes.new("ShaderNodeMath")
    fac.operation = "MULTIPLY"
    nt.links.new(tex.outputs["Alpha"], fac.inputs[0])
    nt.links.new(val.outputs[0], fac.inputs[1])
    mixn = nt.nodes.new("ShaderNodeMix")
    mixn.data_type = "RGBA"
    mixn.inputs[7].default_value = (1, 1, 1, 1)
    nt.links.new(fac.outputs[0], mixn.inputs[0])
    # between the painted-eye colour mix and the shading scale
    src = next(l for l in nt.links if l.from_node.type == "MIX" and l.from_node != mixn and l.to_node.type == "VECT_MATH")
    to_sock, from_sock = src.to_socket, src.from_socket
    nt.links.remove(src)
    nt.links.new(from_sock, mixn.inputs[6])
    nt.links.new(mixn.outputs[2], to_sock)
    sparkle_stats[s] = dict(image=os.path.relpath(path, RACE3D), size=[W, H], uv_scale=[su, sv])
stats["sparkle"] = sparkle_stats

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
sc["mmg_baseline"] = "MainGirlfriend_Race3D_v3b_Expressions (experiment, v3 + checks pass, from Race3D_v1)"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True)
if os.path.exists(OUT + "1"):
    os.remove(OUT + "1")
json.dump(stats, open(os.path.join(RACE3D, "spec", "race3d_v3b_expr_build.json"), "w"), indent=1)
print("V3B_BUILD_DONE", OUT)
