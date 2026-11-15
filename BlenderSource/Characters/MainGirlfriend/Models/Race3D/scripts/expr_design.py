"""Race3D v2 expression design (pure numpy, shared by Blender build and the 2D preview): lid edge heights per column.

Inputs per eye (r30 pixel space, py grows downward): column x, Basis edges E0u / E0l, Blink edges Ebu / Ebl, the r30
opening outline. Every pose returns new upper / lower edge heights; the build turns them into per-column fractions of
the Blink motion (cu, cl), so a pose is "Blink by a different amount in every column".
"""
import numpy as np

# pose parameters (r30 px, 1 px = 0.55 mm on the face)
HAPPY_ARCH = 0.15        # closed smile: middle of the closing line above the Blink line, share of the eye height
HAPPY_TAIL = 3.0         # outer end of the closing line raised (px)
HAPPY_A_UP = 0.15        # crescent stage: share of the way the upper lid goes toward the closed smile line
HAPPY_A_OPEN = 0.40      # crescent stage: opening left in the middle, share of the eye height
ANGRY_IN, ANGRY_OUT, ANGRY_LO = 0.42, 0.08, 0.20
SAD_OUT, SAD_IN, SAD_LO = 0.32, -0.06, 0.14
CRY_UP, CRY_LO = 0.12, 0.38
SURPRISE_UP, SURPRISE_LO = -0.09, -0.05


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def eye_u(s, x, opening):
    """0 at the inner corner, 1 at the outer corner of the r30 opening (L: inner = smaller px)"""
    op = np.asarray(opening, float)
    xi, xo = (op[:, 0].min(), op[:, 0].max()) if s == "L" else (op[:, 0].max(), op[:, 0].min())
    return (np.asarray(x, float) - xi) / (xo - xi)


def profiles(u):
    uc = np.clip(u, 0, 1)
    bump = np.clip(1 - (2 * uc - 1) ** 2, 0, 1) ** 0.7
    tail = smooth((uc - 0.55) / 0.45)
    inner = smooth((0.45 - uc) / 0.45)
    return bump, tail, inner


def poses(s, d):
    """{pose: (Eu, El)} for one eye; d: dict with x, E0u, E0l, Ebu, Ebl, opening"""
    x = np.asarray(d["x"], float)
    E0u, E0l = np.asarray(d["E0u"], float), np.asarray(d["E0l"], float)
    Ebu, Ebl = np.asarray(d["Ebu"], float), np.asarray(d["Ebl"], float)
    u = eye_u(s, x, d["opening"])
    bump, tail, inner = profiles(u)
    Hmid = float(np.max(E0l - E0u))
    out = {}
    # corner to corner base line (outer end a little raised); every smile curve is an arch above it
    ci, co = np.argmin(np.abs(u - 0.0)), np.argmin(np.abs(u - 1.0))
    yi, yo = (E0u[ci] + E0l[ci]) / 2, (E0u[co] + E0l[co]) / 2 - HAPPY_TAIL
    base = yi + (yo - yi) * np.clip(u, 0, 1)
    # Happy B: closed smile, a smooth arch from corner to corner (not the r30 closed-eye line, which sags)
    archB = np.clip(1 - (2 * np.clip(u, 0, 1) - 1) ** 2, 0, 1) ** 0.8
    Mh = base - HAPPY_ARCH * Hmid * archB
    EuB, ElB = Mh + 1.5, Mh - 1.5
    out["ExHappyB"] = (EuB, ElB)
    # Happy A: crescent - upper lid part way down; the lower lid edge is its own arch (corner to corner, highest in the
    # middle), not a blend of the open (U-shaped) edge and the closed line, which would come out straight
    EuA = E0u + HAPPY_A_UP * (EuB - E0u)
    mid = int(np.argmin(np.abs(u - 0.5)))
    arch = base[mid] - (EuA[mid] + HAPPY_A_OPEN * Hmid)
    archA = np.clip(1 - (2 * np.clip(u, 0, 1) - 1) ** 2, 0, 1)
    ElA = np.clip(base - arch * archA, EuA + 2.0, E0l)
    out["ExHappyA"] = (EuA, ElA)
    blink = lambda cu, cl: (E0u + cu * (Ebu - E0u), E0l + cl * (Ebl - E0l))
    out["ExAngry"] = blink(ANGRY_OUT + (ANGRY_IN - ANGRY_OUT) * inner ** 0.8 * (1 - tail), ANGRY_LO * bump)
    out["ExSad"] = blink(SAD_IN + (SAD_OUT - SAD_IN) * tail, SAD_LO * bump)
    out["ExCry"] = blink(CRY_UP * bump ** 0.3, CRY_LO * bump)
    return out


C_LIMITS = ((-0.5, 1.35), (-0.5, 1.8))     # upper / lower: next to the corners Blink hardly moves, keep the share sane
HAPPY_TAIL_KEEP = 0.45                      # closed / crescent smile: the lash past the outer corner follows Blink less


def fractions(Eu, El, d):
    """per-column share of the Blink motion for new edges (columns where Blink hardly moves take the neighbour's)"""
    E0u, E0l = np.asarray(d["E0u"], float), np.asarray(d["E0l"], float)
    Ebu, Ebl = np.asarray(d["Ebu"], float), np.asarray(d["Ebl"], float)
    out = []
    for E0, Eb, En in ((E0u, Ebu, Eu), (E0l, Ebl, El)):
        den = Eb - E0
        ok = np.abs(den) > 2.0
        c = np.where(ok, (En - E0) / np.where(ok, den, 1), np.nan)
        idx = np.arange(len(c))
        good = idx[ok]
        c = np.where(ok, c, np.interp(idx, good, c[good]))
        out.append(c)
    out = [np.clip(out[0], *C_LIMITS[0]), np.clip(out[1], *C_LIMITS[1])]
    return out[0], out[1]
