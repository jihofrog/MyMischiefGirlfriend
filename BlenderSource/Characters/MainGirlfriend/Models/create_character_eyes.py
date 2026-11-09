"""MainGirlfriend anime-style eyes on the body blockout head.

Run inside Blender 4.x / 5.x (Scripting workspace > Run Script) after
create_character_blockout.py has built the MainGirlfriend_Blockout collection.

- Reads the evaluated Blockout_Head mesh (position, size, front surface) and builds
  both eyes as thin shells that follow the face, not as spheres.
- The eye opening is a smooth closed spline (wide upper lid, softly narrowing bottom,
  lifted outer corner). Each eye is split into separate objects:
    Eye_Root.L              empty at the eye centre (move / scale the whole eye)
      Eye_White.L           eye white (mesh, soft lid shadow at the top)
      Eye_UpperLid.L        thick dark-brown upper lid line: forked inner end, lifted outer wing (mesh)
        Eye_UpperLashes.L   3-4 flat tapered lash spikes, longer toward the outer corner (mesh)
      Eye_UpperCrease.L     thin double-eyelid crease line above the lid (curve)
      Eye_OuterLine.L       outer side line: thick under the lid wing, tapering down the outer side (mesh)
      Eye_LowerLid.L        faint thin lower lid line (curve)
      Eye_Gaze.L            empty; move it in local X / Z to slide the gaze
        Eye_Iris.L          vertical oval iris: chocolate -> warm brown -> red-brown, radial streaks
        Eye_Pupil.L         dark-brown vertical oval pupil
        Eye_Highlight.L     large highlight at the top of the iris, small one at the side
  Iris, pupil and highlight shrinkwrap onto the eye white, so moving Eye_Gaze keeps
  them on the eye surface and clips them at its rim.
- Character faces -Y, left side (.L) is +X. The right eye is an exact mirror.
- Only the MainGirlfriend_Eyes collection is rebuilt on every run. Body meshes,
  Reference_Images and every other collection are left untouched.
- The .blend file is never saved by this script.

No eyebrows, nose, mouth or hair yet.
"""

import math

import bpy
from mathutils import Vector, kdtree
from mathutils.bvhtree import BVHTree


# ===========================================================================
# Eye placement and size (fractions of the head mesh height, so the face width can change; measured on Front.png)
# ===========================================================================

EYE_CENTER_HEIGHT = 0.3536 # eye centre above the chin, fraction of head height (Front.png: Z 1.29 m)
EYE_SPACING = 0.426        # distance between the two eye centres, fraction of head height (Front.png: 0.228 m)
EYE_WIDTH = 0.2206         # eye opening width, fraction of head height (Front.png: 0.118 m)
EYE_HEIGHT = 0.1542        # eye opening height, fraction of head height
EYE_TILT = 2.0             # degrees; positive lifts the outer corner and lowers the inner corner

# Eye opening outline: control points of a smooth closed curve, counter-clockwise from the outer corner.
# u: -1 inner corner (nose) .. +1 outer corner; v: -1 bottom .. +1 top.
# Concept: the top peaks about a third in from the inner corner and slopes down to a high outer corner;
# the bottom is a round U that narrows and sits slightly toward the nose.
EYE_SHAPE = (
    (1.00, 0.45), (0.85, 0.62), (0.50, 0.80), (0.10, 0.94), (-0.35, 1.00), (-0.75, 0.86),
    (-1.00, 0.55), (-0.94, -0.05), (-0.74, -0.60), (-0.35, -0.95), (0.10, -1.00), (0.50, -0.82),
    (0.80, -0.42), (0.96, 0.05),
)

# ===========================================================================
# Depth (metres)
# ===========================================================================

EYE_PROTRUSION = 0.001     # gap between the face surface and the rim of the eye white
EYE_BULGE = 0.004          # extra forward bulge at the eye centre; 0 = flat on the face
LAYER_GAP = 0.0003         # forward spacing between white / iris / pupil / highlight / lids

# ===========================================================================
# Iris, pupil and highlights (fractions)
# ===========================================================================

IRIS_WIDTH = 0.68          # fraction of eye width
IRIS_HEIGHT = 0.95         # fraction of eye height (vertical oval); the top tucks under the upper lid
IRIS_OFFSET = (0.14, 0.03)  # (toward the nose, up), fraction of eye width / height
IRIS_STREAKS = 0.35        # strength of the radial streak pattern (0 = none)
IRIS_STREAK_SCALE = 9.0    # number-ish of radial streaks; higher = finer
PUPIL_SIZE = (0.34, 0.44)  # (width, height), fraction of iris width / height (vertical oval)
PUPIL_OFFSET = (0.02, -0.03)  # (toward the nose, up), fraction of iris width / height
HIGHLIGHTS = (
    # (width, height, toward the nose, up): sizes as fractions of iris width,
    # offsets as fractions of iris width / height from the iris centre
    (0.21, 0.20, 0.03, 0.27),   # larger highlight just above the pupil
    (0.16, 0.16, 0.38, 0.12),   # smaller highlight on the inner (nose) edge of the iris
)

# ===========================================================================
# Lids and lashes
# ===========================================================================

UPPER_LID_THICKNESS = 0.013    # metres at the thickest part (concept: about 14% of the eye width)
UPPER_LID_INNER = 0.2          # thickness at the inner corner, fraction of UPPER_LID_THICKNESS
UPPER_LID_OVERLAP = 0.35       # share of the lid line that covers the top edge of the eye white
UPPER_LID_END = 0.4            # the lid leaves the outline on the outer side at this height (fraction of half height)
EYE_WING_LENGTH = 0.013        # metres the lid line flicks out past that point
EYE_WING_ANGLE = 15.0          # degrees above horizontal for that outer wing (plus EYE_TILT)
INNER_FORK_AT = 0.12           # the lid line splits here near the inner corner (0 = inner .. 1 = outer)
INNER_FORK_LENGTH = 0.011      # length of the short prong toward the nose (m)
INNER_FORK_ANGLE = 10.0        # degrees above horizontal for that prong
UPPER_LASHES = (
    # (position along the upper lid 0 = inner .. 1 = outer, length m, sweep toward the outer corner deg)
    (0.57, 0.011, 0.0),
    (0.80, 0.010, 28.0),
    (0.95, 0.009, 55.0),
)
LASH_BEND = 20.0               # extra outward curl along each lash (deg)
LASH_WIDTH = 0.0045            # lash width at the root (m); short thick spikes that taper to a point
LASH_LIFT = 0.0015             # lash tips lift this far off the face (m)
CREASE_RANGE = (0.16, 0.56)    # double-eyelid crease span along the upper lid (0 = inner .. 1 = outer); short, inner half
CREASE_GAP = 0.004             # gap between the top of the lid line and the crease (m), more in the middle
CREASE_ARCH = 0.003            # extra gap at the middle of the crease (m)
CREASE_RADIUS = 0.001          # crease line thickness (m)
OUTER_LINE_WIDTH = 0.005       # outer side line width where it leaves the upper lid (m)
OUTER_LINE_LENGTH = 0.045      # length down the outer side before it tapers away (m)
OUTER_LINE_OVERLAP = 0.3       # share of the outer side line that covers the eye white edge
LOWER_LID_RANGE = (0.30, 0.78)  # faint lower lid line span along the lower edge (0 = inner .. 1 = outer corner)
LOWER_LID_RADIUS = 0.0005      # lower lid line thickness (m)
LOWER_LID_OFFSET = 0.0005      # gap below the eye white edge (m)

# ===========================================================================
# Colours (sRGB hex)
# ===========================================================================

COLOR_WHITE = "FAF3EF"
COLOR_WHITE_SHADOW = "D8C5C6"   # soft shadow the upper lid casts on the eye white
COLOR_IRIS_TOP = "2A1616"       # dark chocolate
COLOR_IRIS_MIDDLE = "623430"    # warm brown
COLOR_IRIS_BOTTOM = "B86E58"    # bright red-brown
COLOR_IRIS_RIM = "1A0B08"       # darker ring at the iris edge
COLOR_IRIS_GLOW = "C8703F"      # warm glow around the pupil
COLOR_PUPIL = "24100A"
COLOR_HIGHLIGHT = "F6F2FF"      # white with a faint lavender tint
COLOR_UPPER_LID = "140805"
COLOR_LASH = "120704"
COLOR_CREASE = "8C5442"
COLOR_OUTER_LINE = "40190F"
COLOR_LOWER_LID = "B07A68"

# ===========================================================================
# Output
# ===========================================================================

COLLECTION_NAME = "MainGirlfriend_Eyes"
OBJECT_PREFIX = "Eye_"
PART_TAG = "mg_eye_part"
BLOCKOUT_COLLECTION = "MainGirlfriend_Blockout"
HEAD_PART = ("mg_blockout_part", "Head")
HEAD_OBJECT_NAME = "Blockout_Head"
PROTECTED_COLLECTION_NAME = "Reference_Images"
MATERIAL_PREFIX = "MG_Eye_"
IRIS_GRADIENT_ATTRIBUTE = "IrisGradient"  # vertex colours with the same 3-colour gradient (for export)

RINGS = 10                 # rings per disc (centre to rim)
SEGMENTS = 64              # vertices around each disc
LID_SAMPLES = 48           # samples along the upper lid line
GAZE_FOLLOWS_SURFACE = True  # shrinkwrap iris / pupil / highlight onto the eye white
CLIP_MARGIN = 0.985        # clipped iris points stay this far inside the eye white rim
SYMMETRY_TOLERANCE = 0.0005  # metres, left/right difference allowed after the shrinkwrap modifiers
LID_LAYER = 4              # lids and lashes sit this many LAYER_GAPs in front of the eye white


# ---------------------------------------------------------------------------
# 2D eye shapes. u points away from the nose (outer corner), v points up.
# ---------------------------------------------------------------------------

def rotate(u, v, degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return u * c - v * s, u * s + v * c


class Outline:
    """Superellipse around (cu, cv) with separate upper / lower half heights."""

    def __init__(self, cu, cv, half_width, half_top, half_bottom, exponent=2.0):
        self.cu, self.cv = cu, cv
        self.a, self.top, self.bottom = half_width, half_top, half_bottom
        self.n = exponent

    def point(self, angle, scale=1.0):
        c, s = math.cos(angle), math.sin(angle)
        e = 2.0 / self.n
        u = self.a * math.copysign(abs(c) ** e, c)
        v = (self.top if s >= 0.0 else self.bottom) * math.copysign(abs(s) ** e, s)
        return self.cu + u * scale, self.cv + v * scale

    def metric(self, u, v):
        """0 at the centre, 1 on the outline, > 1 outside."""
        du, dv = u - self.cu, v - self.cv
        half_v = self.top if dv >= 0.0 else self.bottom
        return (abs(du) / self.a) ** self.n + (abs(dv) / half_v) ** self.n


def ellipse(cu, cv, half_width, half_height):
    return Outline(cu, cv, half_width, half_height, half_height)


class SplineOutline:
    """Closed Catmull-Rom curve through control points (star-shaped around the origin)."""

    def __init__(self, points, half_width, half_height, tilt):
        ctrl = [rotate(u * half_width, v * half_height, tilt) for u, v in points]
        n = len(ctrl)
        self.polygon = []
        for i in range(n):
            p0, p1, p2, p3 = ctrl[i - 1], ctrl[i], ctrl[(i + 1) % n], ctrl[(i + 2) % n]
            for step in range(32):
                t = step / 32.0
                self.polygon.append(tuple(
                    0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3)
                    for a, b, c, d in zip(p0, p1, p2, p3)
                ))
        self.cu = self.cv = 0.0
        polar = sorted((math.atan2(v, u), math.hypot(u, v)) for u, v in self.polygon)
        self.polar = [(a - 2.0 * math.pi, r) for a, r in polar[-2:]] + polar + [(a + 2.0 * math.pi, r) for a, r in polar[:2]]

    def radius(self, angle):
        angle = math.atan2(math.sin(angle), math.cos(angle))
        lo, hi = 0, len(self.polar) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.polar[mid][0] <= angle:
                lo = mid
            else:
                hi = mid
        (a0, r0), (a1, r1) = self.polar[lo], self.polar[hi]
        return r0 + (r1 - r0) * (angle - a0) / (a1 - a0) if a1 > a0 else r0

    def point(self, angle, scale=1.0):
        r = self.radius(angle) * scale
        return r * math.cos(angle), r * math.sin(angle)

    def metric(self, u, v):
        r = math.hypot(u, v)
        return 0.0 if r == 0.0 else (r / self.radius(math.atan2(v, u))) ** 2

    def edges(self):
        """(upper, lower) rim paths, each running from the inner corner (min u) to the outer corner (max u)."""
        poly = self.polygon
        inner = min(range(len(poly)), key=lambda i: poly[i][0])
        outer = max(range(len(poly)), key=lambda i: poly[i][0])
        n = len(poly)
        upper = [poly[(outer + k) % n] for k in range((inner - outer) % n + 1)][::-1]
        lower = [poly[(inner + k) % n] for k in range((outer - inner) % n + 1)]
        return upper, lower


def clip_inside(u, v, cu, cv, clip):
    """Pull (u, v) toward (cu, cv) until it lies inside the clip outline."""
    if clip is None or clip.metric(u, v) <= CLIP_MARGIN:
        return u, v
    lo, hi = 0.0, 1.0
    for _ in range(24):
        mid = (lo + hi) / 2.0
        if clip.metric(cu + (u - cu) * mid, cv + (v - cv) * mid) <= CLIP_MARGIN:
            lo = mid
        else:
            hi = mid
    return cu + (u - cu) * lo, cv + (v - cv) * lo


def disc(outline, clip=None):
    """Polar grid inside an outline: centre vertex, RINGS rings of SEGMENTS. Returns (uv list, faces).

    With a clip outline the rim is clipped first and the rings are spaced evenly up to it,
    so clipped parts keep clean, non-overlapping faces.
    """
    cu, cv = outline.cu, outline.cv
    rim = [clip_inside(*outline.point(2.0 * math.pi * seg / SEGMENTS), cu, cv, clip) for seg in range(SEGMENTS)]
    uvs = [(cu, cv)]
    for ring in range(1, RINGS + 1):
        f = ring / RINGS
        uvs.extend((cu + (u - cu) * f, cv + (v - cv) * f) for u, v in rim)
    faces = [(0, 1 + seg, 1 + (seg + 1) % SEGMENTS) for seg in range(SEGMENTS)]
    for ring in range(RINGS - 1):
        a, b = 1 + ring * SEGMENTS, 1 + (ring + 1) * SEGMENTS
        for seg in range(SEGMENTS):
            nxt = (seg + 1) % SEGMENTS
            faces.append((a + seg, b + seg, b + nxt, a + nxt))
    return uvs, faces


def resample(path, count):
    """Evenly spaced points along a 2D polyline."""
    lengths = [0.0]
    for (u0, v0), (u1, v1) in zip(path, path[1:]):
        lengths.append(lengths[-1] + math.hypot(u1 - u0, v1 - v0))
    total, out, j = lengths[-1], [], 0
    for i in range(count):
        target = total * i / (count - 1)
        while j < len(lengths) - 2 and lengths[j + 1] < target:
            j += 1
        span = lengths[j + 1] - lengths[j]
        t = 0.0 if span == 0.0 else (target - lengths[j]) / span
        (u0, v0), (u1, v1) = path[j], path[j + 1]
        out.append((u0 + (u1 - u0) * t, v0 + (v1 - v0) * t))
    return out


def side_normals(path):
    """Unit normals pointing to the left of the walking direction (away from the eye for the upper lid)."""
    normals = []
    for i in range(len(path)):
        (u0, v0), (u1, v1) = path[max(i - 1, 0)], path[min(i + 1, len(path) - 1)]
        du, dv = u1 - u0, v1 - v0
        length = math.hypot(du, dv) or 1.0
        normals.append((-dv / length, du / length))
    return normals


def smoothstep(edge0, edge1, x):
    t = min(1.0, max(0.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# Head
# ---------------------------------------------------------------------------

def find_head():
    blockout = bpy.data.collections.get(BLOCKOUT_COLLECTION)
    candidates = blockout.all_objects if blockout else bpy.data.objects
    for obj in candidates:
        if obj.type == "MESH" and obj.get(HEAD_PART[0]) == HEAD_PART[1]:
            return obj
    obj = bpy.data.objects.get(HEAD_OBJECT_NAME)
    if obj is None or obj.type != "MESH":
        raise RuntimeError(
            f"머리 메시({HEAD_OBJECT_NAME})를 찾을 수 없습니다. create_character_blockout.py를 먼저 실행하세요."
        )
    return obj


class Head:
    """World-space evaluated head mesh with a ray-cast helper for the face surface."""

    def __init__(self, obj):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        matrix = obj.matrix_world
        verts = [matrix @ v.co for v in mesh.vertices]
        polys = [tuple(p.vertices) for p in mesh.polygons]
        evaluated.to_mesh_clear()

        self.name = obj.name
        self.bvh = BVHTree.FromPolygons(verts, polys)
        self.lo = Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts)))
        self.hi = Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts)))
        self.width = self.hi.x - self.lo.x
        self.height = self.hi.z - self.lo.z
        self.centre_x = (self.lo.x + self.hi.x) / 2.0
        self.chin_z = self.lo.z

    def front_y(self, x, z):
        """Y of the first head surface seen from the front (-Y side), or None."""
        hit = self.bvh.ray_cast(Vector((x, self.lo.y - 1.0, z)), Vector((0.0, 1.0, 0.0)))[0]
        return None if hit is None else hit.y

    def surface_y(self, x, z):
        y = self.front_y(x, z)
        if y is None:
            raise RuntimeError("눈 위치에서 얼굴 앞면을 찾지 못했습니다. EYE_SPACING / EYE_CENTER_HEIGHT를 확인하세요.")
        return y


# ---------------------------------------------------------------------------
# Eye layout (left eye, +X). The right eye is mirrored from it.
# ---------------------------------------------------------------------------

class EyeLayout:
    def __init__(self, head):
        self.head = head
        self.cx = head.centre_x + head.height * EYE_SPACING / 2.0
        self.cz = head.chin_z + head.height * EYE_CENTER_HEIGHT
        width = head.height * EYE_WIDTH
        height = head.height * EYE_HEIGHT
        self.white = SplineOutline(EYE_SHAPE, width / 2.0, height / 2.0, EYE_TILT)

        iris_w, iris_h = width * IRIS_WIDTH, height * IRIS_HEIGHT
        iu, iv = -IRIS_OFFSET[0] * width, IRIS_OFFSET[1] * height
        self.iris = ellipse(iu, iv, iris_w / 2.0, iris_h / 2.0)
        self.pupil = ellipse(iu - PUPIL_OFFSET[0] * iris_w, iv + PUPIL_OFFSET[1] * iris_h,
                             iris_w * PUPIL_SIZE[0] / 2.0, iris_h * PUPIL_SIZE[1] / 2.0)
        self.highlights = [
            ellipse(iu - toward_nose * iris_w, iv + up * iris_h, iris_w * w / 2.0, iris_w * h / 2.0)
            for w, h, toward_nose, up in HIGHLIGHTS
        ]
        self.width, self.height = width, height
        self.iris_size = (iris_w, iris_h)

    def world(self, u, v, layer, lift=0.0):
        """3D point on the eye surface: face front (projected from the front view, as in Front.png),
        pushed forward by protrusion, bulge (inside the eye white), layer gap and an optional lift."""
        x, z = self.cx + u, self.cz + v
        bulge = EYE_BULGE * max(0.0, 1.0 - self.white.metric(u, v))
        return Vector((x, self.head.surface_y(x, z) - EYE_PROTRUSION - bulge - layer * LAYER_GAP - lift, z))


# ---------------------------------------------------------------------------
# Lids and lashes (2D layout, left eye)
# ---------------------------------------------------------------------------

def upper_lid_cut(layout):
    """Upper rim (inner -> outer corner) and the index where the lid line leaves it on the outer side."""
    upper, _ = layout.white.edges()
    top = max(range(len(upper)), key=lambda i: upper[i][1])
    end_v = UPPER_LID_END * layout.height / 2.0
    cut = next((i for i in range(top, len(upper)) if upper[i][1] < end_v), len(upper))
    return upper, max(cut, top + 2)


def upper_lid_line(layout):
    """Centre line of the upper lid (inner corner -> outer wing tip), its outward normals and thickness."""
    upper, cut = upper_lid_cut(layout)
    path = resample(upper[:cut], LID_SAMPLES)
    count = len(path)
    thickness = [UPPER_LID_THICKNESS * (UPPER_LID_INNER + (1.0 - UPPER_LID_INNER) * smoothstep(0.0, 0.45, i / (count - 1)))
                 for i in range(count)]

    wing_dir = rotate(1.0, 0.0, EYE_TILT + EYE_WING_ANGLE)
    end_u, end_v = path[-1]
    wing_steps = 6
    for k in range(1, wing_steps + 1):
        t = k / wing_steps
        path.append((end_u + wing_dir[0] * EYE_WING_LENGTH * t, end_v + wing_dir[1] * EYE_WING_LENGTH * t))
        thickness.append(UPPER_LID_THICKNESS * (1.0 - t) ** 1.3)
    return path, side_normals(path), thickness, count


def taper_strip(layout, centre, root_width, layer, lift=0.0, columns=2):
    """Flat strip along a 2D centre line, root_width wide at the start and pointed at the end."""
    steps = len(centre) - 1
    verts, faces = [], []
    for k, ((cu, cv), (su, sv)) in enumerate(zip(centre, side_normals(centre))):
        t = k / steps
        half = root_width / 2.0 * (1.0 - t) ** 0.9
        for j in range(columns + 1):
            offset = half * (2.0 * j / columns - 1.0)
            verts.append(layout.world(cu + su * offset, cv + sv * offset, layer, lift=lift * t * t))
    for k in range(steps):
        for j in range(columns):
            a, b = k * (columns + 1) + j, (k + 1) * (columns + 1) + j
            faces.append((a, b, b + 1, a + 1))
    return verts, faces


def append_mesh(verts, faces, part):
    base = len(verts)
    verts.extend(part[0])
    faces.extend(tuple(i + base for i in f) for f in part[1])


def inner_fork(layout, path, normals, thickness, count):
    """Short prong toward the nose where the lid line splits near the inner corner."""
    i = round(INNER_FORK_AT * (count - 1))
    (u, v), (nu, nv), w = path[i], normals[i], thickness[i]
    root = w * (0.5 - UPPER_LID_OVERLAP)
    du, dv = rotate(-1.0, 0.0, -INNER_FORK_ANGLE)
    start = (u + nu * root, v + nv * root)
    centre = [(start[0] + du * INNER_FORK_LENGTH * k / 6, start[1] + dv * INNER_FORK_LENGTH * k / 6) for k in range(7)]
    return taper_strip(layout, centre, w * 1.2, LID_LAYER + 0.5)


def lid_ribbon(layout):
    """Flat ribbon mesh for the upper lid that follows the eye white / face surface, plus the inner fork."""
    path, normals, thickness, count = upper_lid_line(layout)
    rows = 4
    verts = []
    for (u, v), (nu, nv), w in zip(path, normals, thickness):
        for j in range(rows + 1):
            offset = w * (j / rows - UPPER_LID_OVERLAP)
            verts.append(layout.world(u + nu * offset, v + nv * offset, LID_LAYER))
    faces = []
    for i in range(len(path) - 1):
        for j in range(rows):
            a, b = i * (rows + 1) + j, (i + 1) * (rows + 1) + j
            faces.append((a, b, b + 1, a + 1))
    append_mesh(verts, faces, inner_fork(layout, path, normals, thickness, count))
    return verts, faces


def lash_mesh(layout):
    """Flat tapered spikes rooted inside the top edge of the lid line, curling toward the outer corner."""
    path, normals, thickness, count = upper_lid_line(layout)
    verts, faces = [], []
    steps = 6
    for position, length, sweep in UPPER_LASHES:
        i = round(position * (count - 1))
        (u, v), (nu, nv), w = path[i], normals[i], thickness[i]
        root = w * (1.0 - UPPER_LID_OVERLAP) - LASH_WIDTH * 0.6
        centre = [(u + nu * root, v + nv * root)]
        for k in range(1, steps + 1):
            du, dv = rotate(nu, nv, -(sweep + LASH_BEND * k / steps))
            pu, pv = centre[-1]
            centre.append((pu + du * length / steps, pv + dv * length / steps))
        append_mesh(verts, faces, taper_strip(layout, centre, LASH_WIDTH, LID_LAYER + 1, lift=LASH_LIFT))
    return verts, faces


def crease_strand(layout):
    """Thin double-eyelid line that follows the lid line from above."""
    path, normals, thickness, count = upper_lid_line(layout)
    first, last = (round(f * (count - 1)) for f in CREASE_RANGE)
    points, radii = [], []
    for i in range(first, last + 1):
        t = (i - first) / (last - first)
        (u, v), (nu, nv), w = path[i], normals[i], thickness[i]
        offset = w * (1.0 - UPPER_LID_OVERLAP) + CREASE_GAP + CREASE_ARCH * math.sin(math.pi * t) + CREASE_RADIUS
        points.append(layout.world(u + nu * offset, v + nv * offset, LID_LAYER, lift=CREASE_RADIUS))
        radii.append(max(0.05, math.sin(math.pi * t) ** 0.5))
    return [(points, radii)]


def trim_length(path, length):
    """First `length` metres of a 2D polyline."""
    out, travelled = [path[0]], 0.0
    for (u0, v0), (u1, v1) in zip(path, path[1:]):
        step = math.hypot(u1 - u0, v1 - v0)
        if travelled + step >= length:
            t = (length - travelled) / step if step else 0.0
            out.append((u0 + (u1 - u0) * t, v0 + (v1 - v0) * t))
            return out
        out.append((u1, v1))
        travelled += step
    return out


def outer_line(layout):
    """Flat line from under the end of the upper lid down the outer side, tapering to a point."""
    _, lower = layout.white.edges()
    upper, cut = upper_lid_cut(layout)
    # End of the lid line -> outer corner -> down the outer side (clockwise, so the left normal points outward).
    path = resample(trim_length(upper[max(cut - 2, 0):] + lower[::-1][1:], OUTER_LINE_LENGTH), 24)
    rows = 2
    verts, faces = [], []
    for i, ((u, v), (nu, nv)) in enumerate(zip(path, side_normals(path))):
        w = OUTER_LINE_WIDTH * (1.0 - i / (len(path) - 1)) ** 1.1
        for j in range(rows + 1):
            offset = w * (j / rows - OUTER_LINE_OVERLAP)
            verts.append(layout.world(u + nu * offset, v + nv * offset, LID_LAYER + 0.5))
    for i in range(len(path) - 1):
        for j in range(rows):
            a, b = i * (rows + 1) + j, (i + 1) * (rows + 1) + j
            faces.append((a, b, b + 1, a + 1))
    return verts, faces


def lower_lid_strand(layout):
    """Faint thin line along the middle of the lower edge."""
    _, lower = layout.white.edges()
    lower = resample(lower, 48)
    first, last = (round(f * (len(lower) - 1)) for f in LOWER_LID_RANGE)
    path = lower[first:last + 1]
    normals = side_normals(path)  # walking inner -> outer along the bottom: left side points into the eye
    points, radii = [], []
    for i, ((u, v), (nu, nv)) in enumerate(zip(path, normals)):
        t = i / (len(path) - 1)
        offset = LOWER_LID_OFFSET + LOWER_LID_RADIUS
        points.append(layout.world(u - nu * offset, v - nv * offset, LID_LAYER, lift=LOWER_LID_RADIUS))
        radii.append(max(0.05, math.sin(math.pi * t) ** 0.6))
    return [(points, radii)]


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def hex_to_linear(value):
    def channel(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return tuple(channel(int(value[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


def rgba(value):
    return hex_to_linear(value) + (1.0,)


def find_socket(sockets, name, kind=None):
    for socket in sockets:
        if socket.name == name and (kind is None or socket.type == kind):
            return socket
    raise KeyError(name)


def new_material(name, color_hex, roughness, specular=0.5):
    """Material with a fresh Principled BSDF; returns (material, tree, bsdf)."""
    material = bpy.data.materials.get(MATERIAL_PREFIX + name) or bpy.data.materials.new(MATERIAL_PREFIX + name)
    material.diffuse_color = rgba(color_hex)
    material.roughness = roughness
    if material.node_tree is None and hasattr(material, "use_nodes"):
        material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    output.location, bsdf.location = (600, 0), (300, 0)
    tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = rgba(color_hex)
    bsdf.inputs["Roughness"].default_value = roughness
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    return material, tree, bsdf


def set_emission(tree, bsdf, color, strength):
    """color is an RGBA tuple or an output socket."""
    if "Emission Strength" not in bsdf.inputs or "Emission Color" not in bsdf.inputs:
        return
    bsdf.inputs["Emission Strength"].default_value = strength
    if isinstance(color, tuple):
        bsdf.inputs["Emission Color"].default_value = color
    else:
        tree.links.new(color, bsdf.inputs["Emission Color"])


def mix_node(tree, blend, factor, a, b):
    """ShaderNodeMix (colour). a / b / factor are sockets or constant values."""
    node = tree.nodes.new("ShaderNodeMix")
    node.data_type = "RGBA"
    node.blend_type = blend
    for socket, value in ((find_socket(node.inputs, "Factor", "VALUE"), factor),
                          (find_socket(node.inputs, "A", "RGBA"), a),
                          (find_socket(node.inputs, "B", "RGBA"), b)):
        if isinstance(value, (int, float, tuple)):
            socket.default_value = value
        else:
            tree.links.new(value, socket)
    return find_socket(node.outputs, "Result", "RGBA")


def map_range(tree, value, from_min, from_max, to_min=0.0, to_max=1.0):
    node = tree.nodes.new("ShaderNodeMapRange")
    node.data_type = "FLOAT"
    node.interpolation_type = "SMOOTHSTEP"
    tree.links.new(value, node.inputs[0])
    for index, number in zip((1, 2, 3, 4), (from_min, from_max, to_min, to_max)):
        node.inputs[index].default_value = number
    return node.outputs[0]


def color_ramp(tree, factor, stops):
    node = tree.nodes.new("ShaderNodeValToRGB")
    elements = node.color_ramp.elements
    while len(elements) > 1:
        elements.remove(elements[-1])
    elements[0].position, elements[0].color = stops[0]
    for position, color in stops[1:]:
        element = elements.new(position)
        element.color = color
    tree.links.new(factor, node.inputs["Fac"])
    return node.outputs["Color"]


def object_coords(tree, scale):
    """Object-space coordinates scaled so the part spans about -1..1; returns the Separate XYZ node."""
    coord = tree.nodes.new("ShaderNodeTexCoord")
    mapping = tree.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = scale
    tree.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    separate = tree.nodes.new("ShaderNodeSeparateXYZ")
    tree.links.new(mapping.outputs["Vector"], separate.inputs["Vector"])
    return separate


def white_material(layout):
    material, tree, bsdf = new_material("White", COLOR_WHITE, 0.4)
    xyz = object_coords(tree, (1.0, 1.0, 1.0))
    top = layout.height / 2.0
    shadow = map_range(tree, xyz.outputs["Z"], top * 0.2, top * 0.95)
    tree.links.new(mix_node(tree, "MIX", shadow, rgba(COLOR_WHITE), rgba(COLOR_WHITE_SHADOW)), bsdf.inputs["Base Color"])
    return material


def iris_material(layout):
    """3-colour vertical gradient, radial streaks, dark rim and a warm glow around the pupil."""
    material, tree, bsdf = new_material("Iris", COLOR_IRIS_MIDDLE, 0.6, specular=0.2)
    iris_w, iris_h = layout.iris_size
    xyz = object_coords(tree, (2.0 / iris_w, 1.0, 2.0 / iris_h))

    flat = tree.nodes.new("ShaderNodeCombineXYZ")
    tree.links.new(xyz.outputs["X"], flat.inputs["X"])
    tree.links.new(xyz.outputs["Z"], flat.inputs["Y"])
    radius = tree.nodes.new("ShaderNodeVectorMath")
    radius.operation = "LENGTH"
    tree.links.new(flat.outputs["Vector"], radius.inputs[0])
    direction = tree.nodes.new("ShaderNodeVectorMath")
    direction.operation = "NORMALIZE"
    tree.links.new(flat.outputs["Vector"], direction.inputs[0])

    # Noise sampled on (direction, radius): stretched along the radius -> radial streaks, no seam.
    dir_xyz = tree.nodes.new("ShaderNodeSeparateXYZ")
    tree.links.new(direction.outputs["Vector"], dir_xyz.inputs["Vector"])
    streak_vec = tree.nodes.new("ShaderNodeCombineXYZ")
    tree.links.new(dir_xyz.outputs["X"], streak_vec.inputs["X"])
    tree.links.new(dir_xyz.outputs["Y"], streak_vec.inputs["Y"])
    tree.links.new(radius.outputs["Value"], streak_vec.inputs["Z"])
    scaled = tree.nodes.new("ShaderNodeVectorMath")
    scaled.operation = "MULTIPLY"
    scaled.inputs[1].default_value = (IRIS_STREAK_SCALE, IRIS_STREAK_SCALE, 1.5)
    tree.links.new(streak_vec.outputs["Vector"], scaled.inputs[0])
    noise = tree.nodes.new("ShaderNodeTexNoise")
    if hasattr(noise, "noise_dimensions"):
        noise.noise_dimensions = "3D"
    noise.inputs["Scale"].default_value = 1.0
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.6
    tree.links.new(scaled.outputs["Vector"], noise.inputs["Vector"])
    streaks = color_ramp(tree, noise.outputs["Fac"], ((0.35, (0.0, 0.0, 0.0, 1.0)), (0.65, (1.0, 1.0, 1.0, 1.0))))

    vertical = map_range(tree, xyz.outputs["Z"], -1.0, 1.0)
    gradient = color_ramp(tree, vertical, (
        (0.06, rgba(COLOR_IRIS_BOTTOM)), (0.42, rgba(COLOR_IRIS_MIDDLE)), (0.72, rgba(COLOR_IRIS_TOP)),
    ))
    color = mix_node(tree, "OVERLAY", IRIS_STREAKS, gradient, streaks)
    glow = map_range(tree, radius.outputs["Value"], 0.25, 0.6, 0.25, 0.0)
    color = mix_node(tree, "SCREEN", glow, color, rgba(COLOR_IRIS_GLOW))
    rim = map_range(tree, radius.outputs["Value"], 0.78, 1.0, 0.0, 0.85)
    color = mix_node(tree, "MIX", rim, color, rgba(COLOR_IRIS_RIM))
    tree.links.new(color, bsdf.inputs["Base Color"])
    set_emission(tree, bsdf, color, 0.12)
    return material


def plain_material(name, color_hex, roughness, emission=0.0, specular=0.5):
    material, tree, bsdf = new_material(name, color_hex, roughness, specular)
    if emission > 0.0:
        set_emission(tree, bsdf, rgba(color_hex), emission)
    return material


# ---------------------------------------------------------------------------
# Scene helpers
# ---------------------------------------------------------------------------

def reset_collection(scene):
    collection = bpy.data.collections.get(COLLECTION_NAME)
    protected_collection = bpy.data.collections.get(PROTECTED_COLLECTION_NAME)
    protected = set(protected_collection.all_objects) if protected_collection else set()

    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
    else:
        for child in list(collection.children):
            collection.children.unlink(child)
        for obj in list(collection.objects):
            if obj in protected or len(obj.users_collection) > 1:
                collection.objects.unlink(obj)
                continue
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data is not None and data.users == 0:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Curve):
                    bpy.data.curves.remove(data)

    if collection not in scene.collection.children_recursive:
        scene.collection.children.link(collection)
    return collection


def add_empty(name, location, parent, collection, display="PLAIN_AXES", size=0.02):
    obj = bpy.data.objects.new(OBJECT_PREFIX + name, None)
    obj.empty_display_type = display
    obj.empty_display_size = size
    obj[PART_TAG] = name
    collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    return obj


def add_mesh(name, verts, faces, origin, parent, collection, material):
    mesh = bpy.data.meshes.new(OBJECT_PREFIX + name + "_Mesh")
    mesh.from_pydata([tuple(v - origin) for v in verts], [], faces)
    mesh.validate()
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(OBJECT_PREFIX + name, mesh)
    obj[PART_TAG] = name
    collection.objects.link(obj)
    obj.parent = parent
    return obj


def add_curve(name, strands, bevel, origin, parent, collection, material):
    """Curve object with one smooth spline per strand; point radius tapers the bevel."""
    curve = bpy.data.curves.new(OBJECT_PREFIX + name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = bevel
    curve.bevel_resolution = 3
    curve.resolution_u = 8
    curve.use_fill_caps = True
    for points, radii in strands:
        spline = curve.splines.new("NURBS")
        spline.points.add(len(points) - 1)
        for point, co, radius in zip(spline.points, points, radii):
            local = co - origin
            point.co = (local.x, local.y, local.z, 1.0)
            point.radius = radius
        spline.order_u = 3
        spline.use_endpoint_u = True
    curve.materials.append(material)
    obj = bpy.data.objects.new(OBJECT_PREFIX + name, curve)
    obj[PART_TAG] = name
    collection.objects.link(obj)
    obj.parent = parent
    return obj


def mirror(points):
    return [Vector((-p.x, p.y, p.z)) for p in points]


def flip(faces):
    # Keep the first vertex so quads split along the same diagonal as on the left eye.
    return [(f[0],) + tuple(reversed(f[1:])) for f in faces]


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_parts(layout):
    """World-space geometry for the left eye: meshes (verts, faces), curves (strands), iris gradient."""
    white_uv, white_faces = disc(layout.white)
    iris_uv, iris_faces = disc(layout.iris, clip=layout.white)
    pupil_uv, pupil_faces = disc(layout.pupil, clip=layout.white)

    highlight_verts, highlight_faces = [], []
    for outline in layout.highlights:
        uv, faces = disc(outline, clip=layout.white)
        base = len(highlight_verts)
        highlight_verts += [layout.world(u, v, 3) for u, v in uv]
        highlight_faces += [tuple(i + base for i in f) for f in faces]

    iris = layout.iris
    gradient = [min(1.0, max(0.0, (v - (iris.cv - iris.bottom)) / (iris.top + iris.bottom))) for _, v in iris_uv]
    meshes = {
        "White": ([layout.world(u, v, 0) for u, v in white_uv], white_faces),
        "Iris": ([layout.world(u, v, 1) for u, v in iris_uv], iris_faces),
        "Pupil": ([layout.world(u, v, 2) for u, v in pupil_uv], pupil_faces),
        "Highlight": (highlight_verts, highlight_faces),
        "UpperLid": lid_ribbon(layout),
        "UpperLashes": lash_mesh(layout),
        "OuterLine": outer_line(layout),
    }
    curves = {
        "UpperCrease": crease_strand(layout),
        "LowerLid": lower_lid_strand(layout),
    }
    return meshes, curves, gradient


def set_iris_gradient(obj, gradient):
    mesh = obj.data
    attribute = mesh.color_attributes.new(IRIS_GRADIENT_ATTRIBUTE, "FLOAT_COLOR", "POINT")
    bottom, middle, top = (hex_to_linear(c) for c in (COLOR_IRIS_BOTTOM, COLOR_IRIS_MIDDLE, COLOR_IRIS_TOP))
    for i, t in enumerate(gradient):
        a, b, f = (bottom, middle, smoothstep(0.0, 0.5, t)) if t < 0.5 else (middle, top, smoothstep(0.5, 0.9, t))
        attribute.data[i].color = tuple(x + (y - x) * f for x, y in zip(a, b)) + (1.0,)


def add_shrinkwrap(obj, target, layer):
    modifier = obj.modifiers.new("FollowEyeWhite", "SHRINKWRAP")
    modifier.target = target
    modifier.wrap_method = "NEAREST_SURFACEPOINT"
    modifier.wrap_mode = "ABOVE_SURFACE"
    modifier.offset = layer * LAYER_GAP


def build_eye(side, layout, meshes, curves, gradient, collection, materials):
    suffix = ".L" if side > 0 else ".R"

    def place(points):
        return points if side > 0 else mirror(points)

    def orient(faces):
        # Discs wind counter-clockwise seen from the front on the left eye; mirroring reverses that.
        return faces if side > 0 else flip(faces)

    def place_strands(strands):
        return [(place(points), radii) for points, radii in strands]

    centre = place([layout.world(0.0, 0.0, 0)])[0]
    gaze_point = place([layout.world(layout.iris.cu, layout.iris.cv, 0)])[0]

    # Empties and meshes keep identity rotation, so moving Eye_Gaze in local X / Z moves the gaze in world X / Z.
    root = add_empty("Root" + suffix, centre, None, collection, "PLAIN_AXES", 0.03)
    objects = {"Root": root}
    objects["White"] = add_mesh("White" + suffix, place(meshes["White"][0]), orient(meshes["White"][1]),
                                centre, root, collection, materials["White"])
    objects["UpperLid"] = add_mesh("UpperLid" + suffix, place(meshes["UpperLid"][0]), orient(meshes["UpperLid"][1]),
                                   centre, root, collection, materials["UpperLid"])
    objects["UpperLashes"] = add_mesh("UpperLashes" + suffix, place(meshes["UpperLashes"][0]),
                                      orient(meshes["UpperLashes"][1]), centre, objects["UpperLid"], collection,
                                      materials["Lash"])
    objects["UpperCrease"] = add_curve("UpperCrease" + suffix, place_strands(curves["UpperCrease"]), CREASE_RADIUS,
                                       centre, root, collection, materials["Crease"])
    objects["OuterLine"] = add_mesh("OuterLine" + suffix, place(meshes["OuterLine"][0]), orient(meshes["OuterLine"][1]),
                                    centre, root, collection, materials["OuterLine"])
    objects["LowerLid"] = add_curve("LowerLid" + suffix, place_strands(curves["LowerLid"]), LOWER_LID_RADIUS,
                                    centre, root, collection, materials["LowerLid"])

    gaze = add_empty("Gaze" + suffix, gaze_point - centre, root, collection, "PLAIN_AXES", 0.012)
    objects["Gaze"] = gaze
    for layer, name in enumerate(("Iris", "Pupil", "Highlight"), start=1):
        verts, faces = meshes[name]
        obj = add_mesh(name + suffix, place(verts), orient(faces), gaze_point, gaze, collection, materials[name])
        if name == "Iris":
            set_iris_gradient(obj, gradient)
        if GAZE_FOLLOWS_SURFACE:
            add_shrinkwrap(obj, objects["White"], layer)
        objects[name] = obj
    return objects


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

VISIBLE_PARTS = ("White", "Iris", "Pupil", "Highlight", "UpperLid", "UpperLashes", "UpperCrease", "OuterLine", "LowerLid")


def evaluated_points(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    evaluated.to_mesh_clear()
    return points


def report(head, layout, eyes):
    bpy.context.view_layer.update()
    problems = []

    behind = 0
    for side in (".L", ".R"):
        for name in VISIBLE_PARTS:
            for p in evaluated_points(eyes[side][name]):
                face_y = head.front_y(p.x, p.z)
                if face_y is not None and p.y > face_y:
                    behind += 1
    if behind:
        problems.append(f"얼굴 표면 안으로 들어간 정점 {behind}개")

    white_l = evaluated_points(eyes[".L"]["White"])
    gaps = [head.front_y(p.x, p.z) - p.y for p in white_l[1 + (RINGS - 1) * SEGMENTS:]]

    def mirror_error(evaluated):
        points = {}
        for side in (".L", ".R"):
            for name in VISIBLE_PARTS:
                obj = eyes[side][name]
                if evaluated or obj.type != "MESH":
                    pts = evaluated_points(obj)
                else:
                    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
                points.setdefault(side, []).extend(pts)
        tree = kdtree.KDTree(len(points[".R"]))
        for i, p in enumerate(points[".R"]):
            tree.insert(p, i)
        tree.balance()
        return max(tree.find(Vector((-p.x, p.y, p.z)))[2] for p in points[".L"])

    symmetry = mirror_error(False)
    # Shrinkwrap offsets follow the eye-white normals and differ by a fraction of LAYER_GAP between sides.
    symmetry_wrapped = mirror_error(True)
    if symmetry > 1e-5 or symmetry_wrapped > SYMMETRY_TOLERANCE:
        problems.append(f"좌우 비대칭 {max(symmetry, symmetry_wrapped):.6f} m")

    upper, _ = layout.white.edges()
    corner_lift = upper[-1][1] - upper[0][1]
    ok = not problems
    result = "결과: 정상" if ok else f"결과: 확인 필요 ({', '.join(problems)})"
    centre = eyes[".L"]["Root"].matrix_world.translation
    iris_w, iris_h = layout.iris_size
    lines = [
        f"머리 메시: {head.name} (너비 {head.width:.3f} m, 높이 {head.height:.3f} m, 턱 Z {head.chin_z:.3f})",
        f"눈 중심 (왼쪽 눈, +X): X {centre.x:+.3f}, Y {centre.y:+.3f}, Z {centre.z:.3f} m / 간격 {centre.x * 2.0:.3f} m",
        f"흰자 윤곽: 너비 {layout.width:.3f} x 높이 {layout.height:.3f} m, 눈꼬리가 눈머리보다 {corner_lift * 1000:.1f} mm 높음",
        f"홍채: {iris_w:.3f} x {iris_h:.3f} m (세로/가로 {iris_h / iris_w:.2f}), "
        f"동공: {layout.pupil.a * 2.0:.3f} x {layout.pupil.top * 2.0:.3f} m",
        "하이라이트: " + ", ".join(f"{h.a * 2.0:.3f} x {h.top * 2.0:.3f} m" for h in layout.highlights)
        + f" (흰자 위 {3 * LAYER_GAP * 1000:.1f} mm)",
        f"위 눈꺼풀: 최대 두께 {UPPER_LID_THICKNESS * 1000:.1f} mm, 눈꼬리 날개 {EYE_WING_LENGTH * 1000:.0f} mm / "
        f"속눈썹 {len(UPPER_LASHES)}개 ({min(l for _, l, _ in UPPER_LASHES) * 1000:.0f}~{max(l for _, l, _ in UPPER_LASHES) * 1000:.0f} mm, 뿌리 폭 {LASH_WIDTH * 1000:.1f} mm)",
        f"쌍꺼풀 선: 두께 {CREASE_RADIUS * 2000:.1f} mm, 구간 {CREASE_RANGE[0]:.2f}~{CREASE_RANGE[1]:.2f} / "
        f"바깥 옆라인: 시작 폭 {OUTER_LINE_WIDTH * 1000:.1f} mm, 길이 {OUTER_LINE_LENGTH * 1000:.0f} mm (끝으로 갈수록 가늘어짐) / "
        f"아래 눈꺼풀: 두께 {LOWER_LID_RADIUS * 2000:.1f} mm",
        f"안쪽 눈꺼풀 갈래: 길이 {INNER_FORK_LENGTH * 1000:.0f} mm",
        f"흰자 테두리와 얼굴 표면 간격: {min(gaps):.4f} ~ {max(gaps):.4f} m, 눈 중앙 돌출 {EYE_PROTRUSION + EYE_BULGE:.4f} m",
        f"좌우 대칭 최대 오차: 기본 형상 {symmetry:.6f} m, 시선용 래핑 적용 후 {symmetry_wrapped:.6f} m",
        f"오브젝트 {sum(len(e) for e in eyes.values())}개 ('{COLLECTION_NAME}' 컬렉션)",
        result,
    ]

    print("\n[MainGirlfriend 눈] 생성 결과")
    for line in lines:
        print("  " + line)

    if not bpy.app.background and bpy.context.window_manager is not None:
        def draw(self, _context):
            for line in lines:
                self.layout.label(text=line)

        bpy.context.window_manager.popup_menu(draw, title="MainGirlfriend 눈", icon="CHECKMARK" if ok else "ERROR")


def main():
    head = Head(find_head())
    layout = EyeLayout(head)
    collection = reset_collection(bpy.context.scene)
    materials = {
        "White": white_material(layout),
        "Iris": iris_material(layout),
        "Pupil": plain_material("Pupil", COLOR_PUPIL, 0.3),
        "Highlight": plain_material("Highlight", COLOR_HIGHLIGHT, 0.2, emission=2.0),
        "UpperLid": plain_material("UpperLid", COLOR_UPPER_LID, 0.9, specular=0.15),
        "Lash": plain_material("Lash", COLOR_LASH, 0.9, specular=0.15),
        "Crease": plain_material("Crease", COLOR_CREASE, 0.7),
        "OuterLine": plain_material("OuterLine", COLOR_OUTER_LINE, 0.9, specular=0.15),
        "LowerLid": plain_material("LowerLid", COLOR_LOWER_LID, 0.6),
    }
    meshes, curves, gradient = build_parts(layout)
    eyes = {
        ".L": build_eye(1, layout, meshes, curves, gradient, collection, materials),
        ".R": build_eye(-1, layout, meshes, curves, gradient, collection, materials),
    }
    report(head, layout, eyes)


if __name__ == "__main__":
    main()
