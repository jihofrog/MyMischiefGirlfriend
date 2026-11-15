"""ToonTest_01 step 60 (python with numpy / scipy / PIL): 2D mock-ups of the far eye outer corner (no mesh change).

usage: python t60_eye_v6g_2d.py <tag> [<tag> ...]
On the t48 close ups (far eye, +-35 / +-45, no hair) with the t59 mask:
  fixL  "liner": the skin coloured area between the white and the lashes takes the lash colour (sampled from the lash
        band right above it), so the upper lash runs down the outer edge of the white into the lower lash
  fixC  "lid cover": the eyelid / eye tail skin covers that area and the thin white strip beyond the iris on the outer
        side (skin colour sampled next to it); a lash coloured line (lid margin) follows the new edge next to the iris
Normal face skin outside the eye outline, the iris and the rest of the white are not touched.
  fixO  "outline": the lash line continues from the end of the upper band down the outer edge of the white into the
        lower lid (band thickness thinning to a fine line), the skin area between white and lashes in lash colour
  fixW  "wrap": the upper lid wraps down the outer side - under the band the outer white strip in lash colour, below it
        the eye tail skin covers the strip and the skin area, a lash line along the iris edge thinning downward
Writes renders/<tag>_g6_fixL_ / fixC_ / fixO_ / fixW_<side>_<a>.png.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, binary_erosion, gaussian_filter, label

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t49_eye_v6f_metrics as M  # noqa: E402
import t59_eye_v6g_mask as G  # noqa: E402


def soft(mask, r=1.2):
    return np.clip(gaussian_filter(mask.astype(float), r) * 1.6, 0, 1)[..., None]


def fix(tag, s, a):
    r = G.analyse(tag, s, a)
    toon = M.load(os.path.join(M.R, f"{tag}_f6_{s}_toon_{a}.png"))
    ball, lash, abn, eye = r["ball"], r["lash"], r["abn"], r["eye"]
    lum = 0.2126 * toon[..., 0] + 0.7152 * toon[..., 1] + 0.0722 * toon[..., 2]
    mx, mn = toon.max(2), toon.min(2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    ys, xs = np.nonzero(ball)
    cx = (xs.min() + xs.max()) / 2
    X = np.arange(ball.shape[1])[None, :].repeat(ball.shape[0], 0)
    outer = X < cx if s == "R" else X > cx
    # lash colour: dark lash pixels of the band nearest to the area
    near_lash = lash & binary_dilation(abn, iterations=30) & (lum < 0.35)
    lash_col = np.median(toon[near_lash], 0) if near_lash.sum() > 20 else np.array([0.18, 0.08, 0.07])
    # A: liner
    fl = toon.copy()
    reg = binary_dilation(abn, iterations=1)
    fl = fl * (1 - soft(reg)) + lash_col * soft(reg)
    # B: lid cover - white strip on the outer side between the iris and the eyeball outline
    white = ball & (lum > 0.72) & (sat < 0.16)
    iris = ball & ~white
    lb, n = label(iris)
    iris = lb == (1 + int(np.argmax(np.bincount(lb.ravel())[1:]))) if n else iris
    rows = np.nonzero(iris.any(1))[0]
    strip = np.zeros_like(ball)
    for y in rows:
        xi = np.nonzero(iris[y])[0]
        if s == "R":
            strip[y, :xi.min()] = white[y, :xi.min()]
        else:
            strip[y, xi.max() + 1:] = white[y, xi.max() + 1:]
    strip &= outer
    cover = (abn | strip) & ~iris
    cover = binary_dilation(cover, iterations=1) & ~iris
    ring = binary_dilation(cover, iterations=8) & ~cover & ~eye
    skin_col = np.median(toon[ring], 0) if ring.sum() > 20 else np.array([0.99, 0.87, 0.80])
    fc = toon * (1 - soft(cover)) + skin_col * soft(cover)
    margin = binary_dilation(cover, iterations=3) & ~cover & (ball | binary_dilation(ball, iterations=2)) & ~lash
    margin &= binary_dilation(iris | white, iterations=1)
    fc = fc * (1 - soft(margin, 0.8)) + lash_col * soft(margin, 0.8)
    # C: outline - the lash line goes on from the end of the upper band down the outer edge of the white and into the
    # lower lid, thinning from the band thickness to a fine line; nothing else changes
    fo = toon.copy()
    H, W = ball.shape
    rows = np.nonzero(ball.any(1))[0]
    band_rows = [y for y in rows if (lash[y] & outer[y]).any()]
    y_end = max(band_rows) if band_rows else rows.min()
    y_bot = rows.max()
    line = np.zeros_like(ball)
    for y in rows:
        if y < y_end - 6:
            continue
        xb = np.nonzero(ball[y])[0]
        xe = xb.min() if s == "R" else xb.max()
        t = np.clip((y - y_end) / max(1.0, (y_bot - y_end)), 0, 1)
        th = 9 * (1 - t) + 3 * t
        if s == "R":
            line[y, max(0, int(xe - th * 0.6)):int(xe + th * 0.4) + 1] = True
        else:
            line[y, int(xe - th * 0.4):int(xe + th * 0.6) + 1] = True
    line |= binary_dilation(abn, iterations=1)
    fo = fo * (1 - soft(line, 0.9)) + lash_col * soft(line, 0.9)
    # W: wrap - the upper lid wraps down the outer side: under the band the outer white strip takes the lash colour (the
    # band meets the iris), below the band end the eye tail skin covers the strip and the skin area, and a lash line along
    # the iris edge thins from the band thickness to a fine line at the lower lid
    fw = toon.copy()
    # outer white crescent: white beyond the iris ellipse (moments fit) on the outer side
    iy, ix = np.nonzero(iris)
    my, mxx = iy.mean(), ix.mean()
    cov_ = np.cov(np.stack([ix - mxx, iy - my]))
    ev, evec = np.linalg.eigh(cov_)
    Yg, Xg = np.mgrid[0:H, 0:W]
    d = np.stack([Xg - mxx, Yg - my], -1) @ evec
    ell = (d[..., 0] ** 2 / (4 * ev[0]) + d[..., 1] ** 2 / (4 * ev[1])) <= 1.0
    side = (Xg < mxx) if s == "R" else (Xg > mxx)
    crescent = white & ~ell & side & outer
    lb, n = label(crescent)
    if n:
        sizes = np.bincount(lb.ravel())
        crescent = np.isin(lb, [i for i in range(1, n + 1) if sizes[i] >= 40])
    under_band = crescent & (Yg <= y_end)
    below = (crescent | abn) & (Yg > y_end)
    fw = fw * (1 - soft(under_band, 0.8)) + lash_col * soft(under_band, 0.8)
    cov = binary_dilation(below, iterations=1) & ~iris
    fw = fw * (1 - soft(cov)) + skin_col * soft(cov)
    wl = np.zeros_like(ball)
    for y in rows:
        if y < y_end - 4:
            continue
        xi = np.nonzero(ell[y] & ball[y])[0]
        if not len(xi):
            continue
        xe = xi.min() if s == "R" else xi.max()
        t = np.clip((y - y_end) / max(1.0, (y_bot - y_end)), 0, 1)
        th = 9 * (1 - t) + 3 * t
        if s == "R":
            wl[y, max(0, int(xe - th)):int(xe + 2)] = True
        else:
            wl[y, int(xe - 1):int(xe + th) + 1] = True
    wl &= ~binary_erosion(iris, iterations=3)
    fw = fw * (1 - soft(wl, 0.8)) + lash_col * soft(wl, 0.8)
    for name, im in (("fixL", fl), ("fixC", fc), ("fixO", fo), ("fixW", fw)):
        Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8)).save(os.path.join(M.R, f"{tag}_g6_{name}_{s}_{a}.png"))
    return dict(abnormal=int(abn.sum()), covered_white=int((strip & ~abn).sum()))


if __name__ == "__main__":
    for tag in sys.argv[1:]:
        for s, a in G.VIEWS:
            print(tag, s, a, fix(tag, s, a))
