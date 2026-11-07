"""MainGirlfriend body blockout (proportion check only).

Run inside Blender 4.x / 5.x (Scripting workspace > Run Script).

- Builds head, neck, torso, pelvis, arms, hands, legs and feet as separate meshes
  from ring-based lofts plus a Subdivision Surface modifier.
- Character faces -Y, soles at Z = 0, centred on X = 0 / Y = 0. Left side (.L) is +X.
- Only the MainGirlfriend_Blockout collection is rebuilt on every run.
  Reference_Images and every other collection are left untouched.
- The .blend file is never saved by this script.

This is a proportion blockout, not final game topology. No face features, rig or clothing.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


# ===========================================================================
# Main proportions (metres)
# ===========================================================================

CHARACTER_HEIGHT = 1.65   # sole to head top including the hair volume on the crown
HEAD_HEIGHT = 0.55        # chin to CHARACTER_HEIGHT. Grows downward from the head top
CROWN_HAIR_SPACE = 0.015  # the bare skull top sits this far below CHARACTER_HEIGHT; the hair fills the gap later
HEAD_WIDTH = 0.42         # skull width at its widest (temples), front view. Hair volume is added later
HEAD_DEPTH = 0.48         # skull depth, side view; face front matches Side.png skin, skull stays inside the hair
SHOULDER_WIDTH = 0.28     # outer shoulder to outer shoulder
TORSO_LENGTH = 0.22       # waist to shoulder top
HIP_WIDTH = 0.342         # widest point of the hips
LEG_LENGTH = 0.64         # floor to crotch
ARM_LENGTH = 0.32         # shoulder joint to wrist


# ===========================================================================
# Secondary proportions, front view (measured from References/Front.png)
# ===========================================================================

PELVIS_HEIGHT = 0.21      # crotch to waist
WAIST_WIDTH = 0.19
CHEST_WIDTH = 0.23
NECK_RADIUS = 0.04        # neck radius just under the chin; the base is a few percent thinner
NECK_FLARE_HEIGHT = 0.035 # height of the lower neck ring above the shoulder line
TORSO_TOP_HALF_WIDTH = 0.072  # half width of the torso top ring around the neck base
NECK_HEAD_INSET = 0.09    # how far the neck reaches up inside the head
NECK_TOP_OFFSET_Y = -0.035 # neck top relative to the head centre (-Y = toward the chin); leans the neck forward
NECK_BACK_OFFSET = 0.028  # moves the whole neck toward the back of the head / upper back (+Y)

SHOULDER_JOINT_DROP = 0.055  # shoulder joint below the shoulder line; larger = the arm top sinks to the trapezius slope
ARM_ROOT_SCALE = 0.8      # size of the arm end hidden in the torso; smaller = no ball rising above the shoulder
ARM_ANGLE_DEG = 52.0      # A-pose: upper arm angle below horizontal (front view)
FOREARM_ANGLE_DEG = 55.0  # forearm angle below horizontal (front view)
ELBOW_BEND_DEG = 2.0      # forearm bends forward (-Y)
UPPER_ARM_RATIO = 0.55    # upper arm share of ARM_LENGTH
UPPER_ARM_RADIUS = 0.038
FOREARM_RADIUS = 0.031
WRIST_RADIUS = 0.026
HAND_LENGTH = 0.138
HAND_WIDTH = 0.075
HAND_THICKNESS = 0.032

LEG_SPACING = 0.08        # hip joint X
ANKLE_SPACING = 0.072     # ankle X
KNEE_HEIGHT = 0.43
ANKLE_HEIGHT = 0.08
THIGH_RADIUS = 0.1        # upper thigh half width (front view)
KNEE_RADIUS = 0.055
CALF_RADIUS = 0.06
ANKLE_RADIUS = 0.036

FOOT_LENGTH = 0.212       # bare foot, shorter than the boot in the sheet
FOOT_WIDTH = 0.092
FOOT_HEIGHT = 0.08
HEEL_BACK = 0.046         # heel extends this far behind the ankle (+Y)


# ===========================================================================
# Depth, side view. These cannot be derived reliably from the 2D sheet; tune by eye.
# ===========================================================================

CHEST_DEPTH = 0.18
BUST_FORWARD = 0.09       # extra chest depth on the front side only (bare body, blouse excluded)
BUST_CENTER = 0.47        # height of the fullest point, as a fraction of TORSO_LENGTH above the waist
BUST_SPACING = 0.062      # distance of each bust mound's centre from the body centre line (X)
BUST_RADIUS = 0.078       # outward radius of each mound (toward the arm)
BUST_INNER_RADIUS = 0.066 # inward radius of each mound; smaller = deeper cleavage, separately rounded undersides
BUST_TOP = 0.095          # mound radius above the fullest point; larger = longer, gentler upper slope
BUST_BOTTOM = 0.062       # mound radius below the fullest point; smaller = rounder, fuller underside
BUST_ROUNDNESS = 0.55     # mound profile exponent; lower = fuller, more spherical (0.5 = half ellipsoid)
BUST_SIDE = 0.4           # share of the mound that also bulges outward (front view fullness)
BUST_EDGE_SOFTNESS = 0.2  # how gradually the mound edge blends into the chest; 0 = sharp crease under the bust
UPPER_CHEST_FORWARD = ((0.64, 0.0), (0.8, 0.3), (0.91, 0.0))  # (t, share of BUST_FORWARD) for the upper-chest rings
WAIST_DEPTH = 0.15
HIP_DEPTH = 0.198
BUTT_BACK = 0.047         # extra hip depth on the back side only
LIMB_DEPTH_SCALE = 1.0    # front/back thickness of the arms relative to their width
THIGH_DEPTH = 0.22        # front-back thickness of the upper thigh (bare leg, socks excluded)
THIGH_FORWARD = -0.008    # front/back bias of the thigh volume; negative keeps the front of the upper thigh flat
THIGH_OUTWARD = 0.016     # upper thigh volume shifted outward (+X on .L) to keep the inner thighs apart
KNEE_DEPTH = 0.13
CALF_DEPTH = 0.155
CALF_BACK = 0.022         # calf bulge on the back of the shin
CALF_PEAK = 1.22          # fullest calf point on the leg path (1 = knee, 2 = ankle); lower = higher on the shin
ANKLE_DEPTH = 0.075
ARM_ROOT_OFFSET_Y = 0.04  # shoulder joint behind the body axis (+Y), as in Side.png
ARM_SWING_BACK_DEG = 6.0  # arms hang slightly backward in the side view
HEAD_OFFSET_Y = 0.025     # skull centre relative to the body axis (-Y = toward the face). Matched to aligned Side.png


# ===========================================================================
# Head shape (face outline only, no eyes / nose / mouth)
# ===========================================================================

HEAD_EQUATOR = 0.52           # widest point of the head, as a fraction of HEAD_HEIGHT above the chin
UPPER_HEAD_FULLNESS = 0.7     # <1 rounds out the skull above the widest point, 1 = plain sphere (egg-shaped top)
FOREHEAD_FULLNESS = 1.25      # same as UPPER_HEAD_FULLNESS but for the front of the crown; higher = forehead top recedes
LOWER_FACE_FULLNESS = 0.65    # <1 keeps the lower face (cheeks) wide, 1 = plain sphere
CHIN_ROUNDNESS = 0.9          # <1 flattens the chin bottom into a U shape, 1 = round/pointed
JAW_TAPER = 0.42              # 0 = no taper, higher = narrower chin
JAW_CURVE = 2.5               # higher keeps the cheeks wide and narrows only near the chin
CHIN_FORWARD = 0.10           # moves the chin toward the front (fraction of HEAD_DEPTH)
CHEEK_PUFF = 0.12             # soft cheek bulge
CHEEK_LEVEL = -0.45           # cheek centre height on the unit sphere (-1 chin .. 0 widest point)
CHEEK_SPREAD = 0.6            # cheek centre distance from the face centre line (0..1)
CHEEK_SIZE = 0.32             # cheek bulge radius on the unit sphere
FACE_FLATNESS = 0.10          # flattens the front of the face
BACK_OF_HEAD_FULLNESS = 0.06  # rounder back of the skull
# Front-view face outline below the eyes. Replaces the jaw formula above up to FACE_OUTLINE_TOP.
# Fitted to the concept face close-up (eye spacing 0.216 m as the scale), face width at height above chin:
# 0.207 m @ 3.2 cm, 0.25 m @ 5 cm, 0.29 m @ 8 cm, 0.31 m @ 12 cm, 0.335 m @ 15.5 cm.
FACE_OUTLINE_TOP = 0.19       # height above the chin (m) where the outline hands over to the skull
FACE_WIDTH_AT_TOP = 0.37     # face width (m) at FACE_OUTLINE_TOP (eye level)
JAW_ROUNDNESS = 2.2           # higher = fuller cheeks and a rounder jaw line
CHIN_TAPER = 0.35             # narrows only the tip of the chin (0 = fully round chin)
CHIN_TAPER_CURVE = 8.0        # higher keeps the taper closer to the chin tip
FACE_OUTLINE_BLEND = 0.035    # height range (m) below FACE_OUTLINE_TOP that blends into the skull
JAW_LIFT = 0.0                # the jaw rises at the sides toward the ears (fraction of HEAD_HEIGHT); chin stays lowest


# ===========================================================================
# Output
# ===========================================================================

COLLECTION_NAME = "MainGirlfriend_Blockout"
PROTECTED_COLLECTION_NAME = "Reference_Images"
OBJECT_PREFIX = "Blockout_"
MATERIAL_NAME = "MG_Skin_Blockout"
SKIN_COLOR = (1.0, 0.87, 0.80)  # sRGB

RING_SEGMENTS = 16
HEAD_SEGMENTS = 32
HEAD_RINGS = 24
SUBDIV_LEVELS = 2
SCULPT_DETAIL_LEVELS = 2  # subdivision levels baked into sculpted parts (bust) before sculpting; higher = smoother mounds

AUTO_FIT_HEIGHT = True    # rescale uniformly so the subdivided result is exactly CHARACTER_HEIGHT - CROWN_HAIR_SPACE
HEIGHT_TOLERANCE = 0.01


# ===========================================================================

X_AXIS = Vector((1.0, 0.0, 0.0))
FRONT = Vector((0.0, -1.0, 0.0))
UP = Vector((0.0, 0.0, 1.0))
PART_TAG = "mg_blockout_part"


def landmarks():
    crotch_z = LEG_LENGTH
    waist_z = crotch_z + PELVIS_HEIGHT
    shoulder_top_z = waist_z + TORSO_LENGTH
    chin_z = CHARACTER_HEIGHT - HEAD_HEIGHT
    return {
        "crotch": crotch_z,
        "waist": waist_z,
        "shoulder_top": shoulder_top_z,
        "chin": chin_z,
    }


# ---------------------------------------------------------------------------
# Ring loft helpers
# ---------------------------------------------------------------------------

def ring(center, u, v, ru, rv_pos, rv_neg=None):
    """Elliptical ring. v points to the side that uses rv_pos (front for torsos/limbs)."""
    return (Vector(center), u.normalized(), v.normalized(), ru, rv_pos, rv_pos if rv_neg is None else rv_neg)


def horizontal_ring(z, half_width, front, back=None, center_y=0.0):
    return ring((0.0, center_y, z), X_AXIS, FRONT, half_width, front, back)


def ring_points(spec, segments):
    center, u, v, ru, rv_pos, rv_neg = spec
    points = []
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments
        c, s = math.cos(angle), math.sin(angle)
        rv = rv_pos if s >= 0.0 else rv_neg
        points.append(center + u * (c * ru) + v * (s * rv))
    return points


def loft(rings, segments, cap_start=0.6, cap_end=0.6):
    """Connect rings with quads and close the ends with a rounded pole (None = open)."""
    verts, faces = [], []
    for spec in rings:
        verts.extend(ring_points(spec, segments))

    for r in range(len(rings) - 1):
        a, b = r * segments, (r + 1) * segments
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((a + i, a + j, b + j, b + i))

    def add_cap(index, neighbour, factor):
        center, _, _, ru, rv_pos, rv_neg = rings[index]
        direction = (center - rings[neighbour][0]).normalized()
        pole = center + direction * ((ru + rv_pos + rv_neg) / 3.0) * factor
        verts.append(pole)
        pole_index = len(verts) - 1
        base = index * segments
        for i in range(segments):
            faces.append((base + i, base + (i + 1) % segments, pole_index))

    if cap_start is not None:
        add_cap(0, 1, cap_start)
    if cap_end is not None:
        add_cap(len(rings) - 1, len(rings) - 2, cap_end)
    return verts, faces


def merge(*parts):
    verts, faces = [], []
    for part_verts, part_faces in parts:
        offset = len(verts)
        verts.extend(part_verts)
        faces.extend(tuple(i + offset for i in face) for face in part_faces)
    return verts, faces


def path_point(points, s):
    """Position along a polyline; s = segment index + fraction, extrapolates past both ends."""
    segment = min(max(int(math.floor(s)), 0), len(points) - 2)
    t = s - segment
    return points[segment].lerp(points[segment + 1], t)


def path_tangent(points, s, eps=0.08):
    return (path_point(points, s + eps) - path_point(points, s - eps)).normalized()


def limb_frame(tangent):
    """u lies in the XZ plane across the limb, v points to the front (-Y) side."""
    u = tangent.cross(FRONT)
    if u.length < 1e-6:
        u = tangent.cross(UP)
    u.normalize()
    v = u.cross(tangent).normalized()
    if v.dot(FRONT) < 0.0:
        v = -v
    return u, v


def limb_rings(points, profile):
    """profile: (s, half_width, front_depth, back_depth)."""
    rings = []
    for s, half_width, front, back in profile:
        u, v = limb_frame(path_tangent(points, s))
        rings.append(ring(path_point(points, s), u, v, half_width, front, back))
    return rings


def mirror_x(verts):
    return [Vector((-v.x, v.y, v.z)) for v in verts]


# ---------------------------------------------------------------------------
# Body parts. Each returns (verts, faces, pivot) in world space for the left (+X) side.
# ---------------------------------------------------------------------------

def head_shape(x, y, w):
    """Map a unit-sphere point (y < 0 is the face) to the head surface."""
    lower = max(0.0, -w)
    if w > 0.0:
        # Superellipse upper half: a round, full skull instead of an egg-shaped top.
        s = math.hypot(x, y)
        if s > 0.0:
            front_share = max(0.0, -y / s) ** 2
            k = s ** (UPPER_HEAD_FULLNESS + (FOREHEAD_FULLNESS - UPPER_HEAD_FULLNESS) * front_share) / s
            x, y = x * k, y * k
    if w < 0.0:
        # Superellipse lower half: wider cheeks and a flatter, U-shaped chin.
        s = math.hypot(x, y)
        if s > 0.0:
            k = s ** LOWER_FACE_FULLNESS / s
            x, y = x * k, y * k
        w = -(lower ** CHIN_ROUNDNESS)
    front = max(0.0, -y)

    px = x * HEAD_WIDTH / 2.0
    py = y * HEAD_DEPTH / 2.0
    pz = w * (HEAD_HEIGHT * (1.0 - HEAD_EQUATOR) - CROWN_HAIR_SPACE if w >= 0.0 else HEAD_HEIGHT * HEAD_EQUATOR)

    px *= 1.0 - JAW_TAPER * lower ** JAW_CURVE
    if y > 0.0:
        py *= 1.0 + BACK_OF_HEAD_FULLNESS * (1.0 - lower)
    py *= 1.0 - FACE_FLATNESS * front

    for side in (-1.0, 1.0):
        d2 = ((x - side * CHEEK_SPREAD) / CHEEK_SIZE) ** 2 + ((w - CHEEK_LEVEL) / CHEEK_SIZE) ** 2
        puff = CHEEK_PUFF * math.exp(-d2) * front
        px += puff * x * HEAD_WIDTH / 2.0
        py += puff * y * HEAD_DEPTH / 2.0

    py -= CHIN_FORWARD * HEAD_DEPTH * lower ** 2

    if lower > 0.0:
        px, pz = fit_face_outline(x, y, px, pz, lower)

    center_z = CHARACTER_HEIGHT - HEAD_HEIGHT * (1.0 - HEAD_EQUATOR)
    return Vector((px, HEAD_OFFSET_Y + py, center_z + pz))


def outline_width(h):
    """Front-view face width at height h above the chin: rounded jaw curve with a slightly narrower chin tip."""
    q = min(1.0, max(0.0, (FACE_OUTLINE_TOP - h) / FACE_OUTLINE_TOP))
    return FACE_WIDTH_AT_TOP * max(0.0, 1.0 - q ** JAW_ROUNDNESS) ** 0.5 * (1.0 - CHIN_TAPER * q ** CHIN_TAPER_CURVE)


def fit_face_outline(x, y, px, pz, lower):
    """Lower face: lift the sides of the jaw toward the ears, then give each height the FACE_OUTLINE width."""
    ring = math.hypot(x, y)
    if ring == 0.0:
        return px, pz
    # Sides only: the chin (front) stays lowest and the underside at the neck (back) keeps its height.
    sideness = 1.0 - abs(y / ring)
    pz += JAW_LIFT * HEAD_HEIGHT * lower ** 2 * sideness
    h = HEAD_HEIGHT * HEAD_EQUATOR + pz
    fitted = (x / ring) * outline_width(h) / 2.0
    blend = smoothstep(FACE_OUTLINE_TOP - FACE_OUTLINE_BLEND, FACE_OUTLINE_TOP, h)
    return fitted + (px - fitted) * blend, pz


def smoothstep(edge0, edge1, value):
    t = min(1.0, max(0.0, (value - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def build_head():
    verts = [head_shape(0.0, 0.0, 1.0)]
    faces = []
    for i in range(1, HEAD_RINGS):
        theta = math.pi * i / HEAD_RINGS
        s, w = math.sin(theta), math.cos(theta)
        for j in range(HEAD_SEGMENTS):
            phi = 2.0 * math.pi * j / HEAD_SEGMENTS
            verts.append(head_shape(s * math.sin(phi), -s * math.cos(phi), w))
    verts.append(head_shape(0.0, 0.0, -1.0))

    bottom = len(verts) - 1
    for j in range(HEAD_SEGMENTS):
        faces.append((0, 1 + (j + 1) % HEAD_SEGMENTS, 1 + j))
    for r in range(HEAD_RINGS - 2):
        a, b = 1 + r * HEAD_SEGMENTS, 1 + (r + 1) * HEAD_SEGMENTS
        for j in range(HEAD_SEGMENTS):
            k = (j + 1) % HEAD_SEGMENTS
            faces.append((a + j, a + k, b + k, b + j))
    last = 1 + (HEAD_RINGS - 2) * HEAD_SEGMENTS
    for j in range(HEAD_SEGMENTS):
        faces.append((last + j, last + (j + 1) % HEAD_SEGMENTS, bottom))

    pivot = Vector((0.0, HEAD_OFFSET_Y, landmarks()["chin"]))
    return verts, faces, pivot


def build_neck():
    lm = landmarks()
    shoulder_z, chin_z = lm["shoulder_top"], lm["chin"]
    base_z = shoulder_z - 0.05
    flare_top_z = min(shoulder_z + NECK_FLARE_HEIGHT, chin_z - 0.01)
    top_z = chin_z + NECK_HEAD_INSET
    r = NECK_RADIUS
    # The neck leans from NECK_BACK_OFFSET toward the head centre so it meets the head under the skull.
    top_y = HEAD_OFFSET_Y + NECK_TOP_OFFSET_Y
    # (z, radius, fraction of top_y): a slim, even neck that is very slightly thinner at the base.
    profile = [
        (base_z, r * 0.94, 0.0),
        (shoulder_z, r * 0.95, 0.15),
        (flare_top_z, r * 0.97, 0.4),
        ((flare_top_z + chin_z) / 2.0, r * 0.99, 0.6),
        (chin_z, r, 0.8),
        (top_z, r * 0.95, 1.0),
    ]
    rings = [
        horizontal_ring(z, radius, radius * 1.05, radius * 1.05, center_y=top_y * k + NECK_BACK_OFFSET)
        for z, radius, k in profile
    ]
    verts, faces = loft(rings, RING_SEGMENTS, 0.5, 0.5)
    return verts, faces, Vector((0.0, 0.0, base_z))


def build_torso():
    lm = landmarks()
    waist_z = lm["waist"]
    half_cd = CHEST_DEPTH / 2.0
    half_wd = WAIST_DEPTH / 2.0
    profile = [
        (-0.14, WAIST_WIDTH / 2.0 * 1.02, half_wd, half_wd),
        (0.0, WAIST_WIDTH / 2.0, half_wd, half_wd),
        (0.23, CHEST_WIDTH / 2.0 * 0.9, half_cd * 0.9, half_cd * 0.9),
        (0.31, CHEST_WIDTH / 2.0 * 0.94, half_cd * 0.94, half_cd * 0.94),
        (0.39, CHEST_WIDTH / 2.0 * 0.98, half_cd * 0.98, half_cd * 0.97),
        (0.47, CHEST_WIDTH / 2.0, half_cd, half_cd),
        (0.55, CHEST_WIDTH / 2.0 * 1.01, half_cd, half_cd),
        (0.64, CHEST_WIDTH / 2.0 * 1.02, half_cd, half_cd),
        (0.8, SHOULDER_WIDTH / 2.0 - 0.01, half_cd * 0.85, half_cd * 0.9),
        (0.91, SHOULDER_WIDTH / 2.0 * 0.8, half_cd * 0.65, half_cd * 0.7),
        (0.95, TORSO_TOP_HALF_WIDTH, half_cd * 0.4, half_cd * 0.45),
    ]
    # The top rings follow the neck backward so the neck flows into the upper back.
    neck_follow = {0.91: 0.3, 0.95: 0.7}
    rings = [
        horizontal_ring(waist_z + TORSO_LENGTH * t, hw, front + BUST_FORWARD * upper_chest(t), back,
                        center_y=NECK_BACK_OFFSET * neck_follow.get(t, 0.0))
        for t, hw, front, back in profile
    ]
    verts, faces = loft(rings, RING_SEGMENTS, 0.5, 0.3)
    return verts, faces, Vector((0.0, 0.0, waist_z))


def upper_chest(t):
    """Forward share of BUST_FORWARD carried by the whole upper-chest ring (keeps the shoulder/neck line)."""
    for (t0, a), (t1, b) in zip(UPPER_CHEST_FORWARD, UPPER_CHEST_FORWARD[1:]):
        if t0 <= t <= t1:
            return a + (b - a) * (t - t0) / (t1 - t0)
    return 0.0


def sculpt_bust(v):
    """Two full, rounded bust mounds: a long gentle upper slope and a round underside."""
    if v.y >= 0.0:
        return
    waist_z = landmarks()["waist"]
    bust_z = waist_z + TORSO_LENGTH * BUST_CENTER
    dx = (abs(v.x) - BUST_SPACING) / (BUST_RADIUS if abs(v.x) > BUST_SPACING else BUST_INNER_RADIUS)
    dz = (v.z - bust_z) / (BUST_TOP if v.z > bust_z else BUST_BOTTOM)
    d2 = dx * dx + dz * dz
    if d2 >= 1.0:
        return
    # Only add what the upper-chest ring has not already pushed forward.
    edge = smoothstep(0.0, BUST_EDGE_SOFTNESS, 1.0 - d2) if BUST_EDGE_SOFTNESS > 0.0 else 1.0
    mound = (1.0 - d2) ** BUST_ROUNDNESS * edge - upper_chest((v.z - waist_z) / TORSO_LENGTH)
    # Fade out toward the flanks so the mound never steps at the side of the torso.
    facing = smoothstep(0.0, 0.45, -v.y / math.hypot(v.x, v.y))
    push = BUST_FORWARD * max(0.0, mound) * facing
    v.y -= push
    v.x += math.copysign(push * BUST_SIDE * min(1.0, max(0.0, dx)), v.x)


def build_pelvis():
    lm = landmarks()
    crotch_z, waist_z = lm["crotch"], lm["waist"]
    half_hw = HIP_WIDTH / 2.0
    half_hd = HIP_DEPTH / 2.0
    half_wd = WAIST_DEPTH / 2.0
    # The t=0.84 ring eases the waist into the hips so the side and front curves stay smooth.
    profile = [
        (1.18, WAIST_WIDTH / 2.0 * 0.95, half_wd, half_wd),
        (1.0, WAIST_WIDTH / 2.0, half_wd, half_wd),
        (0.84, (WAIST_WIDTH / 2.0 + half_hw * 0.92) / 2.0 * 1.03, (half_wd + half_hd) / 2.0,
         (half_wd + half_hd) / 2.0 + BUTT_BACK * 0.3),
        (0.67, half_hw * 0.92, half_hd, half_hd + BUTT_BACK * 0.6),
        (0.38, half_hw, half_hd, half_hd + BUTT_BACK),
        # Lower rings stay wide enough to cover the top of the thick thighs (no ledge at the hip joint).
        (0.14, half_hw * 0.97, half_hd * 0.9, half_hd + BUTT_BACK * 0.8),
        (-0.05, half_hw * 0.68, half_hd * 0.55, half_hd * 0.6),
    ]
    rings = [
        horizontal_ring(crotch_z + PELVIS_HEIGHT * t, hw, front, back)
        for t, hw, front, back in profile
    ]
    verts, faces = loft(rings, RING_SEGMENTS, 0.3, 0.5)
    return verts, faces, Vector((0.0, 0.0, crotch_z + PELVIS_HEIGHT * 0.38))


def arm_joints():
    lm = landmarks()
    shoulder = Vector((SHOULDER_WIDTH / 2.0 - UPPER_ARM_RADIUS, ARM_ROOT_OFFSET_Y, lm["shoulder_top"] - SHOULDER_JOINT_DROP))
    swing = math.tan(math.radians(ARM_SWING_BACK_DEG))

    def hanging(angle_deg):
        # A-pose angle in the front view, tilted backward (+Y) by the swing angle in the side view.
        a = math.radians(angle_deg)
        return Vector((math.cos(a), math.sin(a) * swing, -math.sin(a))).normalized()

    upper_dir = hanging(ARM_ANGLE_DEG)
    b = math.radians(ELBOW_BEND_DEG)
    fore_dir = (hanging(FOREARM_ANGLE_DEG) * math.cos(b) + FRONT * math.sin(b)).normalized()
    elbow = shoulder + upper_dir * ARM_LENGTH * UPPER_ARM_RATIO
    wrist = elbow + fore_dir * ARM_LENGTH * (1.0 - UPPER_ARM_RATIO)
    return shoulder, elbow, wrist, fore_dir


def build_arm():
    shoulder, elbow, wrist, _ = arm_joints()
    d = LIMB_DEPTH_SCALE
    profile = [
        (-0.15, UPPER_ARM_RADIUS * ARM_ROOT_SCALE),
        (0.0, UPPER_ARM_RADIUS * 1.1),
        (0.4, UPPER_ARM_RADIUS),
        (0.85, UPPER_ARM_RADIUS * 0.85),
        (1.0, FOREARM_RADIUS * 0.95),
        (1.2, FOREARM_RADIUS),
        (1.6, (FOREARM_RADIUS + WRIST_RADIUS) / 2.0),
        (2.0, WRIST_RADIUS),
        (2.06, WRIST_RADIUS * 0.95),
    ]
    rings = limb_rings([shoulder, elbow, wrist], [(s, r, r * d, r * d) for s, r in profile])
    verts, faces = loft(rings, RING_SEGMENTS, 0.8, 0.5)
    return verts, faces, shoulder


def build_hand():
    _, _, wrist, direction = arm_joints()
    tip = wrist + direction * HAND_LENGTH
    half_t, half_w = HAND_THICKNESS / 2.0, HAND_WIDTH / 2.0
    # Starts at the forearm's wrist thickness (inside the arm) so the wrist has no lip, then flares to the palm.
    wrist_t, wrist_w = WRIST_RADIUS * 0.93, WRIST_RADIUS * 0.97
    profile = [
        (-0.15, WRIST_RADIUS * 0.9, WRIST_RADIUS * 0.9),
        (0.0, wrist_t, wrist_w),
        (0.12, (wrist_t + half_t) / 2.0, (wrist_w + half_w * 0.92) / 2.0),
        (0.25, half_t, half_w * 0.92),
        (0.45, half_t * 0.95, half_w),
        (0.6, half_t * 0.85, half_w * 0.98),
        (0.8, half_t * 0.7, half_w * 0.9),
        (0.95, half_t * 0.5, half_w * 0.7),
    ]
    rings = limb_rings([wrist, tip], [(s, t, w, w) for s, t, w in profile])
    palm = loft(rings, RING_SEGMENTS, 0.5, 0.5)

    u, v = limb_frame(direction)
    thumb = HAND_LENGTH / 0.12  # thumb was sized for a 0.12 m hand
    thumb_base = wrist + direction * (HAND_LENGTH * 0.25) + v * (half_w * 0.7)
    thumb_tip = thumb_base + (direction * 0.6 + v * 0.55 - u * 0.2).normalized() * 0.045 * thumb
    thumb_rings = limb_rings(
        [thumb_base, thumb_tip],
        [(s, r * thumb, r * thumb, r * thumb) for s, r in ((0.0, 0.012), (0.5, 0.011), (1.0, 0.008))],
    )
    thumb = loft(thumb_rings, 8, 0.6, 0.8)

    verts, faces = merge(palm, thumb)
    return verts, faces, wrist


def leg_joints():
    hip = Vector((LEG_SPACING, 0.0, LEG_LENGTH + 0.06))
    knee = Vector(((LEG_SPACING + ANKLE_SPACING) / 2.0, -0.005, KNEE_HEIGHT))
    ankle = Vector((ANKLE_SPACING, 0.0, ANKLE_HEIGHT))
    return hip, knee, ankle


def build_leg():
    hip, knee, ankle = leg_joints()
    thigh, knee_d, calf, ankle_d = THIGH_DEPTH / 2.0, KNEE_DEPTH / 2.0, CALF_DEPTH / 2.0, ANKLE_DEPTH / 2.0
    # (s, half width in the front view, half depth in the side view, shift toward the front)
    # Thigh tapers evenly to the knee; the calf peaks at CALF_PEAK (upper shin)
    # and eases into the ankle without a second bulge.
    profile = [
        (-0.2, THIGH_RADIUS * 0.85, thigh * 0.85, 0.0),
        (0.0, THIGH_RADIUS, thigh, THIGH_FORWARD),
        (0.3, THIGH_RADIUS * 0.97, thigh * 0.97, THIGH_FORWARD),
        (0.65, THIGH_RADIUS * 0.72, thigh * 0.72, THIGH_FORWARD * 0.5),
        (0.87, KNEE_RADIUS * 1.08, knee_d * 1.08, 0.0),
        (1.0, KNEE_RADIUS, knee_d, 0.0),
        (CALF_PEAK - 0.12, KNEE_RADIUS * 1.06, (knee_d + calf) / 2.0, -CALF_BACK * 0.5),
        (CALF_PEAK, CALF_RADIUS, calf, -CALF_BACK),
        (CALF_PEAK + 0.23, (CALF_RADIUS + ANKLE_RADIUS) / 2.0 * 1.08, (calf + ankle_d) / 2.0 * 1.06, -CALF_BACK * 0.5),
        (1.72, ANKLE_RADIUS * 1.12, ankle_d * 1.12, -CALF_BACK * 0.12),
        (1.9, ANKLE_RADIUS, ankle_d, 0.0),
        (2.0, ANKLE_RADIUS * 0.98, ankle_d * 0.98, 0.0),
        (2.12, ANKLE_RADIUS * 0.9, ankle_d * 0.9, 0.0),
    ]
    rings = limb_rings(
        [hip, knee, ankle],
        [(s, r, depth + shift, depth - shift) for s, r, depth, shift in profile],
    )
    # Push the thick upper thigh outward so the inner thighs meet without intersecting; joints stay put.
    outward = [1.0, 1.0, 1.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    rings = [
        (center + X_AXIS * (THIGH_OUTWARD * k), u, v, ru, rv_pos, rv_neg)
        for (center, u, v, ru, rv_pos, rv_neg), k in zip(rings, outward)
    ]
    verts, faces = loft(rings, RING_SEGMENTS, 0.5, 0.5)
    return verts, faces, hip


def build_foot():
    _, _, ankle = leg_joints()
    half_w, h = FOOT_WIDTH / 2.0, FOOT_HEIGHT
    # (fraction heel->toe, half width, centre height, half height). The instep slopes gently
    # from the ankle (f 0.15-0.35) down to the ball of the foot.
    # The heel/ankle rings stay close to ANKLE_RADIUS so the leg enters the foot without a collar.
    ankle_w = min(half_w * 0.85, ANKLE_RADIUS * 1.08)
    profile = [
        (0.02, half_w * 0.72, h * 0.42, h * 0.42),
        (0.12, ankle_w, h * 0.5, h * 0.5),
        (0.28, ankle_w * 1.04, h * 0.55, h * 0.55),
        (0.45, half_w * 0.95, h * 0.5, h * 0.48),
        (0.62, half_w, h * 0.4, h * 0.38),
        (0.78, half_w, h * 0.3, h * 0.28),
        (0.91, half_w * 0.85, h * 0.22, h * 0.21),
        (0.98, half_w * 0.6, h * 0.16, h * 0.15),
    ]
    rings = [
        ring((ankle.x, ankle.y + HEEL_BACK - f * FOOT_LENGTH, zc), X_AXIS, UP, hw, hh)
        for f, hw, zc, hh in profile
    ]
    verts, faces = loft(rings, RING_SEGMENTS, 0.5, 0.6)
    verts = [Vector((v.x, v.y, max(v.z, 0.0))) for v in verts]
    return verts, faces, ankle


# ---------------------------------------------------------------------------
# Scene helpers
# ---------------------------------------------------------------------------

def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def ensure_material():
    material = bpy.data.materials.get(MATERIAL_NAME) or bpy.data.materials.new(MATERIAL_NAME)
    color = tuple(srgb_to_linear(c) for c in SKIN_COLOR) + (1.0,)
    material.diffuse_color = color
    material.roughness = 0.6
    if material.node_tree is None and hasattr(material, "use_nodes"):
        material.use_nodes = True
    if material.node_tree is not None:
        for node in material.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                node.inputs["Base Color"].default_value = color
                node.inputs["Roughness"].default_value = 0.6
    return material


def reset_collection(scene):
    collection = bpy.data.collections.get(COLLECTION_NAME)
    protected_collection = bpy.data.collections.get(PROTECTED_COLLECTION_NAME)
    protected = set(protected_collection.all_objects) if protected_collection else set()

    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
    else:
        for obj in list(collection.objects):
            if obj in protected or len(obj.users_collection) > 1:
                collection.objects.unlink(obj)
                continue
            mesh = obj.data if obj.type == "MESH" else None
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh is not None and mesh.users == 0:
                bpy.data.meshes.remove(mesh)

    if collection not in scene.collection.children_recursive:
        scene.collection.children.link(collection)
    return collection


def create_part(name, verts, faces, pivot, collection, material, sculpt=None):
    full_name = OBJECT_PREFIX + name
    mesh = bpy.data.meshes.new(full_name + "_Mesh")
    mesh.from_pydata([tuple(v - pivot) for v in verts], [], faces)
    mesh.validate()

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()

    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.materials.append(material)
    mesh.update()

    obj = bpy.data.objects.new(full_name, mesh)
    obj.location = pivot
    obj[PART_TAG] = name
    collection.objects.link(obj)

    modifier = obj.modifiers.new("Subdivision", "SUBSURF")
    modifier.levels = SUBDIV_LEVELS
    modifier.render_levels = SUBDIV_LEVELS
    if sculpt is not None:
        presubdivide(obj, modifier, sculpt)
    return obj


def presubdivide(obj, modifier, sculpt):
    """Bake SCULPT_DETAIL_LEVELS subdivision levels into the cage, then sculpt the denser cage.

    Without the limit-surface projection the baked cage has the same limit surface,
    so un-sculpted areas keep the shape of the plain SUBDIV_LEVELS result.
    """
    modifier.levels = SCULPT_DETAIL_LEVELS
    modifier.use_limit_surface = False
    bpy.context.view_layer.update()
    old_mesh = obj.data
    baked = bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    baked.name = old_mesh.name
    obj.data = baked
    bpy.data.meshes.remove(old_mesh)
    modifier.levels = max(1, SUBDIV_LEVELS - SCULPT_DETAIL_LEVELS)
    modifier.render_levels = modifier.levels
    modifier.use_limit_surface = True
    pivot = obj.location
    for vert in baked.vertices:
        world = vert.co + pivot
        sculpt(world)
        vert.co = world - pivot
    baked.update()


def evaluated_bounds(objects):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for obj in objects:
        # bound_box can lag behind modifiers, so measure the subdivided vertices directly.
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        matrix = evaluated.matrix_world
        for vertex in mesh.vertices:
            p = matrix @ vertex.co
            lo = Vector(map(min, lo, p))
            hi = Vector(map(max, hi, p))
        evaluated.to_mesh_clear()
    return lo, hi


def bare_height():
    return CHARACTER_HEIGHT - CROWN_HAIR_SPACE


def fit_height(objects):
    lo, hi = evaluated_bounds(objects)
    scale = bare_height() / (hi.z - lo.z)
    for obj in objects:
        obj.data.transform(Matrix.Scale(scale, 4))
        obj.location = (obj.location - Vector((0.0, 0.0, lo.z))) * scale
    return scale


def world_mesh(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    matrix = evaluated.matrix_world
    verts = [matrix @ v.co for v in mesh.vertices]
    polygons = [tuple(p.vertices) for p in mesh.polygons]
    evaluated.to_mesh_clear()
    return verts, polygons


def tagged_parts(objects):
    return {obj[PART_TAG]: obj for obj in objects if PART_TAG in obj}


def head_metrics(parts):
    """Head size, exposed neck length and head/shoulder clearance of a blockout."""
    head = parts.get("Head")
    if head is None:
        return None

    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    head_verts, head_polys = world_mesh(head, depsgraph)
    chin_z = min(v.z for v in head_verts)
    head_ys = [v.y for v in head_verts]
    metrics = {
        "head_height": max(v.z for v in head_verts) - chin_z,
        "head_width": max(v.x for v in head_verts) - min(v.x for v in head_verts),
        "head_depth": max(head_ys) - min(head_ys),
        "head_centre_y": (max(head_ys) + min(head_ys)) / 2.0,
        "face_front_y": min(head_ys),
        "head_back_y": max(head_ys),
        "chin_z": chin_z,
    }
    head_bvh = BVHTree.FromPolygons(head_verts, head_polys)

    neck, torso = parts.get("Neck"), parts.get("Torso")
    if neck is not None and torso is not None:
        neck_verts, _ = world_mesh(neck, depsgraph)
        torso_bvh = BVHTree.FromPolygons(*world_mesh(torso, depsgraph))
        ring = [v for v in neck_verts if abs(v.z - (chin_z - 0.015)) < 0.01] or neck_verts
        cx = sum(v.x for v in ring) / len(ring)
        cy = sum(v.y for v in ring) / len(ring)
        metrics["neck_centre_y"] = cy
        metrics["neck_top_z"] = max(v.z for v in neck_verts)
        lines = {
            "front": (cx, cy - (cy - min(v.y for v in ring)) * 0.95),
            "side": (cx + (max(v.x for v in ring) - cx) * 0.95, cy),
            "back": (cx, cy + (max(v.y for v in ring) - cy) * 0.95),
        }
        exposed = {}
        # Vertical distance between the torso surface and the head underside along the neck surface.
        for name, (x, y) in lines.items():
            head_hit = head_bvh.ray_cast(Vector((x, y, 0.0)), UP)[0]
            torso_hit = torso_bvh.ray_cast(Vector((x, y, CHARACTER_HEIGHT + 1.0)), -UP)[0]
            if head_hit is not None and torso_hit is not None:
                exposed[name] = max(0.0, head_hit.z - torso_hit.z)
        if exposed:
            metrics["neck_exposed"] = sum(exposed.values()) / len(exposed)
            metrics["neck_exposed_lines"] = exposed

    shoulder_parts = [parts[name] for name in ("Torso", "Arm.L", "Arm.R") if name in parts]
    if shoulder_parts:
        clearance = math.inf
        overlap = False
        for part in shoulder_parts:
            part_bvh = BVHTree.FromPolygons(*world_mesh(part, depsgraph))
            overlap = overlap or bool(head_bvh.overlap(part_bvh))
            for v in head_verts:
                hit = part_bvh.find_nearest(v)
                if hit[0] is not None:
                    clearance = min(clearance, hit[3])
        metrics["shoulder_clearance"] = clearance
        metrics["shoulder_overlap"] = overlap

    metrics.update(body_metrics(parts, depsgraph))
    return metrics


# Pairs that should not touch (joints such as arm/torso or leg/foot overlap on purpose).
SEPARATE_PAIRS = (
    ("Leg.L", "Leg.R"),
    ("Hand.L", "Pelvis"),
    ("Hand.L", "Leg.L"),
    ("Hand.L", "Torso"),
    ("Arm.L", "Pelvis"),
    ("Foot.L", "Foot.R"),
)


def body_metrics(parts, depsgraph):
    meshes = {name: world_mesh(obj, depsgraph) for name, obj in parts.items()}
    m = {}

    def extent(verts, axis):
        values = [v[axis] for v in verts]
        return max(values) - min(values)

    def band(verts, z, half=0.01):
        return [v for v in verts if abs(v.z - z) < half]

    if "Torso" in meshes:
        verts = meshes["Torso"][0]
        lm = landmarks()
        bust = [v for v in verts if lm["waist"] + TORSO_LENGTH * 0.35 < v.z < lm["waist"] + TORSO_LENGTH * 0.6]
        if bust:
            m["chest_front"] = -min(v.y for v in bust)
            m["chest_width"] = extent(bust, 0)

    if "Pelvis" in meshes:
        verts, polygons = meshes["Pelvis"]
        m["hip_width"] = extent(verts, 0)
        m["hip_depth"] = extent(verts, 1)
        m["hip_back"] = max(v.y for v in verts)
        bm = bmesh.new()
        for v in verts:
            bm.verts.new(v)
        bm.verts.ensure_lookup_table()
        for poly in polygons:
            bm.faces.new([bm.verts[i] for i in poly])
        m["hip_volume"] = abs(bm.calc_volume())
        bm.free()

    if "Leg.L" in meshes:
        verts = meshes["Leg.L"][0]
        thigh = band(verts, LEG_LENGTH - 0.03)
        if thigh:
            m["thigh_width"] = extent(thigh, 0)
            m["thigh_depth"] = extent(thigh, 1)
        def full_slice(z):
            # Thick enough to always contain complete vertex rings of the subdivided leg.
            slice_ = band(verts, z, 0.012)
            return slice_ if len(slice_) >= 40 else None

        # Knee = narrowest front-back slice within 7 cm of KNEE_HEIGHT.
        knee = (math.inf, None)
        z = KNEE_HEIGHT - 0.07
        while z < KNEE_HEIGHT + 0.07:
            slice_ = full_slice(z)
            if slice_ and extent(slice_, 1) < knee[0]:
                knee = (extent(slice_, 1), z)
            z += 0.005
        m["knee_z"] = knee[1]

        best = (0.0, None)
        z = ANKLE_HEIGHT + 0.04
        while z < (knee[1] or KNEE_HEIGHT):
            slice_ = full_slice(z)
            if slice_ and extent(slice_, 1) > best[0]:
                best = (extent(slice_, 1), z)
            z += 0.005
        m["calf_max_depth"], m["calf_max_z"] = best
        calf = full_slice(best[1] or 0.3)
        m["calf_back"] = max(v.y for v in calf) if calf else None

    if "Hand.L" in meshes:
        verts = meshes["Hand.L"][0]
        wrist = parts["Hand.L"].matrix_world.translation
        m["hand_length"] = max((v - wrist).length for v in verts)
        m["hand_width"] = extent(verts, 1)

    if "Foot.L" in meshes:
        verts = meshes["Foot.L"][0]
        m["foot_length"] = extent(verts, 1)
        m["foot_width"] = extent(verts, 0)
        m["foot_bottom_z"] = min(v.z for v in verts)

    overlaps = {}
    for a, b in SEPARATE_PAIRS:
        if a in meshes and b in meshes:
            overlaps[f"{a}/{b}"] = len(bvh_of(meshes[a]).overlap(bvh_of(meshes[b])))
    m["overlaps"] = overlaps
    return m


def bvh_of(mesh):
    verts, polygons = mesh
    return BVHTree.FromPolygons(verts, polygons)


NECK_LINE_NAMES = {"front": "앞", "side": "옆", "back": "뒤"}

# (label, metrics key, value format, show % change)
HEAD_METRICS = (
    ("머리 높이", "head_height", "{:.3f} m", False),
    ("머리 너비", "head_width", "{:.3f} m", False),
    (f"머리 깊이 (HEAD_DEPTH {HEAD_DEPTH})", "head_depth", "{:.3f} m", False),
    ("머리 중심 Y", "head_centre_y", "{:+.3f} m", False),
    ("얼굴 앞 Y", "face_front_y", "{:+.3f} m", False),
    ("뒤통수 Y", "head_back_y", "{:+.3f} m", False),
    ("턱 Z", "chin_z", "{:.3f} m", False),
    ("턱 아래 목 중심 Y", "neck_centre_y", "{:+.3f} m", False),
    ("목 위쪽 끝 Z", "neck_top_z", "{:.3f} m", False),
    ("목 노출 길이", "neck_exposed", "{:.3f} m", True),
)
BODY_METRICS = (
    ("가슴 앞쪽 돌출 (몸 중심 기준)", "chest_front", "{:.3f} m", True),
    ("가슴 너비", "chest_width", "{:.3f} m", True),
    ("힙 너비", "hip_width", "{:.3f} m", True),
    ("힙 깊이", "hip_depth", "{:.3f} m", True),
    ("힙 뒤쪽 돌출 (몸 중심 기준)", "hip_back", "{:.3f} m", True),
    ("힙 볼륨 (m³)", "hip_volume", "{:.5f}", True),
    ("허벅지 상단 너비", "thigh_width", "{:.3f} m", True),
    ("허벅지 상단 앞뒤 두께", "thigh_depth", "{:.3f} m", True),
    ("무릎 (가장 가는 지점) Z", "knee_z", "{:.3f} m", False),
    ("종아리 최대 앞뒤 두께", "calf_max_depth", "{:.3f} m", True),
    ("종아리 최대 두께 위치 Z", "calf_max_z", "{:.3f} m", False),
    ("종아리 뒤쪽 돌출 (몸 중심 기준)", "calf_back", "{:+.3f} m", False),
    ("손 길이 (손목→손끝)", "hand_length", "{:.3f} m", True),
    ("손 너비 (엄지 포함)", "hand_width", "{:.3f} m", True),
    ("발 길이", "foot_length", "{:.3f} m", True),
    ("발 너비", "foot_width", "{:.3f} m", True),
    ("발바닥 Z", "foot_bottom_z", "{:.3f} m", False),
)


def metric_lines(before, after, specs):
    def value(metrics, key, form):
        if metrics is None or metrics.get(key) is None:
            return "-"
        return form.format(metrics[key])

    lines = []
    for label, key, form, show_change in specs:
        text = f"{label}: {value(before, key, form)} -> {value(after, key, form)}"
        if show_change and before and after and abs(before.get(key) or 0.0) > 1e-9 and after.get(key) is not None:
            text += f" ({after[key] / before[key] - 1.0:+.1%})"
        lines.append(text)
    return lines


def head_lines(before, after):
    lines = metric_lines(before, after, HEAD_METRICS)
    if after and "neck_exposed_lines" in after:
        detail = ", ".join(f"{NECK_LINE_NAMES[k]} {v:.3f}" for k, v in after["neck_exposed_lines"].items())
        lines.append(f"  목 노출 (앞/옆/뒤): {detail}")
    if after and "shoulder_clearance" in after:
        state = "겹침" if after["shoulder_overlap"] else "겹침 없음"
        lines.append(f"머리–어깨·팔 간격: {after['shoulder_clearance']:.3f} m ({state})")
    return lines


def body_lines(before, after):
    lines = metric_lines(before, after, BODY_METRICS)
    if after and after.get("overlaps"):
        detail = ", ".join(f"{k} {v}" for k, v in after["overlaps"].items())
        lines.append(f"불필요한 메시 교차 (면 쌍 수): {detail}")
    return lines


def report(objects, head, fit_scale, before_metrics, after_metrics):
    lo, hi = evaluated_bounds(objects)
    height = hi.z - lo.z
    head_lo, head_hi = evaluated_bounds([head])
    head_height = head_hi.z - head_lo.z
    problems = []
    if abs(height - bare_height()) > HEIGHT_TOLERANCE or abs(lo.z) > HEIGHT_TOLERANCE:
        problems.append(f"키·발바닥 오차가 {HEIGHT_TOLERANCE} m 초과")
    if after_metrics and after_metrics.get("shoulder_overlap"):
        problems.append("머리와 어깨·팔이 겹침")
    if after_metrics and any(after_metrics.get("overlaps", {}).values()):
        problems.append("부위 사이 메시 교차")
    ok = not problems

    result = "결과: 정상" if ok else f"결과: 확인 필요 ({', '.join(problems)})"
    overview = [
        f"헤어 제외 키: {height:.4f} m (목표 {bare_height():.3f} m, 차이 {height - bare_height():+.4f})",
        f"헤어 포함 기준 키: {CHARACTER_HEIGHT:.2f} m (정수리 위 헤어 공간 {CROWN_HAIR_SPACE:.3f} m)",
        f"발바닥 Z: {lo.z:.4f} / 머리 꼭대기 Z: {hi.z:.4f}",
        f"머리 높이: {head_height:.3f} m -> {CHARACTER_HEIGHT / HEAD_HEIGHT:.2f}등신 (헤어 포함 기준)",
    ]
    body = body_lines(before_metrics, after_metrics)
    lines = [
        *overview,
        f"X 범위: {lo.x:+.3f} .. {hi.x:+.3f} (중심 {(lo.x + hi.x) / 2:+.4f})",
        f"Y 범위: {lo.y:+.3f} .. {hi.y:+.3f} (앞쪽이 -Y)",
        f"높이 자동 맞춤 배율: {fit_scale:.4f}" if fit_scale is not None else "높이 자동 맞춤: 꺼짐",
        f"부위 수: {len(objects)}개 ('{COLLECTION_NAME}' 컬렉션)",
        "--- 머리·목 (변경 전 -> 후) ---",
        *head_lines(before_metrics, after_metrics),
        "--- 몸 (변경 전 -> 후) ---",
        *body,
        result,
    ]

    print("\n[MainGirlfriend 블록아웃] 검증 결과")
    for line in lines:
        print("  " + line)

    if not bpy.app.background and bpy.context.window_manager is not None:
        summary = [*overview, *body, result]

        def draw(self, _context):
            for line in summary:
                self.layout.label(text=line)
            self.layout.label(text="전체 결과: Blender 시스템 콘솔")

        bpy.context.window_manager.popup_menu(
            draw, title="MainGirlfriend 블록아웃", icon="CHECKMARK" if ok else "ERROR"
        )


def main():
    scene = bpy.context.scene
    existing = bpy.data.collections.get(COLLECTION_NAME)
    before_metrics = head_metrics(tagged_parts(existing.objects)) if existing else None
    collection = reset_collection(scene)
    material = ensure_material()

    center_parts = {
        "Head": build_head,
        "Neck": build_neck,
        "Torso": build_torso,
        "Pelvis": build_pelvis,
    }
    side_parts = {
        "Arm": build_arm,
        "Hand": build_hand,
        "Leg": build_leg,
        "Foot": build_foot,
    }

    sculpts = {"Torso": sculpt_bust}

    objects = []
    for name, builder in center_parts.items():
        verts, faces, pivot = builder()
        objects.append(create_part(name, verts, faces, pivot, collection, material, sculpts.get(name)))

    for name, builder in side_parts.items():
        verts, faces, pivot = builder()
        objects.append(create_part(name + ".L", verts, faces, pivot, collection, material))
        mirrored_pivot = Vector((-pivot.x, pivot.y, pivot.z))
        objects.append(create_part(name + ".R", mirror_x(verts), faces, mirrored_pivot, collection, material))

    fit_scale = fit_height(objects) if AUTO_FIT_HEIGHT else None
    head = next(obj for obj in objects if obj[PART_TAG] == "Head")
    after_metrics = head_metrics(tagged_parts(objects))
    report(objects, head, fit_scale, before_metrics, after_metrics)


if __name__ == "__main__":
    main()
