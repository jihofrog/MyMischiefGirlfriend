"""MainGirlfriend hair blockout: bob with bangs, face-framing side locks and the X hair clip.

Run inside Blender 4.x / 5.x (Scripting workspace > Run Script) after
create_character_blockout.py (and optionally the eye / face detail scripts).

- The outer silhouette is measured on References/Front.png, Side.png and Back.png
  (same scale as the blockout: head top y=16 -> Z 1.65, sole y=337 -> Z 0, 5.14 mm/px).
- Objects (character faces -Y, left side is +X):
    Hair_Main    one low-poly shell: crown, bangs above the eyes, thin side locks in front of the ears,
                 shoulder-length back with strand tips (Solidify + Subdivision modifiers, not applied)
    Hair_Clip_X  white X-shaped clip on the character's left (+X) side, on the hair surface
- The shell is pushed outside the blockout head / neck / torso / arms so the skin never shows through.
- Only the MainGirlfriend_Hair collection is rebuilt on every run, so parts are never duplicated.
  Every other collection (Blockout, Eyes, FaceDetails, Reference_Images) is only read.
- The .blend file is never saved by this script.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


# ===========================================================================
# Silhouette (world metres), measured on the reference sheet
# ===========================================================================

HAIR_TOP = 1.65               # CHARACTER_HEIGHT of the blockout: hair top
# (z, half width X from Back.png, front Y and back Y from Side.png). Front Y below the bangs is
# only used by the side / back columns, so it is a guess that keeps the side locks near the cheeks.
SILHOUETTE = (
    (1.650, 0.000, -0.005, 0.060),
    (1.640, 0.087, -0.019, 0.135),
    (1.614, 0.144, -0.107, 0.197),
    (1.588, 0.167, -0.143, 0.222),
    (1.563, 0.195, -0.168, 0.248),
    (1.537, 0.213, -0.184, 0.269),
    (1.511, 0.239, -0.199, 0.299),
    (1.486, 0.257, -0.209, 0.310),
    (1.460, 0.262, -0.225, 0.320),
    (1.434, 0.272, -0.232, 0.325),
    (1.408, 0.278, -0.236, 0.330),
    (1.383, 0.283, -0.236, 0.335),
    (1.357, 0.283, -0.232, 0.335),
    (1.306, 0.286, -0.215, 0.335),
    (1.254, 0.290, -0.200, 0.340),
    (1.203, 0.305, -0.200, 0.346),
    (1.151, 0.315, -0.200, 0.355),
    (1.100, 0.320, -0.200, 0.361),
    (1.049, 0.305, -0.200, 0.341),
    (0.990, 0.270, -0.200, 0.300),
)
HAIR_ROUNDNESS = 2.4          # cross-section superellipse exponent; 2 = ellipse, higher = fuller corners

# Lower edge of every column, by angle around the head (0 = face centre, 90 = ear, 180 = back centre).
HAIR_END = (
    (0.0, 1.380),             # bangs end above the eyes (upper lid top Z 1.338)
    (38.0, 1.380),
    (50.0, 1.250),            # side locks in front of the ears; they hide the ears in the front view (ear bottom Z 1.21)
    (70.0, 1.195),
    (84.0, 1.190),
    (91.0, 1.315),            # gap above / behind the ear so the ear shows in the side view (ear top Z 1.30)
    (98.0, 1.315),
    (108.0, 1.050),           # shoulder-length back
    (180.0, 1.000),
)
EAR_GAP_ANGLES = (86.0, 102.0)  # columns without strand tips (the ear opening)
BANG_CLUMP = (-8.0, 8.0, 0.035)   # (angle, width, extra drop) of the centre clump; slightly to the character's right
STRAND_TIP = 0.03             # every other column ends lower, giving pointed strand tips
STRAND_GROOVE = 0.016         # radius dip on every other column below the crown (soft strand ridges)
GROOVE_TOP = 1.52             # grooves fade in below this height

# Face-framing parts hug the face instead of following the wide outer silhouette.
HUG_TOP = 1.43                # hugging fades in below this height
HUG_FULL = 1.32
HUG_ANGLES = (30.0, 48.0, 60.0, 84.0)  # fade in / full / full / fade out (degrees); the locks open out in front of the ears
HUG_GAP = 0.016               # outer hair surface distance from the face when hugging

HAIR_GAP = 0.016              # minimum outer-surface distance from the body (> HAIR_THICKNESS)
HAIR_THICKNESS = 0.010        # Solidify thickness, inward
COLUMNS = 40                  # around the head (even, mirrored)
DOME_ROWS = (1.645, 1.632, 1.612, 1.586, 1.556, 1.522, 1.486, 1.450)
LOWER_ROWS = 8                # from the last dome row down to the column end
SUBDIV_LEVELS = 1

# X clip (Front.png: X +0.21, Z 1.42 / Side.png: Y -0.01, Z 1.43; bars ~8 cm)
CLIP_Y = -0.06
CLIP_Z = 1.43
CLIP_BAR_LENGTH = 0.075
CLIP_BAR_WIDTH = 0.013
CLIP_BAR_THICKNESS = 0.006
CLIP_ANGLE_DEG = 38.0         # each bar's angle from horizontal (side view)
CLIP_LIFT = 0.003             # gap between the clip back and the hair surface

COLOR_HAIR = "7B4A46"
COLOR_CLIP = "F6F3EE"


# ===========================================================================
# Output
# ===========================================================================

COLLECTION_NAME = "MainGirlfriend_Hair"
BLOCKOUT_COLLECTION = "MainGirlfriend_Blockout"
PROTECTED_COLLECTIONS = ("Reference_Images", "MainGirlfriend_Blockout", "MainGirlfriend_Eyes",
                         "MainGirlfriend_FaceDetails")
BLOCKOUT_PART_TAG = "mg_blockout_part"
COLLIDER_PARTS = ("Head", "Neck", "Torso", "Arm.L", "Arm.R")
COLLIDER_OBJECTS = ("Face_Ear.L", "Face_Ear.R")  # optional (create_character_face_details.py)
OBJECT_PREFIX = "Hair_"
MATERIAL_PREFIX = "MG_"
PART_TAG = "mg_hair_part"
SYMMETRY_TOLERANCE = 1e-4


# ===========================================================================

def smoothstep(edge0, edge1, x):
    t = min(1.0, max(0.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def hex_to_linear(value):
    def channel(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return tuple(channel(int(value[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


def interpolate(table, x):
    """Piecewise-linear lookup; returns the row tuple without its key."""
    if x >= table[0][0]:
        return table[0][1:]
    for a, b in zip(table, table[1:]):
        if b[0] <= x <= a[0]:
            t = (x - a[0]) / (b[0] - a[0])
            return tuple(p + (q - p) * t for p, q in zip(a[1:], b[1:]))
    return table[-1][1:]


def by_angle(table, angle):
    for (a0, v0), (a1, v1) in zip(table, table[1:]):
        if a0 <= angle <= a1:
            return v0 + (v1 - v0) * smoothstep(a0, a1, angle)
    return table[-1][1]


def signed_pow(value, exponent):
    return math.copysign(abs(value) ** exponent, value)


# ---------------------------------------------------------------------------
# Body (read only)
# ---------------------------------------------------------------------------

def evaluated_world(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    verts = [obj.matrix_world @ v.co for v in mesh.vertices]
    polys = [tuple(p.vertices) for p in mesh.polygons]
    evaluated.to_mesh_clear()
    return verts, polys


def blockout_parts():
    collection = bpy.data.collections.get(BLOCKOUT_COLLECTION)
    if collection is None:
        raise RuntimeError(f"'{BLOCKOUT_COLLECTION}' 컬렉션이 없습니다. create_character_blockout.py를 먼저 실행하세요.")
    parts = {obj.get(BLOCKOUT_PART_TAG): obj for obj in collection.all_objects if obj.type == "MESH"}
    if "Head" not in parts:
        raise RuntimeError("블록아웃 머리(Blockout_Head)를 찾을 수 없습니다.")
    return parts


class Body:
    def __init__(self, parts):
        self.head_verts, self.head_polys = evaluated_world(parts["Head"])
        self.head = BVHTree.FromPolygons(self.head_verts, self.head_polys)
        self.colliders = []
        for name in COLLIDER_PARTS:
            if name in parts:
                verts, polys = evaluated_world(parts[name])
                self.colliders.append(BVHTree.FromPolygons(verts, polys))
        for name in COLLIDER_OBJECTS:
            obj = bpy.data.objects.get(name)
            if obj is not None and obj.type == "MESH":
                verts, polys = evaluated_world(obj)
                self.colliders.append(BVHTree.FromPolygons(verts, polys))
        ys = [v.y for v in self.head_verts]
        self.centre_y = (min(ys) + max(ys)) / 2.0
        self.top_z = max(v.z for v in self.head_verts)
        self.chin_z = min(v.z for v in self.head_verts)

    def head_radius(self, z, direction):
        """Horizontal distance from the head axis to the head surface along direction (None above / below)."""
        origin = Vector((0.0, self.centre_y, z))
        hit = self.head.ray_cast(origin, direction, 1.0)[0]
        return None if hit is None else (hit - origin).length

    def push_out(self, p, gap):
        for _ in range(3):
            moved = False
            for tree in self.colliders:
                nearest, normal, _, distance = tree.find_nearest(p, gap * 4.0)
                if nearest is None:
                    continue
                offset = p - nearest
                outward = offset.dot(normal)
                if outward < gap:
                    p = nearest + normal * gap
                    moved = True
            if not moved:
                break
        return p


# ---------------------------------------------------------------------------
# Hair shell
# ---------------------------------------------------------------------------

def column_angle(j):
    """Signed angle in degrees; positive toward the character's left (+X)."""
    angle = 360.0 * j / COLUMNS
    return angle - 360.0 if angle > 180.0 else angle


def column_end(j):
    angle = column_angle(j)
    a = abs(angle)
    end = by_angle(HAIR_END, a)
    centre, width, drop = BANG_CLUMP
    end -= drop * math.exp(-((angle - centre) / width) ** 2) * (1.0 - smoothstep(30.0, 40.0, a))
    if j % 2 == 0 and not EAR_GAP_ANGLES[0] < a < EAR_GAP_ANGLES[1]:
        end -= STRAND_TIP
    return end


def silhouette_point(z, angle_deg, groove):
    half_w, front_y, back_y = interpolate(SILHOUETTE, z)
    phi = math.radians(angle_deg)
    e = 2.0 / HAIR_ROUNDNESS
    s, c = math.sin(phi), math.cos(phi)
    centre_y = BODY.centre_y
    depth = (centre_y - front_y) if c >= 0.0 else (back_y - centre_y)
    point = Vector((half_w * signed_pow(s, e), centre_y - depth * signed_pow(c, e), z))
    if groove:
        dip = STRAND_GROOVE * (1.0 - smoothstep(GROOVE_TOP - 0.08, GROOVE_TOP, z))
        axis = Vector((0.0, centre_y, z))
        point = axis + (point - axis) * (1.0 - dip / max(0.05, (point - axis).length))
    return point


def hug(point, angle_deg):
    a = abs(angle_deg)
    f0, f1, f2, f3 = HUG_ANGLES
    weight = smoothstep(HUG_TOP, HUG_FULL, point.z) * smoothstep(f0, f1, a) * (1.0 - smoothstep(f2, f3, a))
    if weight <= 0.0:
        return point
    axis = Vector((0.0, BODY.centre_y, point.z))
    direction = point - axis
    if direction.length < 1e-6:
        return point
    direction.normalize()
    radius = BODY.head_radius(point.z, direction)
    if radius is None:
        return point
    current = (point - axis).length
    target = radius + HUG_GAP
    return axis + direction * (current + (target - current) * weight) if target < current else point


def build_shell():
    rows = []
    for j in range(COLUMNS):
        angle = column_angle(j)
        end = column_end(j)
        dome_end = DOME_ROWS[-1]
        zs = list(DOME_ROWS) + [dome_end + (end - dome_end) * (i + 1) / LOWER_ROWS for i in range(LOWER_ROWS)]
        column = []
        for z in zs:
            p = silhouette_point(z, angle, groove=(j % 2 == 1))
            p = hug(p, angle)
            column.append(BODY.push_out(p, HAIR_GAP))
        rows.append(column)

    count = len(rows[0])
    verts = [Vector((0.0, (silhouette_point(DOME_ROWS[0], 0.0, False).y
                           + silhouette_point(DOME_ROWS[0], 180.0, False).y) / 2.0, HAIR_TOP))]
    for i in range(count):
        for j in range(COLUMNS):
            verts.append(rows[j][i])

    def index(i, j):
        return 1 + i * COLUMNS + (j % COLUMNS)

    faces = [(0, index(0, j), index(0, j + 1)) for j in range(COLUMNS)]
    for i in range(count - 1):
        for j in range(COLUMNS):
            faces.append((index(i, j), index(i + 1, j), index(i + 1, j + 1), index(i, j + 1)))
    return mirror_fix(verts), faces


def mirror_fix(verts):
    """Average each vertex with its mirror (push_out can differ by float noise between sides)."""
    fixed = list(verts)
    count = (len(verts) - 1) // COLUMNS
    for i in range(count):
        for j in range(1, COLUMNS // 2):
            a, b = 1 + i * COLUMNS + j, 1 + i * COLUMNS + (COLUMNS - j)
            pa, pb = verts[a], verts[b]
            avg = Vector(((pa.x - pb.x) / 2.0, (pa.y + pb.y) / 2.0, (pa.z + pb.z) / 2.0))
            fixed[a], fixed[b] = avg, Vector((-avg.x, avg.y, avg.z))
        for j in (0, COLUMNS // 2):
            k = 1 + i * COLUMNS + j
            fixed[k] = Vector((0.0, verts[k].y, verts[k].z))
    fixed[0] = Vector((0.0, verts[0].y, verts[0].z))
    return fixed


# ---------------------------------------------------------------------------
# X clip
# ---------------------------------------------------------------------------

def clip_frame(shell_tree):
    hit, normal, _, _ = shell_tree.ray_cast(Vector((1.0, CLIP_Y, CLIP_Z)), Vector((-1.0, 0.0, 0.0)))
    if hit is None:
        raise RuntimeError("머리카락 표면에서 X 핀 위치를 찾지 못했습니다.")
    if normal.x < 0.0:
        normal = -normal
    up = (Vector((0.0, 0.0, 1.0)) - normal * normal.z).normalized()
    side = up.cross(normal).normalized()
    matrix = Matrix((
        (normal.x, side.x, up.x, 0.0),
        (normal.y, side.y, up.y, 0.0),
        (normal.z, side.z, up.z, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    matrix.translation = hit + normal * (CLIP_LIFT + CLIP_BAR_THICKNESS / 2.0)
    return matrix


def clip_mesh():
    """Two crossed flat bars in local space: X = out of the hair, Y / Z = the hair surface plane."""
    verts, faces = [], []
    hx, hl, hw = CLIP_BAR_THICKNESS / 2.0, CLIP_BAR_LENGTH / 2.0, CLIP_BAR_WIDTH / 2.0
    box = ((0, 1, 3, 2), (4, 6, 7, 5), (0, 2, 6, 4), (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6))
    for sign in (1.0, -1.0):
        a = math.radians(CLIP_ANGLE_DEG) * sign
        along = Vector((0.0, math.cos(a), math.sin(a)))
        across = Vector((0.0, -math.sin(a), math.cos(a)))
        base = len(verts)
        for dx in (-hx, hx):
            for dl in (-hl, hl):
                for dw in (-hw, hw):
                    verts.append(Vector((dx, 0.0, 0.0)) + along * dl + across * dw)
        # Second bar sits a hair above the first so the two never z-fight.
        if sign < 0.0:
            verts[base:] = [v + Vector((CLIP_BAR_THICKNESS * 0.3, 0.0, 0.0)) for v in verts[base:]]
        faces.extend(tuple(base + i for i in f) for f in box)
    return verts, faces


# ---------------------------------------------------------------------------
# Scene helpers
# ---------------------------------------------------------------------------

def material(name, colour, roughness, specular=0.5):
    mat = bpy.data.materials.get(MATERIAL_PREFIX + name) or bpy.data.materials.new(MATERIAL_PREFIX + name)
    rgb = hex_to_linear(colour)
    mat.diffuse_color = rgb + (1.0,)
    mat.roughness = roughness
    if mat.node_tree is None and hasattr(mat, "use_nodes"):
        mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location, output.location = (0, 0), (300, 0)
    bsdf.inputs["Base Color"].default_value = rgb + (1.0,)
    bsdf.inputs["Roughness"].default_value = roughness
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat


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


def add_mesh(name, verts, faces, matrix, collection, mat, outward_from=None):
    """verts in world space. Open shells point their normals away from outward_from(point);
    closed meshes (outward_from None) get outward normals."""
    inverse = matrix.inverted()
    mesh = bpy.data.meshes.new(OBJECT_PREFIX + name + "_Mesh")
    mesh.from_pydata([tuple(inverse @ v) for v in verts], [], faces)
    mesh.validate()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    if outward_from is None:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    else:
        world = [matrix @ f.calc_center_median() for f in bm.faces]
        flip = sum((matrix.to_3x3() @ f.normal).dot(c - outward_from(c)) for f, c in zip(bm.faces, world)) < 0.0
        if flip:
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(OBJECT_PREFIX + name, mesh)
    obj[PART_TAG] = name
    collection.objects.link(obj)
    obj.matrix_world = matrix
    return obj


def add_modifiers(obj, thickness, levels):
    if thickness:
        solidify = obj.modifiers.new("Thickness", "SOLIDIFY")
        solidify.thickness = thickness
        solidify.offset = -1.0
        solidify.use_even_offset = True
        solidify.use_rim = True
    if levels:
        subsurf = obj.modifiers.new("Subdivision", "SUBSURF")
        subsurf.levels = levels
        subsurf.render_levels = levels


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def mirror_error(points):
    tree_points = sorted((round(p.y, 5), round(p.z, 5), round(p.x, 5)) for p in points)
    mirrored = sorted((round(p.y, 5), round(p.z, 5), round(-p.x, 5)) for p in points)
    return max(abs(a[2] - b[2]) + abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(tree_points, mirrored))


def triangle_count(obj):
    _, polys = evaluated_world(obj)
    return sum(len(p) - 2 for p in polys)


def report(shell, clip, shell_verts, collection):
    bpy.context.view_layer.update()
    problems = []
    outer = shell_verts

    gaps = []
    for p in outer:
        nearest, normal, _, _ = BODY.head.find_nearest(p)
        gaps.append((p - nearest).dot(normal))
    inside = sum(1 for g in gaps if g < HAIR_THICKNESS)
    if inside:
        problems.append(f"머리 표면과 두께보다 가까운 정점 {inside}개")

    evaluated = evaluated_world(shell)[0]
    symmetry = mirror_error(outer)
    if symmetry > SYMMETRY_TOLERANCE:
        problems.append(f"좌우 비대칭 {symmetry:.6f} m")

    # Columns in front of the eyes only; the centre clump between the eyes may hang lower.
    front_cols = [column_end(j) for j in range(COLUMNS) if 15.0 < abs(column_angle(j)) < 38.0]
    eye_lid_top = None
    eyes = bpy.data.collections.get("MainGirlfriend_Eyes")
    if eyes:
        lids = [o for o in eyes.all_objects if o.type == "MESH" and "UpperLid" in o.name]
        if lids:
            eye_lid_top = max(p.z for o in lids for p in evaluated_world(o)[0])
            if min(front_cols) < eye_lid_top:
                problems.append("앞머리가 눈꺼풀을 가림")

    count = len(collection.objects)
    if count != 2:
        problems.append(f"오브젝트 수 {count}개 (예상 2개)")
    tris = {obj.name: triangle_count(obj) for obj in (shell, clip)}

    ok = not problems
    result = "결과: 정상" if ok else f"결과: 확인 필요 ({', '.join(problems)})"
    xs = [p.x for p in evaluated]
    ys = [p.y for p in evaluated]
    zs = [p.z for p in evaluated]
    back_end = min(column_end(j) for j in range(COLUMNS) if abs(column_angle(j)) > 110.0)
    lock_end = min(column_end(j) for j in range(COLUMNS) if 48.0 < abs(column_angle(j)) < 72.0)
    clip_pos = clip.matrix_world.translation
    lines = [
        f"머리카락 범위: X {min(xs):+.3f} .. {max(xs):+.3f} (너비 {max(xs) - min(xs):.3f} m), "
        f"Y {min(ys):+.3f} .. {max(ys):+.3f}, Z {min(zs):.3f} .. {max(zs):.3f}",
        f"앞머리 끝 Z {min(front_cols):.3f} ~ {max(front_cols):.3f}"
        + (f" (위 눈꺼풀 꼭대기 Z {eye_lid_top:.3f})" if eye_lid_top else ""),
        f"옆머리(귀 앞) 끝 Z {lock_end:.3f} / 뒷머리 끝 Z {back_end:.3f}",
        f"머리 표면과의 간격: 최소 {min(gaps) * 1000:.1f} mm, 두께 {HAIR_THICKNESS * 1000:.0f} mm",
        f"X 핀: 위치 X {clip_pos.x:+.3f}, Y {clip_pos.y:+.3f}, Z {clip_pos.z:.3f} (캐릭터 왼쪽)",
        f"삼각형 수: 합계 {sum(tris.values())} (머리카락 {tris[shell.name]}, X 핀 {tris[clip.name]})",
        f"좌우 대칭 최대 오차: {symmetry:.6f} m",
        f"오브젝트 {count}개 ('{COLLECTION_NAME}' 컬렉션)",
        result,
    ]

    print("\n[MainGirlfriend 머리카락] 생성 결과")
    for line in lines:
        print("  " + line)

    if not bpy.app.background and bpy.context.window_manager is not None:
        def draw(self, _context):
            for line in lines:
                self.layout.label(text=line)

        bpy.context.window_manager.popup_menu(draw, title="MainGirlfriend 머리카락", icon="CHECKMARK" if ok else "ERROR")


# ---------------------------------------------------------------------------

BODY = None


def main():
    global BODY
    BODY = Body(blockout_parts())
    collection = reset_collection(bpy.context.scene)
    hair_mat = material("Hair", COLOR_HAIR, 0.45, specular=0.35)
    clip_mat = material("HairClip", COLOR_CLIP, 0.3)

    verts, faces = build_shell()
    axis_of = lambda c: Vector((0.0, BODY.centre_y, min(c.z, HAIR_TOP - 0.12)))
    shell = add_mesh("Main", verts, faces, Matrix.Translation((0.0, BODY.centre_y, BODY.top_z)),
                     collection, hair_mat, axis_of)
    add_modifiers(shell, HAIR_THICKNESS, SUBDIV_LEVELS)

    shell_tree = BVHTree.FromPolygons(verts, faces)
    frame = clip_frame(shell_tree)
    clip_verts, clip_faces = clip_mesh()
    clip = add_mesh("Clip_X", [frame @ v for v in clip_verts], clip_faces, frame, collection, clip_mat)
    add_modifiers(clip, 0.0, 1)

    report(shell, clip, verts, collection)


if __name__ == "__main__":
    main()
