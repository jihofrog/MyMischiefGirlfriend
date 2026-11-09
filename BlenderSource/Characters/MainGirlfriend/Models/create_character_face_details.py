"""MainGirlfriend face details: eyebrows, extra lashes, nose, mouth and ears on the body blockout head.

Run inside Blender 4.x / 5.x (Scripting workspace > Run Script) after
create_character_blockout.py and create_character_eyes.py.

- Reads the evaluated Blockout_Head mesh and the eye objects in MainGirlfriend_Eyes
  (eye centres, eye width, top of the upper lid line) from the current file and places
  every part relative to them on the face surface. The head, the eyes, Reference_Images
  and every other collection are only read, never changed.
- Objects (character faces -Y, left side .L is +X; the right side is an exact mirror):
    Face_Brow_Root.L / .R        empty at the brow centre, aligned to the face (local -Y points out of the face).
                                 Move in local X / Z and rotate around local Y for expressions.
      Face_Brow.L / .R           thin, soft dark-brown brow following the face (mesh)
    Face_Nose                    small anime nose: a low soft bump with soft shading (mesh)
    Face_Mouth_Root              empty at the mouth centre, aligned to the face (move / rotate the whole mouth)
      Face_Mouth_Smile           empty holding the default bright smile; other expressions become sibling sets
        Face_Mouth_Smile_Inside  dark-pink open mouth
        Face_Mouth_Smile_Teeth   thin upper teeth strip
        Face_Mouth_Smile_Tongue  light-pink tongue
        Face_Mouth_Smile_Line    upper lip line with slightly lifted corners
    Face_UpperLashes.L / .R      extra upper lashes, longer toward the outer corner and curling up
                                 (child of Eye_UpperLid, so they follow a blink)
    Face_LowerLashes.L / .R      a few short lower lashes at the outer corner (child of Eye_Root)
    Face_Ear.L / .R              low-poly ears with a rolled rim and a pink inner bowl (origin at the attachment)
    Face_Blush.L / .R            soft pink cheek blush (vertex colours fading into the skin, no transparency)
- The lash shapes reuse the lid lines of create_character_eyes.py (same folder); the eye objects are not changed.
- Brow and mouth meshes shrinkwrap onto the head, so moving or rotating their roots keeps them on the face.
- Only the MainGirlfriend_FaceDetails collection is rebuilt on every run, so parts are never duplicated.
- The .blend file is never saved by this script.
"""

import importlib.util
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector, kdtree
from mathutils.bvhtree import BVHTree


# ===========================================================================
# Eyebrows (left brow; metres unless noted). Measured on Front.png and the concept face close-up.
# ===========================================================================

BROW_LIFT = 0.06           # brow centre line above the top of the upper lid line (concept: high, under the bangs)
BROW_INWARD = 0.06         # brow centre toward the nose from the eye centre, fraction of eye width
BROW_LENGTH = 0.062        # inner end to outer tip
BROW_THICKNESS = 0.0042    # at the thickest part
BROW_INNER_WIDTH = 0.85    # thickness at the rounded inner end, fraction of BROW_THICKNESS
BROW_TIP_WIDTH = 0.15      # thickness at the outer tip, fraction of BROW_THICKNESS
BROW_ARCH = 0.006          # height of the soft arch above the line between both ends
BROW_PEAK_AT = 0.45        # arch peak along the brow (0 = inner .. 1 = outer)
BROW_INNER_DROP = 0.0      # inner end lowered (positive reads worried / angry; keep 0 for a bright look)
BROW_OUTER_DROP = 0.003    # outer tip lowered; gentle droop keeps the brow soft and cute
BROW_SOFT_EDGE = 0.35      # how much the brow edges and inner end fade toward the softer colour

# ===========================================================================
# Nose
# ===========================================================================

NOSE_HEIGHT = 0.32         # nose tip below the eye centres, fraction of the eye-centre-to-chin distance
NOSE_WIDTH = 0.012         # width of the rounded tip
NOSE_TIP_UP = 0.6          # tip radius above its centre, fraction of NOSE_WIDTH
NOSE_TIP_DOWN = 0.45       # tip radius below its centre (short, so the underside turns quickly)
NOSE_LENGTH = 0.028        # bridge length above the tip that rises softly out of the face
NOSE_BRIDGE = 0.3          # bridge height, fraction of NOSE_PROTRUSION
NOSE_PROTRUSION = 0.007    # height of the small pointed tip above the face (concept side view)
NOSE_SHADOW = 0.75         # strength of the soft shadow under the tip and beside the bridge
NOSE_HIGHLIGHT = 0.2       # strength of the small highlight on the tip

# ===========================================================================
# Mouth (default expression: bright open smile)
# ===========================================================================

MOUTH_HEIGHT = 0.535       # middle of the upper edge below the eye centres, fraction of the eye-centre-to-chin distance
MOUTH_WIDTH = 0.088        # corner to corner
MOUTH_OPEN = 0.055         # depth of the round lower edge below the corners
MOUTH_SMILE = 0.005        # corners rise this far above the middle of the upper edge
MOUTH_ROUNDNESS = 2.2      # higher = fuller, flatter-bottomed U for the lower edge
MOUTH_FULLNESS = 0.6       # <1 widens the lower edge near the corners (softer D shape)
TEETH_SPAN = 0.72          # upper teeth span, fraction of the mouth width
TEETH_HEIGHT = 0.004       # upper teeth height at the middle
TONGUE_WIDTH = 0.78        # tongue width, fraction of the mouth width
TONGUE_HEIGHT = 0.5        # tongue top above the lowest point of the mouth, fraction of MOUTH_OPEN
LIP_LINE_WIDTH = 0.0012    # upper lip line thickness
LIP_LINE_EXTEND = 0.1      # the line continues past each corner by this fraction of the half width (smile tick)
LIP_LINE_OVERLAP = 0.5     # share of the lip line that lies over the mouth opening

# ===========================================================================
# Extra lashes (added on top of the existing eyes; the eye objects themselves are not changed)
# ===========================================================================

UPPER_LASHES = (
    # (position along the upper lid line incl. its outer wing: 0 = inner corner .. 1 = wing tip,
    #  length m, sweep toward the outer corner deg, upward curl toward the tip deg)
    # Longer toward the outer corner and curling up, between the three short lashes of the eye script.
    (0.62, 0.009, 15.0, 6.0),
    (0.78, 0.013, 35.0, 15.0),
    (0.92, 0.019, 68.0, 32.0),
)
UPPER_LASH_WIDTH = 0.004       # root width; each lash tapers to a point
UPPER_LASH_LIFT = 0.0015       # lash tips lift this far off the face
LOWER_LASHES = (
    # (position across the eye: 0 = under the eye centre .. 1 = outer corner, length m, sweep toward the outer corner deg)
    # Kept inside the end of the eye script's outer side line, which covers the outer corner itself.
    (0.42, 0.005, 15.0),
    (0.57, 0.0065, 30.0),
    (0.70, 0.008, 45.0),
)
LOWER_LASH_WIDTH = 0.0024
LOWER_LASH_OFFSET = 0.0012     # roots sit this far outside the eye-white edge

# ===========================================================================
# Ears
# ===========================================================================

EAR_HEIGHT_AT = 0.2        # ear centre below the eye centres, fraction of the eye-centre-to-chin distance
EAR_HEIGHT = 0.1           # top of the rim to the bottom of the lobe
EAR_LENGTH = 0.058         # attached front edge to the back of the rim
EAR_Y = 0.04               # where the ear meets the side of the head (Y, + = toward the back)
EAR_FORWARD = 25.0         # degrees the ear turns from facing sideways toward the front (shows in the front view)
EAR_TILT = -8.0            # degrees; negative leans the top of the ear back
EAR_EMBED = 0.004          # how far the attached edge sinks into the head (no gap)
EAR_THICKNESS = 0.008      # at the centre; the rim is thinner
EAR_RELIEF = 0.006         # depth of the inner bowl / height of the rolled rim
EAR_INNER_PINK = 0.55      # strength of the pink inside the ear
# Outline (a: 0 = attached front edge .. 1 = back of the rim, b: -1 = lobe .. 1 = top), as in the concept:
# a wide round top and a smaller lobe.
EAR_SHAPE = (
    (0.0, 0.75), (0.25, 0.97), (0.55, 1.0), (0.82, 0.85), (0.98, 0.5), (1.0, 0.1),
    (0.9, -0.3), (0.7, -0.6), (0.45, -0.85), (0.2, -0.95), (0.03, -0.75), (-0.05, 0.0),
)

# ===========================================================================
# Cheek blush (soft pink below the outer half of each eye, as in the concept)
# ===========================================================================

BLUSH_OUTWARD = 0.15       # blush centre outward from the eye centre, fraction of eye width
BLUSH_BELOW = 0.34         # blush centre below the eye centre, fraction of the eye-centre-to-chin distance
BLUSH_SIZE = (0.06, 0.032) # width, height
BLUSH_STRENGTH = 0.7       # pink at the centre; fades to the plain skin colour at the edge
BLUSH_GRID = (12, 8)

# ===========================================================================
# Depth (metres in front of the face surface)
# ===========================================================================

BROW_GAP = 0.0004
NOSE_GAP = 0.0002          # rim of the nose patch; the bump grows from here
MOUTH_GAP = 0.0004         # mouth inside
BLUSH_GAP = 0.0003
MOUTH_LAYER = 0.0003       # extra gap per layer: teeth / tongue (1), lip line (2)

# ===========================================================================
# Colours (sRGB hex)
# ===========================================================================

COLOR_BROW = "4E2F23"           # soft dark brown, matches the brown hair
COLOR_BROW_SOFT = "8E6656"      # brow edges and inner end
COLOR_NOSE_SHADOW = "D99A8B"    # warm pink-brown shadow
COLOR_NOSE_HIGHLIGHT = "FFF6F1"
COLOR_SKIN_FALLBACK = "FFDECC"  # used only if the head material has no readable colour
COLOR_MOUTH_INSIDE = "A33E4E"   # dark pink
COLOR_MOUTH_DEEP = "6A1C2A"     # shadow under the upper lip and in the corners
COLOR_TEETH = "FFF9F6"
COLOR_TEETH_SHADE = "E9D6D3"
COLOR_TONGUE = "F49BA0"         # light pink
COLOR_TONGUE_SHADE = "E2878F"   # back of the tongue
COLOR_LIP_LINE = "5E2422"
COLOR_LASH = "1A0A06"           # same dark brown-black as the upper lid line
COLOR_LOWER_LASH = "4A2418"     # softer, lighter lower lashes
COLOR_EAR_INNER = "EFA096"      # pink inside the ear
COLOR_BLUSH = "F49C9A"

# ===========================================================================
# Output
# ===========================================================================

COLLECTION_NAME = "MainGirlfriend_FaceDetails"
OBJECT_PREFIX = "Face_"
PART_TAG = "mg_face_part"
BLOCKOUT_COLLECTION = "MainGirlfriend_Blockout"
EYES_COLLECTION = "MainGirlfriend_Eyes"
HEAD_PART = ("mg_blockout_part", "Head")
HEAD_OBJECT_NAME = "Blockout_Head"
EYE_TAG = "mg_eye_part"
PROTECTED_COLLECTIONS = ("Reference_Images", BLOCKOUT_COLLECTION, EYES_COLLECTION)
MATERIAL_PREFIX = "MG_Face_"
SHADE_ATTRIBUTE = "FaceShade"   # per-vertex colour (also exported for Unity)
FOLLOW_FACE_SURFACE = True      # shrinkwrap brows and mouth onto the head
SYMMETRY_TOLERANCE = 0.0005     # metres, after the shrinkwrap modifiers

EYES_SCRIPT = "create_character_eyes.py"  # lid lines for the lashes come from here (same folder)

# Mesh density, kept low for Unity mobile.
BROW_SAMPLES = 24
BROW_ROWS = 2
NOSE_GRID = (14, 18)            # quads across / along the nose patch
MOUTH_COLUMNS = 24
MOUTH_ROWS = 6
EAR_RINGS = 4
EAR_SEGMENTS = 16
EAR_SUBDIV = 1                  # Subdivision Surface level on the ears

UP = Vector((0.0, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def smoothstep(edge0, edge1, x):
    t = min(1.0, max(0.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def side_normals(path):
    """Unit normals to the left of the walking direction of a 2D polyline."""
    normals = []
    for i in range(len(path)):
        (u0, v0), (u1, v1) = path[max(i - 1, 0)], path[min(i + 1, len(path) - 1)]
        length = math.hypot(u1 - u0, v1 - v0) or 1.0
        normals.append((-(v1 - v0) / length, (u1 - u0) / length))
    return normals


def hex_to_linear(value):
    def channel(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return tuple(channel(int(value[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


def mix(a, b, f):
    return tuple(x + (y - x) * f for x, y in zip(a, b))


def cosine_spacing(half, count):
    """count + 1 values from -half to +half, denser toward both ends."""
    return [-half * math.cos(math.pi * i / count) for i in range(count + 1)]


# ---------------------------------------------------------------------------
# Head and eyes (read only)
# ---------------------------------------------------------------------------

def evaluated_world(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    verts = [obj.matrix_world @ v.co for v in mesh.vertices]
    polys = [tuple(p.vertices) for p in mesh.polygons]
    evaluated.to_mesh_clear()
    return verts, polys


def find_head():
    blockout = bpy.data.collections.get(BLOCKOUT_COLLECTION)
    for obj in (blockout.all_objects if blockout else bpy.data.objects):
        if obj.type == "MESH" and obj.get(HEAD_PART[0]) == HEAD_PART[1]:
            return obj
    obj = bpy.data.objects.get(HEAD_OBJECT_NAME)
    if obj is None or obj.type != "MESH":
        raise RuntimeError(f"머리 메시({HEAD_OBJECT_NAME})를 찾을 수 없습니다. create_character_blockout.py를 먼저 실행하세요.")
    return obj


class Head:
    """World-space evaluated head with front-view ray casts onto the face."""

    def __init__(self, obj):
        verts, polys = evaluated_world(obj)
        self.obj = obj
        self.bvh = BVHTree.FromPolygons(verts, polys)
        self.min_y = min(v.y for v in verts)
        self.max_x = max(v.x for v in verts)
        self.chin_z = min(v.z for v in verts)
        self.skin = head_skin_colour(obj)

    def front_y(self, x, z):
        hit = self.bvh.ray_cast(Vector((x, self.min_y - 1.0, z)), Vector((0.0, 1.0, 0.0)))[0]
        return None if hit is None else hit.y

    def surface(self, x, z):
        y = self.front_y(x, z)
        if y is None:
            raise RuntimeError(f"얼굴 앞면을 찾지 못했습니다 (X {x:.3f}, Z {z:.3f}). 위치 파라미터를 확인하세요.")
        return Vector((x, y, z))

    def point(self, x, z, gap):
        """Face point seen from the front (as in Front.png), pushed gap metres toward the viewer."""
        return self.surface(x, z) - Vector((0.0, gap, 0.0))

    def normal(self, x, z, spread=0.006):
        """Outward face normal averaged over a small cross around (x, z)."""
        total = Vector((0.0, 0.0, 0.0))
        for dx, dz in ((0, 0), (spread, 0), (-spread, 0), (0, spread), (0, -spread)):
            hit = self.bvh.ray_cast(Vector((x + dx, self.min_y - 1.0, z + dz)), Vector((0.0, 1.0, 0.0)))
            if hit[0] is not None:
                n = hit[1] if hit[1].y < 0.0 else -hit[1]
                total += n
        return total.normalized() if total.length > 0.0 else Vector((0.0, -1.0, 0.0))

    def frame(self, x, z):
        """World matrix on the face at (x, z): local -Y out of the face, local Z up along the face."""
        n = self.normal(x, z)
        y_axis = -n
        z_axis = (UP - n * UP.dot(n)).normalized()
        x_axis = y_axis.cross(z_axis)
        rotation = Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()
        return Matrix.Translation(self.surface(x, z)) @ rotation


def head_skin_colour(obj):
    material = obj.active_material
    if material is not None and material.node_tree is not None:
        for node in material.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                return tuple(node.inputs["Base Color"].default_value[:3])
    if material is not None:
        return tuple(material.diffuse_color[:3])
    return hex_to_linear(COLOR_SKIN_FALLBACK)


class Eyes:
    """Eye centres, eye width and the top of the upper lid line, read from the eye objects."""

    def __init__(self):
        collection = bpy.data.collections.get(EYES_COLLECTION)
        parts = {}
        for obj in (collection.all_objects if collection else bpy.data.objects):
            if EYE_TAG in obj:
                parts[obj[EYE_TAG]] = obj
        missing = [name for name in ("Root.L", "Root.R", "White.L", "UpperLid.L") if name not in parts]
        if missing:
            raise RuntimeError(f"눈 오브젝트({', '.join(missing)})를 찾을 수 없습니다. create_character_eyes.py를 먼저 실행하세요.")
        self.parts = parts
        bpy.context.view_layer.update()
        left = parts["Root.L"].matrix_world.translation
        right = parts["Root.R"].matrix_world.translation
        self.centre_x = (left.x + right.x) / 2.0
        self.left = left.copy()
        self.z = (left.z + right.z) / 2.0
        white, _ = evaluated_world(parts["White.L"])
        self.width = max(v.x for v in white) - min(v.x for v in white)
        lid, _ = evaluated_world(parts["UpperLid.L"])
        self.lid_top = max(v.z for v in lid)

    def upper_parts(self, suffix=".L"):
        names = ("UpperLid", "UpperLashes", "UpperCrease", "OuterLine")
        return [self.parts[n + suffix] for n in names if n + suffix in self.parts]

    def lid(self, suffix):
        return self.parts.get("UpperLid" + suffix) or self.parts["Root" + suffix]


def script_folders():
    folders = []
    if globals().get("__file__"):
        folders.append(os.path.dirname(os.path.abspath(__file__)))
    for text in bpy.data.texts:
        if text.filepath:
            folders.append(os.path.dirname(bpy.path.abspath(text.filepath)))
    if bpy.data.filepath:
        folders.append(os.path.dirname(bpy.data.filepath))
    return folders


def load_eye_module():
    """create_character_eyes.py as a module (its main() does not run), for the lid line geometry."""
    for folder in script_folders():
        path = os.path.join(folder, EYES_SCRIPT)
        if os.path.exists(path):
            spec = importlib.util.spec_from_file_location("mg_character_eyes", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise RuntimeError(f"{EYES_SCRIPT}를 찾을 수 없습니다. 이 스크립트와 같은 폴더에 있어야 합니다.")


class EyeLines:
    """Upper lid line and lower edge of the left eye from the eye script, moved onto the actual Eye_Root.L."""

    def __init__(self, eyes):
        self.module = load_eye_module()
        self.layout = self.module.EyeLayout(self.module.Head(self.module.find_head()))
        self.shift = eyes.left - self.layout.world(0.0, 0.0, 0)

    def strip(self, centre, width, layer, lift):
        verts, faces = self.module.taper_strip(self.layout, centre, width, layer, lift=lift)
        return [v + self.shift for v in verts], faces


# ---------------------------------------------------------------------------
# Layout (left side; the right side is mirrored around the face centre)
# ---------------------------------------------------------------------------

class Layout:
    def __init__(self, head, eyes):
        self.head, self.eyes = head, eyes
        drop = eyes.z - head.chin_z
        self.cx = eyes.centre_x
        self.brow = (eyes.left.x - BROW_INWARD * eyes.width, eyes.lid_top + BROW_LIFT)
        self.nose_z = eyes.z - NOSE_HEIGHT * drop
        self.mouth_top_z = eyes.z - MOUTH_HEIGHT * drop
        self.mouth_centre_z = self.mouth_top_z + mouth_top(0.0) - MOUTH_OPEN / 2.0

    def mirror(self, p):
        return Vector((2.0 * self.cx - p.x, p.y, p.z))


# ---------------------------------------------------------------------------
# Eyebrow
# ---------------------------------------------------------------------------

def brow_width(t):
    cap = max(0.2, min(1.0, t / 0.06)) ** 0.5  # rounded inner end
    body = BROW_INNER_WIDTH + (1.0 - BROW_INNER_WIDTH) * smoothstep(0.0, 0.3, t)
    tail = 1.0 - (1.0 - BROW_TIP_WIDTH) * smoothstep(0.5, 1.0, t)
    return BROW_THICKNESS * cap * body * tail


def brow_mesh(layout):
    """Left brow: world verts, faces and colours. u runs from the inner end (nose) to the outer tip."""
    k = math.log(0.5) / math.log(BROW_PEAK_AT)

    def centre(t):
        return BROW_ARCH * math.sin(math.pi * t ** k) - BROW_INNER_DROP * (1.0 - t) - BROW_OUTER_DROP * t

    mid = centre(0.5)
    path = [((i / (BROW_SAMPLES - 1) - 0.5) * BROW_LENGTH, centre(i / (BROW_SAMPLES - 1)) - mid)
            for i in range(BROW_SAMPLES)]
    bx, bz = layout.brow
    brow, soft = hex_to_linear(COLOR_BROW), hex_to_linear(COLOR_BROW_SOFT)
    verts, colours, faces = [], [], []
    for i, ((u, v), (nu, nv)) in enumerate(zip(path, side_normals(path))):
        t = i / (BROW_SAMPLES - 1)
        half = brow_width(t) / 2.0
        for j in range(BROW_ROWS + 1):
            a = 2.0 * j / BROW_ROWS - 1.0
            verts.append(layout.head.point(bx + u + nu * half * a, bz + v + nv * half * a, BROW_GAP))
            fade = max(smoothstep(0.35, 1.0, abs(a)), 1.0 - smoothstep(0.0, 0.18, t))
            colours.append(mix(brow, soft, BROW_SOFT_EDGE * fade))
    for i in range(BROW_SAMPLES - 1):
        for j in range(BROW_ROWS):
            a, b = i * (BROW_ROWS + 1) + j, (i + 1) * (BROW_ROWS + 1) + j
            faces.append((a, b, b + 1, a + 1))
    return verts, faces, colours


# ---------------------------------------------------------------------------
# Nose
# ---------------------------------------------------------------------------

def nose_height(u, v):
    """Bump height (fraction of NOSE_PROTRUSION) around the tip at (0, 0): rounded tip plus a soft bridge."""
    a = NOSE_WIDTH / 2.0
    b = NOSE_WIDTH * (NOSE_TIP_UP if v > 0.0 else NOSE_TIP_DOWN)
    d2 = (u / a) ** 2 + (v / b) ** 2
    tip = (1.0 - math.sqrt(d2)) ** 1.3 if d2 < 1.0 else 0.0  # small pointed tip, soft at the rim
    ridge = 0.0
    if 0.0 < v < NOSE_LENGTH:
        ridge = NOSE_BRIDGE * (1.0 - v / NOSE_LENGTH) ** 1.5 * math.exp(-(u / (a * 0.5)) ** 2)
    return tip + ridge * (1.0 - tip)


def nose_mesh(layout):
    head = layout.head
    a = NOSE_WIDTH / 2.0
    u_half = a * 1.8
    v_lo, v_hi = -NOSE_WIDTH * NOSE_TIP_DOWN * 1.9, NOSE_LENGTH * 1.05
    normal = head.normal(layout.cx, layout.nose_z)
    skin = head.skin
    shadow_c, light_c = hex_to_linear(COLOR_NOSE_SHADOW), hex_to_linear(COLOR_NOSE_HIGHLIGHT)
    cols, rows = NOSE_GRID
    verts, colours, faces = [], [], []
    for r in range(rows + 1):
        v = v_lo + (v_hi - v_lo) * r / rows
        for c in range(cols + 1):
            u = -u_half + 2.0 * u_half * c / cols
            h = nose_height(u, v)
            base = head.surface(layout.cx + u, layout.nose_z + v)
            verts.append(base + normal * (NOSE_GAP + NOSE_PROTRUSION * h))
            # Soft shading, faded to the plain skin colour at the patch border.
            edge = smoothstep(0.0, 0.3, 1.0 - max(abs(u) / u_half, v / v_hi if v > 0.0 else v / v_lo))
            under = math.exp(-((u / (a * 0.9)) ** 2 + ((v + NOSE_WIDTH * NOSE_TIP_DOWN * 0.7) / (NOSE_WIDTH * 0.3)) ** 2))
            side = 0.5 * math.exp(-(((abs(u) - a * 0.6) / (a * 0.35)) ** 2 + ((v - NOSE_LENGTH * 0.3) / (NOSE_LENGTH * 0.45)) ** 2))
            light = math.exp(-((u / (a * 0.35)) ** 2 + ((v - NOSE_WIDTH * NOSE_TIP_UP * 0.25) / (NOSE_WIDTH * 0.18)) ** 2))
            colour = mix(skin, shadow_c, NOSE_SHADOW * min(1.0, under + side) * edge)
            colours.append(mix(colour, light_c, NOSE_HIGHLIGHT * light * edge))
    for r in range(rows):
        for c in range(cols):
            a0, b0 = r * (cols + 1) + c, (r + 1) * (cols + 1) + c
            faces.append((a0, a0 + 1, b0 + 1, b0))
    return verts, faces, colours


# ---------------------------------------------------------------------------
# Cheek blush
# ---------------------------------------------------------------------------

def blush_mesh(layout):
    """Left blush: a patch on the cheek, pink in the middle and exactly the skin colour at its border."""
    head, eyes = layout.head, layout.eyes
    cx = eyes.left.x + BLUSH_OUTWARD * eyes.width
    cz = eyes.z - BLUSH_BELOW * (eyes.z - head.chin_z)
    half_w, half_h = BLUSH_SIZE[0] * 0.65, BLUSH_SIZE[1] * 0.65
    pink = hex_to_linear(COLOR_BLUSH)
    cols, rows = BLUSH_GRID
    verts, colours, faces = [], [], []
    for r in range(rows + 1):
        v = -half_h + 2.0 * half_h * r / rows
        for c in range(cols + 1):
            u = -half_w + 2.0 * half_w * c / cols
            verts.append(head.point(cx + u, cz + v, BLUSH_GAP))
            d2 = (u / (BLUSH_SIZE[0] / 2.0)) ** 2 + (v / (BLUSH_SIZE[1] / 2.0)) ** 2
            edge = smoothstep(0.0, 0.25, 1.0 - max(abs(u) / half_w, abs(v) / half_h))
            colours.append(mix(head.skin, pink, BLUSH_STRENGTH * math.exp(-1.6 * d2) * edge))
    for r in range(rows):
        for c in range(cols):
            a, b = r * (cols + 1) + c, (r + 1) * (cols + 1) + c
            faces.append((a, a + 1, b + 1, b))
    return verts, faces, colours, Vector((cx, 0.0, cz))


# ---------------------------------------------------------------------------
# Mouth (u = 0 at the face centre, v = 0 at the middle of the upper edge)
# ---------------------------------------------------------------------------

def mouth_top(u):
    s = min(1.0, abs(u) / (MOUTH_WIDTH / 2.0))
    return MOUTH_SMILE * s * s


def mouth_bottom(u):
    s = min(1.0, abs(u) / (MOUTH_WIDTH / 2.0))
    return mouth_top(u) - MOUTH_OPEN * max(0.0, 1.0 - s ** MOUTH_ROUNDNESS) ** MOUTH_FULLNESS


def lens_grid(us, top, bottom, rows):
    """Mesh between v = top(u) and v = bottom(u); columns where both meet become one vertex.

    Returns (uv, faces, params) with params = (u, r), r = 0 on the top edge .. 1 on the bottom edge.
    """
    uv, params, columns = [], [], []
    for u in us:
        t, b = top(u), bottom(u)
        if t - b <= 1e-6:
            columns.append([len(uv)])
            uv.append((u, (t + b) / 2.0))
            params.append((u, 0.5))
            continue
        column = []
        for j in range(rows + 1):
            r = j / rows
            column.append(len(uv))
            uv.append((u, t + (b - t) * r))
            params.append((u, r))
        columns.append(column)
    faces = []
    for a, b in zip(columns, columns[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            faces += [(a[0], b[j + 1], b[j]) for j in range(len(b) - 1)]
        elif len(b) == 1:
            faces += [(a[j], a[j + 1], b[0]) for j in range(len(a) - 1)]
        else:
            faces += [(a[j], a[j + 1], b[j + 1], b[j]) for j in range(len(a) - 1)]
    return uv, faces, params


def meeting_point(f, lo, hi):
    """u in [lo, hi] where f changes sign (f(lo) > 0 > f(hi))."""
    for _ in range(40):
        mid = (lo + hi) / 2.0
        lo, hi = (mid, hi) if f(mid) > 0.0 else (lo, mid)
    return lo


def mouth_parts(layout):
    """Smile parts as {name: (verts, faces, colours, layer)} in world space."""
    half = MOUTH_WIDTH / 2.0
    head = layout.head

    def world(uv, layer):
        return [head.point(layout.cx + u, layout.mouth_top_z + v, MOUTH_GAP + layer * MOUTH_LAYER) for u, v in uv]

    parts = {}

    uv, faces, params = lens_grid(cosine_spacing(half, MOUTH_COLUMNS), mouth_top, mouth_bottom, MOUTH_ROWS)
    inside, deep = hex_to_linear(COLOR_MOUTH_INSIDE), hex_to_linear(COLOR_MOUTH_DEEP)
    colours = [mix(inside, deep, max(0.9 * (1.0 - smoothstep(0.0, 0.55, r)), 0.6 * smoothstep(0.7, 1.0, abs(u) / half)))
               for u, r in params]
    parts["Inside"] = (world(uv, 0), faces, colours, 0)

    inset = 0.0003
    span = TEETH_SPAN * half

    def teeth_top(u):
        return mouth_top(u) - inset

    def teeth_bottom(u):
        return teeth_top(u) - TEETH_HEIGHT * math.sqrt(max(0.0, 1.0 - (u / span) ** 2))

    uv, faces, params = lens_grid(cosine_spacing(span, MOUTH_COLUMNS // 2), teeth_top, teeth_bottom, 3)
    teeth, teeth_shade = hex_to_linear(COLOR_TEETH), hex_to_linear(COLOR_TEETH_SHADE)
    colours = [mix(teeth, teeth_shade, 0.6 * (1.0 - smoothstep(0.0, 0.7, r))) for _, r in params]
    parts["Teeth"] = (world(uv, 1), faces, colours, 1)

    tongue_half = TONGUE_WIDTH * half
    lowest = mouth_bottom(0.0)

    def tongue_top(u):
        return lowest + TONGUE_HEIGHT * MOUTH_OPEN * math.sqrt(max(0.0, 1.0 - (u / tongue_half) ** 2))

    def tongue_bottom(u):
        return mouth_bottom(u) + inset

    end = meeting_point(lambda u: tongue_top(u) - tongue_bottom(u), 0.0, tongue_half)
    uv, faces, params = lens_grid(cosine_spacing(end, MOUTH_COLUMNS // 2), tongue_top, tongue_bottom, 6)
    tongue, tongue_shade = hex_to_linear(COLOR_TONGUE), hex_to_linear(COLOR_TONGUE_SHADE)
    colours = [mix(tongue, tongue_shade, 0.7 * (1.0 - smoothstep(0.0, 0.45, r))) for _, r in params]
    parts["Tongue"] = (world(uv, 1), faces, colours, 1)

    reach = half * (1.0 + LIP_LINE_EXTEND)
    path = [(u, mouth_top(u) if abs(u) <= half else MOUTH_SMILE * (abs(u) / half) ** 2)
            for u in cosine_spacing(reach, MOUTH_COLUMNS)]
    uv, faces = [], []
    for i, ((u, v), (nu, nv)) in enumerate(zip(path, side_normals(path))):
        s = abs(u) / reach
        w = LIP_LINE_WIDTH * max(0.05, 1.0 - smoothstep(0.8, 1.0, s))
        for j in range(3):
            offset = w * (j / 2.0 - LIP_LINE_OVERLAP)
            uv.append((u + nu * offset, v + nv * offset))
    for i in range(len(path) - 1):
        for j in range(2):
            a, b = i * 3 + j, (i + 1) * 3 + j
            faces.append((a, b, b + 1, a + 1))
    parts["Line"] = (world(uv, 2), faces, [hex_to_linear(COLOR_LIP_LINE)] * len(uv), 2)
    return parts


# ---------------------------------------------------------------------------
# Lashes (left eye, 2D lid coordinates of the eye script: u away from the nose, v up)
# ---------------------------------------------------------------------------

def grow(root, direction, length, steps):
    """Centre line from root; direction(t) gives the unit step direction at t = 0..1."""
    centre = [root]
    for k in range(1, steps + 1):
        du, dv = direction(k / steps)
        pu, pv = centre[-1]
        centre.append((pu + du * length / steps, pv + dv * length / steps))
    return centre


def merge_into(verts, faces, part):
    base = len(verts)
    verts.extend(part[0])
    faces.extend(tuple(i + base for i in f) for f in part[1])


def upper_lash_mesh(lines):
    """Flat tapered lashes rooted in the top edge of the lid line: sweep outward, then curl up toward the tip."""
    m = lines.module
    path, normals, thickness, _ = m.upper_lid_line(lines.layout)
    last = len(path) - 1
    verts, faces = [], []
    for position, length, sweep, curl in UPPER_LASHES:
        i = round(position * last)
        (u, v), (nu, nv), w = path[i], normals[i], thickness[i]
        root = w * (1.0 - m.UPPER_LID_OVERLAP) - UPPER_LASH_WIDTH * 0.6

        def direction(t, nu=nu, nv=nv, sweep=sweep, curl=curl):
            return m.rotate(nu, nv, -(sweep - curl * t ** 1.5))

        centre = grow((u + nu * root, v + nv * root), direction, length, 6)
        merge_into(verts, faces, lines.strip(centre, UPPER_LASH_WIDTH, m.LID_LAYER + 1.2, UPPER_LASH_LIFT))
    return verts, faces


def lower_lash_mesh(lines):
    """Short straight lashes just below the outer half of the lower edge, pointing down and outward."""
    m = lines.module
    _, lower = lines.layout.white.edges()
    lower = m.resample(lower, 48)
    normals = m.side_normals(lower)  # walking inner -> outer along the bottom, these point into the eye
    verts, faces = [], []
    half = lines.layout.width / 2.0
    for position, length, sweep in LOWER_LASHES:
        i = next((k for k, (u, _) in enumerate(lower) if u >= position * half), len(lower) - 1)
        (u, v), (nu, nv) = lower[i], normals[i]
        du, dv = m.rotate(-nu, -nv, sweep)
        root = (u - nu * LOWER_LASH_OFFSET, v - nv * LOWER_LASH_OFFSET)
        centre = grow(root, lambda t, du=du, dv=dv: (du, dv), length, 3)
        merge_into(verts, faces, lines.strip(centre, LOWER_LASH_WIDTH, m.LID_LAYER, 0.0))
    return verts, faces


# ---------------------------------------------------------------------------
# Ears (left ear; the right ear is mirrored)
# ---------------------------------------------------------------------------

def side_frame(x_axis):
    """Right-handed rotation with the given X axis and Z as close to world up as possible."""
    y_axis = UP.cross(x_axis).normalized()
    z_axis = x_axis.cross(y_axis).normalized()
    return Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()


def ear_frame(layout):
    """(root on the head side, back, out) for the left ear. out faces sideways (+X) turned EAR_FORWARD toward the front."""
    head = layout.head
    z = layout.eyes.z - EAR_HEIGHT_AT * (layout.eyes.z - head.chin_z)
    location, normal, _, _ = head.bvh.ray_cast(Vector((head.max_x + 1.0, EAR_Y, z)), Vector((-1.0, 0.0, 0.0)))
    if location is None:
        raise RuntimeError("귀 위치에서 머리 옆면을 찾지 못했습니다. EAR_Y / EAR_HEIGHT_AT을 확인하세요.")
    if normal.x < 0.0:
        normal = -normal
    out = Matrix.Rotation(-math.radians(EAR_FORWARD), 3, "Z") @ Vector((1.0, 0.0, 0.0))
    back = UP.cross(out).normalized()
    return location - normal * EAR_EMBED, back, out


def ear_mesh(layout, module):
    """Closed low-poly ear shell: rolled rim and a pink inner bowl in front, a thinner back that sinks into the head."""
    head = layout.head
    origin, back, out = ear_frame(layout)
    ca = sum(a for a, _ in EAR_SHAPE) / len(EAR_SHAPE)
    cb = sum(b for _, b in EAR_SHAPE) / len(EAR_SHAPE)
    outline = module.SplineOutline([(a - ca, b - cb) for a, b in EAR_SHAPE], EAR_LENGTH, EAR_HEIGHT / 2.0, EAR_TILT)
    centre = origin + back * (ca * EAR_LENGTH) + UP * (cb * EAR_HEIGHT / 2.0)
    skin, pink = head.skin, hex_to_linear(COLOR_EAR_INNER)

    verts, colours, along = [], [], []
    for side in ("front", "back"):
        for ring in range(EAR_RINGS + 1):
            r = ring / EAR_RINGS
            for seg in range(1 if ring == 0 else EAR_SEGMENTS):
                u, v = outline.point(2.0 * math.pi * seg / EAR_SEGMENTS, r) if ring else (0.0, 0.0)
                if side == "front":
                    c = EAR_RELIEF * (0.6 * math.exp(-((r - 0.75) / 0.15) ** 2) - 0.5 * (1.0 - r * r))
                    colours.append(mix(skin, pink, EAR_INNER_PINK * (1.0 - smoothstep(0.45, 0.85, r))))
                else:
                    c = -EAR_THICKNESS * (1.0 - 0.6 * r ** 3)
                    colours.append(skin)
                verts.append(centre + back * u + UP * v + out * c)
                along.append((u + ca * EAR_LENGTH) / EAR_LENGTH)

    # Pull the attached front edge (and the back of the shell behind it) onto the head,
    # so no gap shows where the head side curves away.
    for i, p in enumerate(verts):
        reach = 0.12 if i < len(verts) // 2 else 0.35
        weight = 1.0 - smoothstep(0.0, reach, along[i])
        if weight <= 0.0:
            continue
        hit = head.bvh.ray_cast(p, Vector((-1.0, 0.0, 0.0)), 0.03)[0]
        if hit is not None:
            verts[i] = p - Vector(((p.x - hit.x + EAR_EMBED) * weight, 0.0, 0.0))

    per_side = 1 + EAR_RINGS * EAR_SEGMENTS

    def index(side, ring, seg):
        return side * per_side + (0 if ring == 0 else 1 + (ring - 1) * EAR_SEGMENTS + seg % EAR_SEGMENTS)

    faces = []
    for side in (0, 1):
        side_faces = [(index(side, 0, 0), index(side, 1, s), index(side, 1, s + 1)) for s in range(EAR_SEGMENTS)]
        for ring in range(2, EAR_RINGS + 1):
            side_faces += [(index(side, ring - 1, s), index(side, ring, s), index(side, ring, s + 1), index(side, ring - 1, s + 1))
                           for s in range(EAR_SEGMENTS)]
        faces += side_faces if side == 0 else [tuple(reversed(f)) for f in side_faces]
    faces += [(index(0, EAR_RINGS, s), index(1, EAR_RINGS, s), index(1, EAR_RINGS, s + 1), index(0, EAR_RINGS, s + 1))
              for s in range(EAR_SEGMENTS)]
    return verts, faces, colours, origin, out


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def shade_material(name, roughness, specular=0.5):
    """Principled BSDF whose base colour comes from the per-vertex FaceShade colours."""
    material = bpy.data.materials.get(MATERIAL_PREFIX + name) or bpy.data.materials.new(MATERIAL_PREFIX + name)
    material.roughness = roughness
    if material.node_tree is None and hasattr(material, "use_nodes"):
        material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    attribute = tree.nodes.new("ShaderNodeAttribute")
    attribute.attribute_name = SHADE_ATTRIBUTE
    attribute.location, bsdf.location, output.location = (0, 0), (300, 0), (600, 0)
    tree.links.new(attribute.outputs["Color"], bsdf.inputs["Base Color"])
    tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = roughness
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    return material


# ---------------------------------------------------------------------------
# Scene helpers
# ---------------------------------------------------------------------------

def reset_collection(scene):
    collection = bpy.data.collections.get(COLLECTION_NAME)
    protected = set()
    for name in PROTECTED_COLLECTIONS:
        other = bpy.data.collections.get(name)
        if other is not None:
            protected |= set(other.all_objects)

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
            if isinstance(data, bpy.types.Mesh) and data.users == 0:
                bpy.data.meshes.remove(data)

    if collection not in scene.collection.children_recursive:
        scene.collection.children.link(collection)
    return collection


def add_empty(name, matrix, parent, collection, size):
    obj = bpy.data.objects.new(OBJECT_PREFIX + name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = size
    obj[PART_TAG] = name
    collection.objects.link(obj)
    obj.parent = parent
    obj.matrix_world = matrix
    return obj


def orient_faces(verts, faces):
    """Wind all faces so their normals point out of the face (-Y)."""
    total = 0.0
    for f in faces:
        a, b, c = verts[f[0]], verts[f[1]], verts[f[2]]
        total += (b - a).cross(c - a).y
    if total > 0.0:
        # Keep the first vertex so quads split along the same diagonal on both sides.
        faces = [(f[0],) + tuple(reversed(f[1:])) for f in faces]
    return faces


def add_mesh(name, verts, faces, colours, matrix, parent, collection, material, closed=False):
    """Mesh object whose origin / rotation is matrix; verts are given in world space.

    Flat parts face out of the face (-Y); closed shells get outward normals instead.
    """
    inverse = matrix.inverted()
    mesh = bpy.data.meshes.new(OBJECT_PREFIX + name + "_Mesh")
    mesh.from_pydata([tuple(inverse @ v) for v in verts], [], faces if closed else orient_faces(verts, faces))
    mesh.validate()
    if closed:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(mesh)
        bm.free()
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    attribute = mesh.color_attributes.new(SHADE_ATTRIBUTE, "FLOAT_COLOR", "POINT")
    for item, colour in zip(attribute.data, colours):
        item.color = tuple(colour) + (1.0,)
    mesh.color_attributes.active_color = attribute
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(OBJECT_PREFIX + name, mesh)
    obj[PART_TAG] = name
    collection.objects.link(obj)
    obj.parent = parent
    obj.matrix_world = matrix
    return obj


def follow_face(obj, head_obj, offset):
    if not FOLLOW_FACE_SURFACE:
        return
    modifier = obj.modifiers.new("FollowFace", "SHRINKWRAP")
    modifier.target = head_obj
    modifier.wrap_method = "NEAREST_SURFACEPOINT"
    modifier.wrap_mode = "ABOVE_SURFACE"
    modifier.offset = offset


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_brows(layout, collection, material):
    head = layout.head
    verts, faces, colours = brow_mesh(layout)
    brows = {}
    for suffix in (".L", ".R"):
        bx, bz = layout.brow
        if suffix == ".R":
            bx = 2.0 * layout.cx - bx
        place = verts if suffix == ".L" else [layout.mirror(v) for v in verts]
        root = add_empty("Brow_Root" + suffix, head.frame(bx, bz), None, collection, 0.015)
        brow = add_mesh("Brow" + suffix, place, faces, colours, root.matrix_world, root, collection, material)
        follow_face(brow, head.obj, BROW_GAP)
        brows[suffix] = {"Root": root, "Brow": brow}
    return brows


def build_nose(layout, collection, material):
    verts, faces, colours = nose_mesh(layout)
    return add_mesh("Nose", verts, faces, colours, layout.head.frame(layout.cx, layout.nose_z), None, collection, material)


def build_lashes(layout, lines, collection, materials):
    """Upper / lower lash meshes per eye, parented to the eye's upper lid / root so they follow blinks and moves."""
    eyes = layout.eyes
    lashes = {}
    for name, (verts, faces), colour, material, parent_name in (
        ("UpperLashes", upper_lash_mesh(lines), COLOR_LASH, materials["Lash"], "UpperLid"),
        ("LowerLashes", lower_lash_mesh(lines), COLOR_LOWER_LASH, materials["LowerLash"], "Root"),
    ):
        colours = [hex_to_linear(colour)] * len(verts)
        for suffix in (".L", ".R"):
            parent = eyes.parts.get(parent_name + suffix) or eyes.parts["Root" + suffix]
            place = verts if suffix == ".L" else [layout.mirror(v) for v in verts]
            lashes[name + suffix] = add_mesh(name + suffix, place, faces, colours, parent.matrix_world.copy(), parent,
                                             collection, material)
    return lashes


def build_blush(layout, collection, material):
    verts, faces, colours, centre = blush_mesh(layout)
    blush = {}
    for suffix in (".L", ".R"):
        x = centre.x if suffix == ".L" else 2.0 * layout.cx - centre.x
        place = verts if suffix == ".L" else [layout.mirror(v) for v in verts]
        obj = add_mesh("Blush" + suffix, place, faces, colours, layout.head.frame(x, centre.z), None, collection, material)
        follow_face(obj, layout.head.obj, BLUSH_GAP)
        blush[suffix] = obj
    return blush


def build_ears(layout, module, collection, material):
    verts, faces, colours, origin, out = ear_mesh(layout, module)
    ears = {}
    for suffix in (".L", ".R"):
        if suffix == ".L":
            place, root, side = verts, origin, out
        else:
            place = [layout.mirror(v) for v in verts]
            root, side = layout.mirror(origin), Vector((-out.x, out.y, out.z))
        matrix = Matrix.Translation(root) @ side_frame(side)
        ear = add_mesh("Ear" + suffix, place, faces, colours, matrix, None, collection, material, closed=True)
        modifier = ear.modifiers.new("Subdivision", "SUBSURF")
        modifier.levels = modifier.render_levels = EAR_SUBDIV
        ears[suffix] = ear
    return ears


def build_mouth(layout, collection, materials):
    head = layout.head
    root = add_empty("Mouth_Root", head.frame(layout.cx, layout.mouth_centre_z), None, collection, 0.02)
    smile = add_empty("Mouth_Smile", root.matrix_world, root, collection, 0.01)
    objects = {"Root": root, "Smile": smile}
    for name, (verts, faces, colours, layer) in mouth_parts(layout).items():
        obj = add_mesh("Mouth_Smile_" + name, verts, faces, colours, smile.matrix_world, smile, collection, materials[name])
        follow_face(obj, head.obj, MOUTH_GAP + layer * MOUTH_LAYER)
        objects[name] = obj
    return objects


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def mirror_error(points_a, points_b, cx):
    tree = kdtree.KDTree(len(points_b))
    for i, p in enumerate(points_b):
        tree.insert(p, i)
    tree.balance()
    return max(tree.find(Vector((2.0 * cx - p.x, p.y, p.z)))[2] for p in points_a)


def triangle_count(obj):
    _, polys = evaluated_world(obj)
    return sum(len(p) - 2 for p in polys)


def report(layout, brows, nose, mouth, lashes, ears, blush, collection):
    bpy.context.view_layer.update()
    head, eyes = layout.head, layout.eyes
    problems = []

    visible = ([brows[s]["Brow"] for s in (".L", ".R")] + [nose] + [mouth[n] for n in ("Inside", "Teeth", "Tongue", "Line")]
               + list(lashes.values()) + list(blush.values()))
    points = {obj.name: evaluated_world(obj)[0] for obj in visible}
    behind = 0
    for pts in points.values():
        for p in pts:
            face_y = head.front_y(p.x, p.z)
            if face_y is not None and p.y > face_y + 1e-5:
                behind += 1
    if behind:
        problems.append(f"얼굴 표면 안으로 들어간 정점 {behind}개")

    brow_l, brow_r = points[brows[".L"]["Brow"].name], points[brows[".R"]["Brow"].name]
    mouth_pts = [p for n in ("Inside", "Teeth", "Tongue", "Line") for p in points[mouth[n].name]]
    nose_pts = points[nose.name]
    ear_l, ear_r = (evaluated_world(ears[s])[0] for s in (".L", ".R"))
    symmetry = max(mirror_error(brow_l, brow_r, layout.cx), mirror_error(mouth_pts, mouth_pts, layout.cx),
                   mirror_error(nose_pts, nose_pts, layout.cx), mirror_error(ear_l, ear_r, layout.cx),
                   *(mirror_error(points[lashes[n + ".L"].name], points[lashes[n + ".R"].name], layout.cx)
                     for n in ("UpperLashes", "LowerLashes")),
                   mirror_error(points[blush[".L"].name], points[blush[".R"].name], layout.cx))
    if symmetry > SYMMETRY_TOLERANCE:
        problems.append(f"좌우 비대칭 {symmetry:.6f} m")

    lid_pts = [p for obj in eyes.upper_parts(".L") for p in evaluated_world(obj)[0]]
    lid_tree = kdtree.KDTree(len(lid_pts))
    for i, p in enumerate(lid_pts):
        lid_tree.insert(p, i)
    lid_tree.balance()
    brow_clearance = min(lid_tree.find(p)[2] for p in brow_l)
    if brow_clearance < 0.005:
        problems.append("눈썹이 눈꺼풀·속눈썹에 너무 가까움")

    brow_bottom = min(p.z for p in brow_l)
    nose_lift = max(head.front_y(p.x, p.z) - p.y for p in nose_pts if head.front_y(p.x, p.z) is not None)
    nose_bottom = min(p.z for p in nose_pts)
    mouth_top_z = max(p.z for p in points[mouth["Inside"].name])
    mouth_low = min(p.z for p in mouth_pts)
    if mouth_top_z > nose_bottom:
        problems.append("입과 코가 겹침")
    if mouth_low < head.chin_z + 0.01:
        problems.append("입이 턱 끝에 너무 가까움")

    upper_tip = max(p.z for p in points[lashes["UpperLashes.L"].name])
    lower_low = min(p.z for p in points[lashes["LowerLashes.L"].name])
    ear_centre_z = (max(p.z for p in ear_l) + min(p.z for p in ear_l)) / 2.0
    hit = head.bvh.ray_cast(Vector((head.max_x + 1.0, EAR_Y, ear_centre_z)), Vector((-1.0, 0.0, 0.0)))[0]
    ear_out = max(p.x for p in ear_l) - (hit.x if hit is not None else 0.0)

    expected = 2 * 2 + 1 + 6 + 4 + 2 + 2
    count = len(collection.objects)
    if count != expected:
        problems.append(f"오브젝트 수 {count}개 (예상 {expected}개)")
    meshes = [obj for obj in collection.objects if obj.type == "MESH"]
    triangles = {obj.name: triangle_count(obj) for obj in meshes}

    ok = not problems
    result = "결과: 정상" if ok else f"결과: 확인 필요 ({', '.join(problems)})"
    brow_root = brows[".L"]["Root"].matrix_world.translation
    lines = [
        f"기준: 눈 중심 Z {eyes.z:.3f}, 눈 간격 {2.0 * (eyes.left.x - eyes.centre_x):.3f} m, 흰자 너비 {eyes.width:.3f} m, "
        f"위 눈꺼풀 꼭대기 Z {eyes.lid_top:.3f}, 턱 Z {head.chin_z:.3f}",
        f"눈썹: 중심 (왼쪽) X {brow_root.x:+.3f}, Z {brow_root.z:.3f} / 길이 {BROW_LENGTH * 1000:.0f} mm, "
        f"두께 {BROW_THICKNESS * 1000:.1f} mm, 아치 {BROW_ARCH * 1000:.1f} mm",
        f"  눈썹 아래 끝과 눈꺼풀 꼭대기 높이 차 {(brow_bottom - eyes.lid_top) * 1000:.1f} mm, "
        f"눈꺼풀·속눈썹·쌍꺼풀과 최소 거리 {brow_clearance * 1000:.1f} mm",
        f"코: 끝 Z {layout.nose_z:.3f}, 너비 {NOSE_WIDTH * 1000:.0f} mm, 얼굴에서 돌출 {nose_lift * 1000:.1f} mm",
        f"입 (미소): 위 가장자리 Z {layout.mouth_top_z:.3f}, 너비 {MOUTH_WIDTH * 1000:.0f} mm, 벌림 {MOUTH_OPEN * 1000:.0f} mm / "
        f"코 아래 간격 {(nose_bottom - mouth_top_z) * 1000:.1f} mm, 턱 위 간격 {(mouth_low - head.chin_z) * 1000:.1f} mm",
        f"윗속눈썹: 눈마다 {len(UPPER_LASHES)}개 추가 ({min(l for _, l, _, _ in UPPER_LASHES) * 1000:.0f}~"
        f"{max(l for _, l, _, _ in UPPER_LASHES) * 1000:.0f} mm, 바깥쪽이 길고 위로 휨), 끝 최고 Z {upper_tip:.3f} / "
        f"아랫속눈썹: 눈마다 {len(LOWER_LASHES)}개, 끝 최저 Z {lower_low:.3f}",
        f"귀: 높이 {max(p.z for p in ear_l) - min(p.z for p in ear_l):.3f} m (Z {min(p.z for p in ear_l):.3f}~"
        f"{max(p.z for p in ear_l):.3f}), 머리 옆면 밖으로 {ear_out * 1000:.0f} mm, 바깥 끝 X ±{max(p.x for p in ear_l):.3f}",
        f"삼각형 수: 합계 {sum(triangles.values())} (귀 {triangles[ears['.L'].name]}×2, 코 {triangles[nose.name]}, "
        f"입 {sum(triangles[mouth[n].name] for n in ('Inside', 'Teeth', 'Tongue', 'Line'))}, "
        f"눈썹 {triangles[brows['.L']['Brow'].name]}×2, 속눈썹 "
        f"{triangles[lashes['UpperLashes.L'].name] + triangles[lashes['LowerLashes.L'].name]}×2, "
        f"볼터치 {triangles[blush['.L'].name]}×2)",
        f"좌우 대칭 최대 오차: {symmetry:.6f} m",
        f"오브젝트 {count}개 ('{COLLECTION_NAME}' 컬렉션)",
        result,
    ]

    print("\n[MainGirlfriend 얼굴 디테일] 생성 결과")
    for line in lines:
        print("  " + line)

    if not bpy.app.background and bpy.context.window_manager is not None:
        def draw(self, _context):
            for line in lines:
                self.layout.label(text=line)

        bpy.context.window_manager.popup_menu(draw, title="MainGirlfriend 얼굴 디테일", icon="CHECKMARK" if ok else "ERROR")


def main():
    head = Head(find_head())
    eyes = Eyes()
    layout = Layout(head, eyes)
    collection = reset_collection(bpy.context.scene)
    materials = {
        "Brow": shade_material("Brow", 0.85, specular=0.2),
        "Nose": shade_material("Nose", 0.6),
        "Inside": shade_material("MouthInside", 0.7, specular=0.3),
        "Teeth": shade_material("Teeth", 0.35),
        "Tongue": shade_material("Tongue", 0.45, specular=0.4),
        "Line": shade_material("LipLine", 0.8, specular=0.2),
        "Lash": shade_material("Lash", 0.9, specular=0.15),
        "LowerLash": shade_material("LowerLash", 0.9, specular=0.15),
        "Ear": shade_material("Ear", 0.6),
        "Blush": shade_material("Blush", 0.6),
    }
    lines = EyeLines(eyes)
    brows = build_brows(layout, collection, materials["Brow"])
    nose = build_nose(layout, collection, materials["Nose"])
    mouth = build_mouth(layout, collection, materials)
    lashes = build_lashes(layout, lines, collection, materials)
    ears = build_ears(layout, lines.module, collection, materials["Ear"])
    blush = build_blush(layout, collection, materials["Blush"])
    report(layout, brows, nose, mouth, lashes, ears, blush, collection)


if __name__ == "__main__":
    main()
