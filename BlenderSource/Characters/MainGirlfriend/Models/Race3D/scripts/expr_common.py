"""Race3D v2 expression helpers (Blender side): eyeball spheroid, lid sheets in r30 pixel space, lash transfer.

The v6 lid sheets were built as sph.surf(x(px), z(py), gap): a point on the eyeball spheroid (front projection px, py)
pushed out along the surface normal by a per-row gap. foot() inverts that for any vertex, so a new pose only has to
give new lid edge heights (py) per column; the rows between the edge and the hidden border keep their proportions and
every vertex keeps its own gap.
"""
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.abspath(os.path.join(HERE, "..", "..", "..", "Experiments", "ToonTest_01"))
sys.path.insert(0, os.path.join(EXP, "scripts"))
import eye_v6_common as E  # noqa: E402

O = bpy.data.objects
ROWS = 7


def world(o, data=None):
    mw = o.matrix_world
    return np.array([tuple(mw @ d.co) for d in (data if data is not None else o.data.vertices)])


def key_world(o, name):
    return world(o, o.data.shape_keys.key_blocks[name].data)


def set_key(o, name, P):
    """add or replace shape key `name` (world coordinates); other keys untouched"""
    return E.add_key(o, name, P)


def fit_ball(s):
    """spheroid of Eye_Ball.<s> (its vertices lie on it)"""
    P = world(O[f"Eye_Ball.{s}"])
    c0 = P.mean(0)
    init = E.Spheroid((c0[0], P[:, 1].max(), c0[2]), 0.07, 0.09)
    sph = E.fit_spheroid(P, np.ones(len(P)), init, R_range=(0.02, 0.2), C_ratio=(0.6, 3.0), iters=120)
    r = sph.front_y(P[:, 0], P[:, 2]) - P[:, 1]
    return sph, float(np.nanmax(np.abs(r)))


def surf(sph, x, z, g):
    """sph.surf with the depth continued past the silhouette (hidden rows of the lid sheets)"""
    x, z = np.asarray(x, float), np.asarray(z, float)
    p = np.stack([x, sph.front_y_clamped(x, z), z], -1)
    return p + sph.normal(p) * np.asarray(g, float)[..., None]


def foot(sph, P, iters=25):
    """(x, z, gap) with surf(x, z, gap) = P (Newton, numeric Jacobian)"""
    P = np.asarray(P, float)
    x, z = P[:, 0].copy(), P[:, 2].copy()
    g = (sph.front_y_clamped(x, z) - P[:, 1]) * sph.ny(x, z)
    q = np.stack([x, z, g], 1)
    for _ in range(iters):
        F = surf(sph, q[:, 0], q[:, 1], q[:, 2]) - P
        J = np.zeros((len(P), 3, 3))
        for k in range(3):
            dq = np.zeros(3)
            dq[k] = 1e-6
            qq = q + dq
            J[:, :, k] = (surf(sph, qq[:, 0], qq[:, 1], qq[:, 2]) - P - F) / 1e-6
        step = np.linalg.solve(J, -F[..., None])[..., 0]
        q += step
        if np.abs(step).max() < 1e-10:
            break
    res = np.linalg.norm(surf(sph, q[:, 0], q[:, 1], q[:, 2]) - P, axis=1)
    return q, float(res.max())


class Lids:
    """Eye_Lids.<s>: upper sheet columns 0..nc-1 then lower sheet, 7 rows each (row 0 skirt, 1 edge, 6 hidden border)"""

    def __init__(self, s, sph):
        self.s, self.sph = s, sph
        self.o = O[f"Eye_Lids.{s}"]
        self.nv = len(self.o.data.vertices)
        self.nc = self.nv // (2 * ROWS)
        B = key_world(self.o, "Basis")
        self.q, self.res = foot(sph, B)              # footpoints of the Basis
        self.py = E.PY(self.q[:, 1])
        self.idx_up = np.arange(self.nc)[:, None] * ROWS + np.arange(ROWS)[None]
        self.idx_lo = self.nc * ROWS + self.idx_up

    def edges(self, name="Basis"):
        """(upper edge py, lower edge py) per column of a key (footpoint space)"""
        q, _ = foot(self.sph, key_world(self.o, name))
        py = E.PY(q[:, 1])
        return py[self.idx_up[:, 1]], py[self.idx_lo[:, 1]]

    def x_px(self):
        return E.PX(self.q[self.idx_up[:, 1], 0])

    def build(self, Eu, El):
        """world coordinates for new edge heights Eu / El (py per column); border rows fixed, rows in proportion"""
        q = self.q.copy()
        for idx, Enew in ((self.idx_up, Eu), (self.idx_lo, El)):
            E0 = self.py[idx[:, 1]]
            Bd = self.py[idx[:, ROWS - 1]]
            for r in range(ROWS):
                f = np.where(np.abs(E0 - Bd) > 1e-6, (self.py[idx[:, r]] - Bd) / (E0 - Bd), 0.0)
                q[idx[:, r], 1] = E.Z(Bd + f * (Enew - Bd))
        return surf(self.sph, q[:, 0], q[:, 1], q[:, 2])


def ball_y(bvh, P):
    out = np.full(len(P), np.nan)
    for i, p in enumerate(P):
        y, _ = E.front_hit(bvh, p[0], p[2])
        if y is not None:
            out[i] = y
    return out
