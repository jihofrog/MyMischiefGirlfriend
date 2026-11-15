"""Race3D v3b expression design (v3 + checks pass; pure numpy). v3b adds to v3 (expr_design_v3.py, unchanged):
  Happy C  a stage at Happy 0.85: the upper lid comes down to near the closed arch keeping its arch, the lower lid stays
           a cradle (U). From A (0.6) to C both edges keep their curve; only from C to B (0.85 -> 1, the slit under the
           lash band) does the lower edge turn from U to the closed arch, so no straight cut shows in between
  Angry 2  a stronger Angry candidate (ExAngry2), next to the kept ExAngry

Earlier v3 notes:

Changes from v2 (expr_design.py, kept for the before / after sheets):
  Happy A  the lower lid no longer rises as a ridge to the middle: it lifts as a shallow cradle under the iris (the open
           U edge raised most in the middle, still U-shaped); the upper lid comes down a little more
  Happy B  the closed smile arch is rounder (apex profile ^1.2) and sits 4 px lower
  Angry    the upper lid line is pressed down from the inner corner in a straight slant (inner 55 %, outer 3 %)
  Sad      outer upper lid droops more (36 %), inner lifts (-8 %), lower lid 18 %
Lid edge heights per column.

Inputs per eye (r30 pixel space, py grows downward): column x, Basis edges E0u / E0l, Blink edges Ebu / Ebl, the r30
opening outline. Every pose returns new upper / lower edge heights; the build turns them into per-column fractions of
the Blink motion (cu, cl), so a pose is "Blink by a different amount in every column".
"""
import numpy as np

# pose parameters (r30 px, 1 px = 0.55 mm on the face)
HAPPY_ARCH = 0.17        # closed smile: arch height above the corner-to-corner line, share of the eye height
HAPPY_ARCH_EXP = 1.2     # closed smile: arch profile exponent (rounder apex, softer ends)
HAPPY_BASE_DROP = 4.0    # closed smile: the corner-to-corner line a little lower (px)
HAPPY_TAIL = 3.0         # outer end of the closing line raised (px)
HAPPY_A_UP = 0.24        # smile stage A: share of the way the upper lid goes toward the closed smile line
HAPPY_A_RISE = 0.24      # smile stage A: lower lid lift in the middle, share of the eye height (cradle, stays U-shaped)
ANGRY_IN, ANGRY_OUT, ANGRY_LO, ANGRY_LO_TAIL = 0.55, 0.03, 0.12, 0.08
ANGRY2_IN, ANGRY2_OUT, ANGRY2_LO, ANGRY2_LO_TAIL = 0.66, 0.05, 0.16, 0.14
HAPPY_C_GAP = 0.11       # stage C: upper lid this share of the eye height above the closed arch
HAPPY_C_RISE = 0.34      # stage C: lower lid cradle lift in the middle
SAD_OUT, SAD_IN, SAD_LO = 0.36, -0.08, 0.18
CRY_UP, CRY_LO = 0.12, 0.40


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
    # corner to corner base line (outer end a little raised, the whole line a little lower)
    ci, co = np.argmin(np.abs(u - 0.0)), np.argmin(np.abs(u - 1.0))
    yi, yo = (E0u[ci] + E0l[ci]) / 2 + HAPPY_BASE_DROP, (E0u[co] + E0l[co]) / 2 - HAPPY_TAIL + HAPPY_BASE_DROP
    uc = np.clip(u, 0, 1)
    base = yi + (yo - yi) * uc
    # Happy B: closed smile, a round arch from corner to corner
    archB = np.clip(1 - (2 * uc - 1) ** 2, 0, 1) ** HAPPY_ARCH_EXP
    Mh = base - HAPPY_ARCH * Hmid * archB
    EuB, ElB = Mh + 1.5, Mh - 1.5
    out["ExHappyB"] = (EuB, ElB)
    # Happy A: upper lid part way down; the lower lid lifts as a shallow cradle under the iris (no ridge in the middle)
    EuA = E0u + HAPPY_A_UP * (EuB - E0u)
    cradle = np.sin(np.pi * uc) ** 0.8
    ElA = np.clip(E0l - HAPPY_A_RISE * Hmid * cradle, EuA + 2.0, E0l)
    out["ExHappyA"] = (EuA, ElA)
    # Happy C: upper lid just above the closed arch (still arched), lower lid a higher cradle (still U-shaped)
    EuC = np.minimum(Mh - HAPPY_C_GAP * Hmid * archB, E0u + 0.92 * (EuB - E0u))
    EuC = np.maximum(EuC, E0u)
    ElC = np.clip(E0l - HAPPY_C_RISE * Hmid * cradle, EuC + 2.0, E0l)
    out["ExHappyC"] = (EuC, ElC)
    blink = lambda cu, cl: (E0u + cu * (Ebu - E0u), E0l + cl * (Ebl - E0l))
    slant = np.clip(1 - np.clip(u, 0, 1), 0, 1) ** 1.3            # straight pressed line from the inner corner
    out["ExAngry"] = blink(ANGRY_OUT + (ANGRY_IN - ANGRY_OUT) * slant, ANGRY_LO * bump + ANGRY_LO_TAIL * tail)
    out["ExAngry2"] = blink(ANGRY2_OUT + (ANGRY2_IN - ANGRY2_OUT) * slant ** 0.9, ANGRY2_LO * bump + ANGRY2_LO_TAIL * tail)
    out["ExSad"] = blink(SAD_IN + (SAD_OUT - SAD_IN) * tail ** 0.8, SAD_LO * bump)
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
