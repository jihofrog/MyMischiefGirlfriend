"""ToonTest_01 step 25 (Blender, background): eye method B - stylised eyeball in a shallow socket with thin 3D lids.

usage: Blender -b MG_ToonTest_01_v5g_temple.blend --python t25_eye_v6b.py
(env V6B_D = socket depth D in m, V6B_OUT = other output .blend for depth trials, V6B_CUTS)
Writes MG_ToonTest_01_v6b_eye.blend and spec/eye_v6b_stats.json (v5g stays as it is; its eye objects are kept in the
new file, excluded from the view layer, for comparison).
  head      Blockout_Head: Subdivision applied, the eye region refined (CUTS), a socket pressed in along y only (the
            front view does not move): inside the opening (+ a margin hidden under the lids) the skin goes behind the
            eyeball; around it a rim T above the eyeball blends back to the original face over F
  eyeball   Eye_Ball.<s>: front part of a spheroid with a vertical axis (horizontal radius R, vertical C; fitted so its
            surface lies D behind the original skin over the opening), turned by the empty Eye_BallPivot.<s> for the
            gaze (a turn about its own axis does not move the surface). Iris = r30 painted eye on the eyeball, front
            projected (eye_tex_ball_<s>.png)
  lids      Eye_Lids.<s> (skin material): upper and lower lid sheets on the eyeball (+ gap) with an edge fold; at rest
            they sit under the rim / lash band, the keys slide their edges over the eyeball
  lashes    Eye_Lash.<s>: r30 EyeLash_Upper band laid on the rim (alpha clip, front projected texture) with an edge
            skirt down to the eyeball (lid thickness), and the lower lash of r30
  keys      Blink, EyeSmile, Smile, Surprise on lids / lashes / brows / head (cheek); MouthOpen and Smile of the
            mouth meshes kept (Shrinkwrap baked so FBX keeps them)
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
P = dict(
    CUTS=int(os.environ.get("V6B_CUTS", 2)),   # eye region refinement of the head (edge cuts)
    D=float(os.environ.get("V6B_D", 0.004)),   # eyeball surface behind the original skin, along the skin normal
    T_UP=0.0030,        # rim above the eyeball at the upper / lower edge of the socket
    T_LO=0.0020,
    DIVE_UP=0.0030,     # the skin turns into the socket this far outside the r30 opening (upper: under the lash band)
    DIVE_LO=0.0021,     # lower: just outside the lower lid edge
    F=0.010,            # rim -> original face blend width
    DEEP=0.0025,        # skin inside the socket: behind the eyeball surface
    GAP_UP=0.0015,      # upper / lower lid sheets above the eyeball
    GAP_LO=0.0015,
    BAND_IN=0.0022,     # lash band height above the eyeball inside the opening, and above the skin outside
    BAND_OUT=0.0004,
    SKIRT=0.0011,      # lid edge fold down to this height (> the chord dip of a half key on the eyeball curve)
)
sc = bpy.context.scene
coll = bpy.data.collections.new("MainGirlfriend_Eyes_v6b")
sc.collection.children.link(coll)
lc = bpy.context.view_layer.layer_collection.children["MainGirlfriend_Eyes"]
lc.exclude = True
for n in ("Face_UpperLashes.L", "Face_UpperLashes.R", "Face_LowerLashes.L", "Face_LowerLashes.R"):
    o = bpy.data.objects[n]
    o.hide_render = True
    o.hide_viewport = True
stats = {"params": P}

# ------------------------------------------------------------------ head: apply Subdivision, refine the eye regions
head = bpy.data.objects["Blockout_Head"]
ORIG = E.bvh_of(["Blockout_Head"])
outl = head.modifiers["TT_Outline"]
outl.show_viewport = False
dg = bpy.context.evaluated_depsgraph_get()
dg.update()
me = bpy.data.meshes.new_from_object(head.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
me.name = "Blockout_Head_v6b"
head.data = me
head.modifiers.remove(head.modifiers["Subdivision"])
mw, mi = head.matrix_world.copy(), head.matrix_world.inverted()

REG = {}
for s in E.SIDES:
    oc, lcs = E.cols(s, "opening_cols"), E.cols(s, "lash_cols")
    xs = list(oc) + list(lcs)
    top = min(v[0] for v in lcs.values())
    bot = max(v[1] for v in oc.values())
    x0, x1 = sorted([float(E.X(min(xs))), float(E.X(max(xs)))])
    REG[s] = (x0 - 0.014, x1 + 0.014, float(E.Z(bot)) - 0.022, float(E.Z(top)) + 0.010)


def in_reg(p, pad=0.0):
    return any(r[0] - pad < p.x < r[1] + pad and r[2] - pad < p.z < r[3] + pad for r in REG.values()) and p.y < -0.04


bm = bmesh.new()
bm.from_mesh(me)
faces = [f for f in bm.faces if in_reg(mw @ f.calc_center_median())]
cen = np.array([tuple(mw @ f.calc_center_median()) for f in faces])
near = np.zeros(len(faces), bool)
for s in E.SIDES:                              # only the socket, rim and cheek-lift band get the finer mesh
    near |= E.signed_dist(cen[:, [0, 2]], E.opening_poly(s)) < P["DIVE_UP"] + P["F"] + 0.009
faces = [f for f, k in zip(faces, near) if k]
edges = list({e for f in faces for e in f.edges})
nv0 = len(bm.verts)
bmesh.ops.subdivide_edges(bm, edges=edges, cuts=P["CUTS"], use_grid_fill=True)
bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
for f in bm.faces:
    f.smooth = True
bm.to_mesh(me)
bm.free()
stats["head_verts"] = [nv0, len(me.vertices)]

# ------------------------------------------------------------------ eyeball fit
SPH = {}
for s in E.SIDES:
    poly = E.opening_poly(s)
    x0, x1, z0, z1 = REG[s]
    gx, gz = np.meshgrid(np.arange(x0, x1, 0.001), np.arange(z0, z1, 0.001))
    G = np.stack([gx.ravel(), gz.ravel()], 1)
    r = E.signed_dist(G, poly)
    G, r = G[r < 0.007], r[r < 0.007]
    T, W, N = [], [], []
    for (x, z), rr in zip(G, r):
        y, n = E.front_hit(ORIG, x, z)
        if y is None:
            continue
        T.append((x, y + P["D"] / max(0.5, -n.y), z))
        W.append(1.0 if rr < 0 else 0.4)
        N.append(tuple(n))
    T, W, N = np.array(T), np.array(W), np.array(N)
    ins = W == 1.0
    p0 = T[ins].mean(0)
    nb = N[ins].mean(0)
    nb /= np.linalg.norm(nb)
    dh = np.array([nb[0], nb[1]]) / np.hypot(nb[0], nb[1])
    psi = math.asin(nb[2])
    R0, C0 = 0.06, 0.08
    beta = math.atan(C0 / R0 * math.tan(psi))
    c0 = p0 - np.array([R0 * math.cos(beta) * dh[0], R0 * math.cos(beta) * dh[1], C0 * math.sin(beta)])
    sph = E.fit_spheroid(T, W, E.Spheroid(c0, R0, C0))
    yb = sph.front_y(T[:, 0], T[:, 2])
    d = (yb - T[:, 1]) * 1000
    skin_gap = (T[:, 1] - P["D"] / np.maximum(0.5, -N[:, 1]) - yb) * -1000     # + = eyeball behind the original skin
    SPH[s] = sph
    stats[f"eyeball_{s}"] = dict(sph.as_dict(), fit_mm=dict(med=round(float(np.nanmedian(d[ins])), 2),
                                 p10=round(float(np.nanpercentile(d[ins], 10)), 2), p90=round(float(np.nanpercentile(d[ins], 90)), 2)),
                                 behind_skin_mm=dict(min=round(float(np.nanmin(skin_gap[ins])), 2),
                                                     med=round(float(np.nanmedian(skin_gap[ins])), 2)))
    print("EYEBALL", s, stats[f"eyeball_{s}"])

# ------------------------------------------------------------------ socket
W_ = np.array([tuple(mw @ v.co) for v in me.vertices])
newy = W_[:, 1].copy()
zone = np.zeros(len(W_), int)               # 1 socket, 2 inner rim, 3 outer rim (outline weight, cheek key)
TRIM = 0.004                                # the eyeball mesh reaches DIVE + TRIM past the r30 opening
FRONT = {}


def dive_T(z, poly):
    up = E.smooth((z - poly[:, 1].mean()) / 0.012 + 0.5)
    return P["DIVE_LO"] + (P["DIVE_UP"] - P["DIVE_LO"]) * up, P["T_LO"] + (P["T_UP"] - P["T_LO"]) * up


for s in E.SIDES:
    sph, poly = SPH[s], E.opening_poly(s)
    x0, x1, z0, z1 = REG[s]
    cand = np.nonzero((W_[:, 0] > x0) & (W_[:, 0] < x1) & (W_[:, 2] > z0) & (W_[:, 2] < z1) & (W_[:, 1] < -0.04))[0]
    idx = np.array([i for i in cand if (lambda y: y is not None and abs(W_[i, 1] - y) < 0.003)(E.front_hit(ORIG, W_[i, 0], W_[i, 2])[0])])
    x, z = W_[idx, 0], W_[idx, 2]
    dive, T_ = dive_T(z, poly)
    sd = E.signed_dist(np.stack([x, z], 1), poly) - dive
    yb, ny = sph.front_y_clamped(x, z), sph.ny(x, z)
    a = sd < 0
    newy[idx[a]] = yb[a] + P["DEEP"] / ny[a]
    zone[idx[a]] = 1
    b = (sd >= 0) & (sd < P["F"])
    w = E.smooth(sd[b] / P["F"])
    yr = (yb[b] - T_[b] / ny[b]) * (1 - w) + W_[idx[b], 1] * w
    lim = sd[b] < TRIM + 0.0035                # where the eyeball mesh is, the skin stays in front of it
    yr = np.where(lim, np.minimum(yr, yb[b] - 0.0008 / ny[b]), yr)
    newy[idx[b]] = yr
    zone[idx[b]] = np.where(sd[b] < P["F"] * 0.5, 2, 3)
    FRONT[s] = (idx, sd)
    mv = (newy[idx] - W_[idx, 1]) * 1000
    stats[f"socket_{s}"] = dict(verts_socket=int(a.sum()), verts_rim=int(b.sum()),
                                rim_moved_back_mm_max=round(float(mv[b].max()), 2), rim_moved_forward_mm_max=round(float(-mv[b].min()), 2))
    print("SOCKET", s, stats[f"socket_{s}"])
R3, Ri3 = mw.to_3x3(), mi.to_3x3()
N0 = np.array([tuple((R3 @ v.normal).normalized()) for v in me.vertices])
for i, v in enumerate(me.vertices):
    v.co = mi @ Vector((W_[i, 0], newy[i], W_[i, 2]))
me.update()
# custom normals: socket wall and inner rim shaded like the original face (no dark ring in the toon steps), blending to
# the real normals across the rim
N1 = np.array([tuple((R3 @ v.normal).normalized()) for v in me.vertices])
SDV = np.full(len(W_), np.inf)
for s in E.SIDES:
    SDV[FRONT[s][0]] = FRONT[s][1]
a = E.smooth((np.where(np.isfinite(SDV), SDV, P["F"]) - 0.5 * P["F"]) / (0.5 * P["F"]))[:, None]
NC = np.where((zone <= 2)[:, None] & (zone >= 1)[:, None], N0, (1 - a) * N0 + a * N1)   # inner rim = the lid sheets' normals
NC /= np.linalg.norm(NC, axis=1, keepdims=True)
me.normals_split_custom_set_from_vertices([tuple((Ri3 @ Vector(tuple(n))).normalized()) for n in NC])
# outline hull off in the socket and on the inner rim (it would draw dark lines over the eyeball)
vg = head.vertex_groups.get("v6b_outline") or head.vertex_groups.new(name="v6b_outline")
for i in range(len(me.vertices)):
    vg.add([i], 0.0 if zone[i] in (1, 2) else 1.0, "REPLACE")
outl.vertex_group = "v6b_outline"
outl.thickness_vertex_group = 0.0
outl.show_viewport = True
HEAD = E.bvh_of(["Blockout_Head"])


def head_point(x, z, lift):
    """point on the (new) skin at (x, z), `lift` above it along the skin normal (approximately, along y)"""
    out = []
    for xx, zz in zip(np.atleast_1d(x), np.atleast_1d(z)):
        y, n = E.front_hit(HEAD, xx, zz)
        out.append((xx, y - lift / max(0.35, abs(n.y)), zz) if y is not None else (xx, np.nan, zz))
    return np.array(out)


# ------------------------------------------------------------------ eyeballs (picture turned by the material for the gaze)
for s in E.SIDES:
    sph, poly = SPH[s], E.opening_poly(s)
    x0, x1, z0, z1 = REG[s]
    gx, gz = np.meshgrid(np.linspace(x0, x1, 50), np.linspace(z0, z1, 50))
    pts = sph.surf(gx.ravel(), gz.ravel())
    pts = pts[~np.isnan(pts[:, 1])]
    pts = pts[E.signed_dist(pts[:, [0, 2]], poly) - dive_T(pts[:, 2], poly)[0] < TRIM + 0.004]
    az, el = sph.param(pts)
    na, ne = 34, 26
    A = np.linspace(az.min() - 0.02, az.max() + 0.02, na)
    Lv = np.linspace(max(-1.45, el.min() - 0.02), min(1.45, el.max() + 0.02), ne)
    V = np.array([sph.point(a, l) for a in A for l in Lv])
    sdv = E.signed_dist(V[:, [0, 2]], poly) - dive_T(V[:, 2], poly)[0]
    F = [f for f in E.grid_faces(na, ne) if max(sdv[list(f)]) < TRIM + 0.002]
    used = sorted({i for f in F for i in f})
    remap = {o: n for n, o in enumerate(used)}
    V = V[used]
    F = [tuple(remap[i] for i in f) for f in F]
    bx = E.TGT["tex_box"][s]
    U = np.stack([(E.PX(V[:, 0]) - bx[0]) / (bx[2] - bx[0]), 1 - (E.PY(V[:, 2]) - bx[1]) / (bx[3] - bx[1])], 1)
    mat = E.eyeball_material(f"MG6_EyeBall_{s}", os.path.join(EXP, "r30", f"eye_tex_ball_{s}.png"), s, sph.c)
    o = E.mesh_object(f"Eye_Ball.{s}", V - sph.c, F, coll, uvs=U, mat=mat)
    o.location = Vector(tuple(sph.c))
    f0 = o.data.polygons[len(F) // 2]
    if Vector(f0.normal).dot(Vector(tuple(sph.normal(np.array(f0.center) + sph.c)))) < 0:
        o.data.flip_normals()
    o["mmg_spheroid"] = json.dumps(sph.as_dict())
    stats[f"eyeball_{s}"]["tris"] = E.tri_count(o)

# ------------------------------------------------------------------ lids and lashes
NU, NL, NB = 5, 5, 6
HU = (P["DIVE_UP"] + 0.003) * E.PPM          # hidden part of the lid sheets past the opening, px
HL = (P["DIVE_LO"] + 0.003) * E.PPM


def every2(keys):
    k = sorted(keys)
    return k[::2] + ([k[-1]] if (len(k) - 1) % 2 else [])


def lid_edges(s, pose, xs, top, bot):
    H = bot - top
    xm, hw = (xs[0] + xs[-1]) / 2, (xs[-1] - xs[0]) / 2
    arc = np.clip(1 - ((xs - xm) / hw) ** 2, 0, 1) ** 0.6
    Ee, Be = top.copy(), bot.copy()
    if pose == "Blink":
        cc = E.cols(s, "closed_cols")
        ck = np.array(sorted(cc))
        M = np.array([(lambda v: v[0] + 0.45 * (v[1] - v[0]))(cc[int(ck[np.argmin(np.abs(ck - x))])]) for x in xs])
        M = np.clip(M, top + 1, bot - 1)
        Ee, Be = np.minimum(M + 1.5, bot), np.maximum(M - 1.5, top)
    elif pose in ("EyeSmile", "Smile"):
        k = 1.0 if pose == "EyeSmile" else 0.45                   # lower lid rises as an arch (highest in the middle)
        rise = np.clip(1 - ((xs - xm) / hw) ** 2, 0, 1) ** 0.5
        Ee, Be = top + 0.10 * k * H * arc, bot - 0.58 * k * H * rise
    elif pose == "Surprise":
        Ee, Be = top - 0.0022 * E.PPM * arc ** 0.5, bot + 0.0009 * E.PPM * arc ** 0.5
    Be = np.maximum(Be, Ee + (3 if pose != "Blink" else -3))
    return Ee, Be


def band_points(s, x, z):
    """lash band: on the eyeball (BAND_IN above it) inside the socket, rising to the rim, then on the skin"""
    sph, poly = SPH[s], E.opening_poly(s)
    r = E.signed_dist(np.stack([x, z], 1), poly)
    gap = P["BAND_IN"] + (P["T_UP"] + P["BAND_OUT"] - P["BAND_IN"]) * E.smooth((r + 0.003) / (P["DIVE_UP"] + 0.003))
    out = sph.surf(x, z, gap)
    far = r >= P["DIVE_UP"]
    if far.any():
        out[far] = head_point(x[far], z[far], P["BAND_OUT"])
    return out


POSES = ("Basis",) + E.EXPR
for s in E.SIDES:
    sph = SPH[s]
    oc = E.cols(s, "opening_cols")
    xs = np.array(every2(oc), float)
    top = np.array([oc[int(x)][0] for x in xs], float)
    bot = np.array([oc[int(x)][1] for x in xs], float)
    NEXT = int(math.ceil((P["DIVE_UP"] + 0.0045) * E.PPM / 2))
    xsE = np.concatenate([xs[0] - 2 * np.arange(NEXT, 0, -1), xs, xs[-1] + 2 * np.arange(1, NEXT + 1)])
    topE = np.concatenate([[top[0]] * NEXT, top, [top[-1]] * NEXT])
    botE = np.concatenate([[bot[0]] * NEXT, bot, [bot[-1]] * NEXT])
    # hidden borders: past the highest / lowest opening edge within the socket margin around each column (the rounded
    # ends of the opening are short columns next to tall ones)
    win = (P["DIVE_UP"] + 0.004) * E.PPM
    BU = np.array([top[np.abs(xs - x) <= win].min() if (np.abs(xs - x) <= win).any() else topE[i] for i, x in enumerate(xsE)]) - HU
    BL = np.array([bot[np.abs(xs - x) <= win].max() if (np.abs(xs - x) <= win).any() else botE[i] for i, x in enumerate(xsE)]) + HL
    lcs = E.cols(s, "lash_cols")
    bxs = np.array(every2(lcs), float)
    btop = np.array([lcs[int(x)][0] for x in bxs], float) - 1
    bbot = np.array([lcs[int(x)][1] for x in bxs], float) + 1
    lo = E.TGT[s]["lower_lash_bbox"]
    lgx, lgy = np.meshgrid(np.linspace(lo[0] - 1, lo[2] + 1, 6), np.linspace(lo[1] - 1, lo[3] + 1, 6), indexing="ij")
    bx = E.TGT["tex_box"][s]
    uv = lambda px, py: np.stack([(px - bx[0]) / (bx[2] - bx[0]), 1 - (py - bx[1]) / (bx[3] - bx[1])], 1)
    lids, lash = {}, {}
    for pose in POSES:
        Ee, Be = lid_edges(s, "neutral" if pose == "Basis" else pose, xs, top, bot)
        # past the corners (the socket margin) both sheets meet on one line
        mi_, mo_ = (Ee[0] + Be[0]) / 2, (Ee[-1] + Be[-1]) / 2
        EeE = np.concatenate([[mi_] * NEXT, Ee, [mo_] * NEXT])
        BeE = np.concatenate([[mi_] * NEXT, Be, [mo_] * NEXT])
        # lid sheets: column-major, per column skirt, edge, rows to the hidden border
        up_px, up_py, up_g, lo_px, lo_py, lo_g = [], [], [], [], [], []
        for i, x in enumerate(xsE):
            bu, bl = BU[i], BL[i]
            Ee_i, Be_i = EeE[i], BeE[i]
            up_py += [Ee_i] + [Ee_i + (bu - Ee_i) * j / NU for j in range(NU + 1)]
            up_g += [P["SKIRT"]] + [P["GAP_UP"]] * (NU + 1)
            lo_py += [Be_i] + [Be_i + (bl - Be_i) * j / NL for j in range(NL + 1)]
            lo_g += [P["SKIRT"]] + [P["GAP_LO"]] * (NL + 1)
            up_px += [x] * (NU + 2)
            lo_px += [x] * (NL + 2)
        pu = sph.surf(E.X(up_px), E.Z(up_py), np.array(up_g))
        pl = sph.surf(E.X(lo_px), E.Z(lo_py), np.array(lo_g))
        lids[pose] = np.concatenate([pu, pl])
        # lash band follows the upper lid edge (nearest lid column; fading off past the opening)
        near = np.array([np.argmin(np.abs(xs - x)) for x in bxs])
        dist = np.array([max(0.0, xs[0] - x, x - xs[-1]) for x in bxs])
        sh = (Ee - top)[near] * np.clip(1 - dist / 40, 0.35, 1)
        squash = 0.7 if pose == "Blink" else 1.0
        b_px, b_py, b_t = [], [], []
        for k, x in enumerate(bxs):
            h = (bbot[k] - btop[k]) * squash
            for j in range(NB):
                t = j / (NB - 1)
                b_px.append(x)
                b_py.append(bbot[k] + sh[k] - t * h)
                b_t.append(t)
        b_px, b_py, b_t = np.array(b_px), np.array(b_py), np.array(b_t)
        pb = band_points(s, E.X(b_px), E.Z(b_py))
        lift = 0.0013 * np.clip((b_t - 0.55) / 0.45, 0, 1) ** 2      # lash tips curl off the face
        pb[:, 1] -= lift
        # skirt (lid edge thickness) under each band column
        inside = (bxs >= xs[0]) & (bxs <= xs[-1])
        sk_py = bbot + sh
        psk = sph.surf(E.X(bxs), E.Z(sk_py), P["SKIRT"])
        bottom_row = pb.reshape(len(bxs), NB, 3)[:, 0]
        psk = np.where(inside[:, None], psk, bottom_row + np.array([0, 0.0003, 0]))
        band = np.concatenate([psk[:, None], pb.reshape(len(bxs), NB, 3)], 1).reshape(-1, 3)
        # lower lash: follows the lower lid edge near the outer corner
        nb = np.argmin(np.abs(xs - lo[0]))
        dz = (Be - bot)[nb] * 0.7
        lx, lz = E.X(lgx.ravel()), E.Z(lgy.ravel() + dz)
        pll = head_point(lx, lz, P["BAND_OUT"])
        rl = E.signed_dist(np.stack([lx, lz], 1), E.opening_poly(s))
        inl = rl < P["DIVE_LO"]                  # over the socket margin: on the lower rim height above the eyeball
        if inl.any():
            pll[inl] = sph.surf(lx[inl], lz[inl], P["T_LO"] + P["BAND_OUT"])
        lash[pose] = np.concatenate([band, pll])
    nc = len(xsE)
    Fl = E.grid_faces(nc, NU + 2) + E.grid_faces(nc, NL + 2, nc * (NU + 2), flip=True)
    o = E.mesh_object(f"Eye_Lids.{s}", lids["Basis"], Fl, coll, mat=bpy.data.materials["TT_Skin"])
    ln = []                                    # lids shaded with the original face normals (they are skin)
    for p in lids["Basis"]:
        _, n = E.front_hit(ORIG, p[0], p[2])
        ln.append(tuple(n) if n is not None else (0, -1, 0))
    o.data.normals_split_custom_set_from_vertices(ln)
    for pose in E.EXPR:
        E.add_key(o, pose, lids[pose])
    nbc = len(bxs)
    Fb = E.grid_faces(nbc, NB + 1) + E.grid_faces(6, 6, nbc * (NB + 1), flip=False)
    Ub = []
    for k, x in enumerate(bxs):
        Ub.append(uv(np.array([x]), np.array([bbot[k] - 3]))[0])
        for j in range(NB):
            Ub.append(uv(np.array([x]), np.array([bbot[k] - j / (NB - 1) * (bbot[k] - btop[k])]))[0])
    Ub = np.concatenate([np.array(Ub), uv(lgx.ravel(), lgy.ravel())])
    lm = E.toon_tex_material(f"MG6_Lash_{s}", os.path.join(EXP, "r30", f"eye_tex_lash_{s}.png"), lit=(0.85, 0.95, 1.0), clip=True)
    o2 = E.mesh_object(f"Eye_Lash.{s}", lash["Basis"], Fb, coll, uvs=Ub, mat=lm)
    for pose in E.EXPR:
        E.add_key(o2, pose, lash[pose])
    for ob in (o, o2):
        mid = ob.data.polygons[len(ob.data.polygons) // 4]
        stats[f"{ob.name}_normal_y"] = round(mid.normal.y, 3)
    stats[f"lids_{s}"] = dict(tris=E.tri_count(o), lash_tris=E.tri_count(o2))

# ------------------------------------------------------------------ head keys: cheek lift under the eye (EyeSmile, Smile)
basis = np.array([tuple(mw @ v.co) for v in me.vertices])
for pose, amt in (("EyeSmile", 1.0), ("Smile", 0.5)):
    co = basis.copy()
    for s in E.SIDES:
        idx, sd = FRONT[s]
        poly = E.opening_poly(s)
        zc = poly[:, 1].mean()
        z = basis[idx, 2]
        f = E.smooth(sd / 0.002) * (1 - E.smooth((sd - 0.002) / 0.016)) * E.smooth((zc - z) / 0.012 + 0.2)
        co[idx, 2] += 0.0016 * amt * f
        co[idx, 1] -= 0.0005 * amt * f
    E.add_key(head, pose, co)

# ------------------------------------------------------------------ face details: bake Shrinkwrap (FBX keeps the keys), brow keys
fd = [o for o in bpy.data.collections["MainGirlfriend_FaceDetails"].all_objects
      if o.type == "MESH" and any(m.type == "SHRINKWRAP" for m in o.modifiers)]
baked = E.bake_modifiers_with_keys(fd)
stats["baked"] = baked
E.brow_keys(HEAD)

for o in bpy.data.objects:
    if o.type == "MESH" and o.data.shape_keys:
        for k in o.data.shape_keys.key_blocks[1:]:
            k.value = 0.0
bpy.context.view_layer.update()
stats["tris"] = {o.name: E.tri_count(o) for o in coll.objects if o.type == "MESH"}
stats["tris"]["Blockout_Head"] = E.tri_count(head)
if "V6B_OUT" not in os.environ:
    json.dump(stats, open(os.path.join(EXP, "spec", "eye_v6b_stats.json"), "w"), indent=1)
    json.dump({s: json.loads(bpy.data.materials[f"MG6_EyeBall_{s}"]["mmg_eye_uv"]) for s in E.SIDES},
              open(os.path.join(EXP, "spec", "eye_v6b_unity_proj.json"), "w"), indent=1)     # for MMGExp/AnimeToonEye
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, os.environ.get("V6B_OUT", "MG_ToonTest_01_v6b_eye.blend")))
print("V6B_OK", json.dumps(stats))
