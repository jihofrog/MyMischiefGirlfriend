"""Read-only check of the MainGirlfriend blockout head against References/Front.png and Side.png.

Run inside Blender 4.x / 5.x (Scripting > Text > Open > Run Script) after
create_character_blockout.py has built the MainGirlfriend_Blockout collection.

Output labels:
    [MODEL]        measured on the evaluated (subdivided) blockout meshes
    [IMAGE]        estimated from reference image pixels (skin colour / background / dark socks),
                   mapped to world space through the REF_Front / REF_Side empties as they are placed
    [NOT MEASURED] hidden by hair or clothing in the sheet; compare by eye

Nothing is created, modified or saved: meshes, reference empties and the .blend stay as they are.
"""

import hashlib
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


BLOCKOUT_COLLECTION = "MainGirlfriend_Blockout"
PART_TAG = "mg_blockout_part"
REFERENCE_TAG = "mmg_reference_view"
PROPORTIONS_FILE = "character_proportions_v1.json"
BLOCKOUT_SCRIPT = "create_character_blockout.py"

SLICE_HALF_THICKNESS = 0.006   # metres, mesh slice used for "at height Z"
PROFILE_STEP = 0.02            # metres between side-profile rows
FRONT_FACE_LIMIT_X = 0.18      # ignore skin further out than this (ears, hands)
CHIN_GAP = 0.008               # a skin gap this tall ends the face when scanning down
BACKGROUND_THRESHOLD = 60      # 0-255 summed RGB difference from the border colour
CHEST_BAND = (0.93, 0.99)      # world Z band of the bust, for the face-vs-chest comparison

# Side alignment: centreline (middle of front and back edge) per region, image vs model.
# Shoulders cannot be used directly (hair covers the back), so the chest/waist stands in for them.
# (world Z band, image mask, model part group)
ALIGN_GROUPS = {
    "가슴·허리": ((0.86, 0.98), "foreground", "torso"),
    "골반 (치마)": ((0.69, 0.78), "navy", "pelvis"),
    "다리 (양말·부츠)": ((0.15, 0.50), "dark", "legs"),
}
ALIGN_STEP = 0.01              # metres between sampled rows
ALIGN_SLICE = 0.012            # half thickness of the model slice for limbs

UP = Vector((0.0, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Mesh helpers
# ---------------------------------------------------------------------------

def world_mesh(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    matrix = np.array(evaluated.matrix_world, dtype=np.float64)
    verts = co.reshape(-1, 3).astype(np.float64) @ matrix[:3, :3].T + matrix[:3, 3]
    polygons = [tuple(p.vertices) for p in mesh.polygons]
    evaluated.to_mesh_clear()
    return verts, polygons


def bvh(verts, polygons):
    return BVHTree.FromPolygons([Vector(v) for v in verts], polygons)


def mesh_slice(verts, z):
    return verts[np.abs(verts[:, 2] - z) < SLICE_HALF_THICKNESS]


def blockout_parts():
    collection = bpy.data.collections.get(BLOCKOUT_COLLECTION)
    if collection is None:
        return {}
    return {obj[PART_TAG]: obj for obj in collection.objects if PART_TAG in obj and obj.type == "MESH"}


# ---------------------------------------------------------------------------
# Model measurements
# ---------------------------------------------------------------------------

def measure_model(parts, depsgraph):
    head_v, head_p = world_mesh(parts["Head"], depsgraph)
    neck_v, _ = world_mesh(parts["Neck"], depsgraph)
    torso_v, torso_p = world_mesh(parts["Torso"], depsgraph)

    chin_z = head_v[:, 2].min()
    top_z = head_v[:, 2].max()
    widest = head_v[np.argmax(np.abs(head_v[:, 0]))]
    front = head_v[np.argmin(head_v[:, 1])]
    back = head_v[np.argmax(head_v[:, 1])]
    chin_band = head_v[head_v[:, 2] < chin_z + 0.003]
    chin_front = head_v[head_v[:, 2] < chin_z + 0.01][:, 1].min()

    m = {
        "head": head_v,
        "chin_z": chin_z,
        "top_z": top_z,
        "height": top_z - chin_z,
        "width": head_v[:, 0].max() - head_v[:, 0].min(),
        "widest_z": widest[2],
        "depth": head_v[:, 1].max() - head_v[:, 1].min(),
        "front_y": front[1],
        "front_z": front[2],
        "back_y": back[1],
        "back_z": back[2],
        "centre_y": (head_v[:, 1].max() + head_v[:, 1].min()) / 2.0,
        "chin_y": chin_band[:, 1].mean(),
        "chin_front_y": chin_front,
    }

    # Neck connection, measured on the neck ring just under the chin.
    ring = neck_v[np.abs(neck_v[:, 2] - (chin_z - 0.015)) < 0.01]
    if len(ring) == 0:
        ring = neck_v
    cx, cy = ring[:, 0].mean(), ring[:, 1].mean()
    m["neck_bottom_z"] = neck_v[:, 2].min()
    m["neck_top_z"] = neck_v[:, 2].max()
    m["neck_centre"] = (cx, cy)
    m["neck_radius_front"] = cy - ring[:, 1].min()
    m["neck_radius_back"] = ring[:, 1].max() - cy
    m["neck_radius_side"] = ring[:, 0].max() - cx
    m["neck_back_y"] = ring[:, 1].max()

    head_tree = bvh(head_v, head_p)
    torso_tree = bvh(torso_v, torso_p)
    axis_hit = head_tree.ray_cast(Vector((cx, cy, 0.0)), UP)[0]
    torso_hit = torso_tree.ray_cast(Vector((cx, cy, top_z + 1.0)), -UP)[0]
    m["neck_entry_z"] = axis_hit.z if axis_hit else None
    m["torso_top_on_neck_axis"] = torso_hit.z if torso_hit else None

    exposed = {}
    lines = {
        "front": (cx, cy - m["neck_radius_front"] * 0.95),
        "side": (cx + m["neck_radius_side"] * 0.95, cy),
        "back": (cx, cy + m["neck_radius_back"] * 0.95),
    }
    for name, (x, y) in lines.items():
        h = head_tree.ray_cast(Vector((x, y, 0.0)), UP)[0]
        t = torso_tree.ray_cast(Vector((x, y, top_z + 1.0)), -UP)[0]
        if h and t:
            exposed[name] = max(0.0, h.z - t.z)
    m["neck_exposed"] = exposed

    m["torso_back_y"] = torso_v[:, 1].max()
    chest = torso_v[(torso_v[:, 2] > CHEST_BAND[0]) & (torso_v[:, 2] < CHEST_BAND[1])]
    m["chest_front_y"] = chest[:, 1].min() if len(chest) else None

    def group(*names):
        verts = [world_mesh(parts[n], depsgraph)[0] for n in names if n in parts]
        return np.concatenate(verts) if verts else None

    m["groups"] = {
        "torso": np.concatenate([torso_v, neck_v]),
        "pelvis": group("Pelvis"),
        "legs": group("Leg.L"),
    }
    m["centres"] = {
        name: None if verts is None else (verts[:, 1].min() + verts[:, 1].max()) / 2.0
        for name, verts in m["groups"].items()
    }
    return m


def model_half_width(m, z):
    s = mesh_slice(m["head"], z)
    return np.abs(s[:, 0]).max() if len(s) else None


def model_front_y(m, z):
    s = mesh_slice(m["head"], z)
    return s[:, 1].min() if len(s) else None


def model_back_y(m, z):
    s = mesh_slice(m["head"], z)
    return s[:, 1].max() if len(s) else None


# ---------------------------------------------------------------------------
# Reference image sampling
# ---------------------------------------------------------------------------

def find_reference(view):
    for obj in bpy.data.objects:
        if obj.get(REFERENCE_TAG) == view:
            return obj
    return bpy.data.objects.get(f"REF_{view}")


class ReferenceImage:
    """Pixels of an image empty plus the world position of every pixel (row 0 = bottom)."""

    def __init__(self, obj, horizontal_axis):
        image = obj.data
        width, height = image.size
        if width == 0 or height == 0:
            raise RuntimeError(f"{obj.name}: 이미지 '{image.name}'의 픽셀이 없습니다 (파일이 없나요?)")

        channels = image.channels
        buffer = np.empty(width * height * channels, dtype=np.float32)
        image.pixels.foreach_get(buffer)
        self.rgb = buffer.reshape(height, width, channels)[:, :, :3] * 255.0
        self.width, self.height = width, height

        size = obj.empty_display_size
        ax, ay = (1.0, height / width) if width >= height else (width / height, 1.0)
        ofs = obj.empty_image_offset
        matrix = obj.matrix_world

        def world(c, r):
            u, v = (c + 0.5) / width, (r + 0.5) / height
            return matrix @ Vector(((ofs[0] + u) * size * ax, (ofs[1] + v) * size * ay, 0.0))

        p00 = world(0, 0)
        du, dv = world(1, 0) - p00, world(0, 1) - p00
        axis = {"X": 0, "Y": 1}[horizontal_axis]
        self.axis_name = horizontal_axis
        self.h0, self.dh = p00[axis], du[axis]
        self.z0, self.dz = p00.z, dv.z
        self.pixel_size = du.length
        self.alignment_ok = abs(du[axis]) > 0.99 * du.length and abs(dv.z) > 0.99 * dv.length

        border = np.concatenate([self.rgb[0], self.rgb[-1], self.rgb[:, 0], self.rgb[:, -1]])
        background = np.median(border, axis=0)
        r, g, b = self.rgb[..., 0], self.rgb[..., 1], self.rgb[..., 2]
        self.foreground = np.abs(self.rgb - background).sum(axis=2) > BACKGROUND_THRESHOLD
        self.skin = (
            (r > 215) & (g > 165) & (g < 225) & (b > 140) & (b < 215) & (r - b > 18) & (r - g > 8)
        )
        self.dark = self.rgb.mean(axis=2) < 55
        self.navy = (b > r + 10) & (self.rgb.mean(axis=2) < 150)

    def row(self, z):
        r = int(round((z - self.z0) / self.dz))
        return r if 0 <= r < self.height else None

    def z_of(self, r):
        return self.z0 + r * self.dz

    def coords(self):
        return self.h0 + np.arange(self.width) * self.dh

    def find_chin(self, start_z, column_mask):
        """Scan down from start_z; the chin is the last skin row before a gap of CHIN_GAP."""
        r = self.row(start_z)
        if r is None:
            return None
        gap_rows = max(1, int(math.ceil(CHIN_GAP / abs(self.dz))))
        last_skin, gap = None, 0
        step = -1 if self.dz > 0 else 1
        while 0 <= r < self.height:
            if (self.skin[r] & column_mask).any():
                last_skin, gap = r, 0
            elif last_skin is not None:
                gap += 1
                if gap >= gap_rows:
                    break
            r += step
        return None if last_skin is None else self.z_of(last_skin) - abs(self.dz) / 2.0


def measure_side_image(side, m):
    coords = side.coords()
    front_half = coords < m["centre_y"]
    result = {"chin_z": side.find_chin(m["chin_z"] + 0.08, front_half)}

    # Front/back offset of the whole image: centreline differences per body region.
    align = {}
    for name, ((z_lo, z_hi), mask_name, group) in ALIGN_GROUPS.items():
        mask = getattr(side, mask_name)
        verts = m["groups"].get(group)
        diffs = []
        z = z_lo
        while verts is not None and z <= z_hi:
            r = side.row(z)
            cols = coords[mask[r]] if r is not None else []
            band = verts[np.abs(verts[:, 2] - z) < ALIGN_SLICE]
            if len(cols) > 2 and len(band):
                image_mid = (cols.min() + cols.max()) / 2.0
                model_mid = (band[:, 1].min() + band[:, 1].max()) / 2.0
                diffs.append(image_mid - model_mid)
            z += ALIGN_STEP
        align[name] = (float(np.median(diffs)), len(diffs)) if diffs else (None, 0)
    result["align"] = align

    def band_edges(band, mask):
        lo, hi = [], []
        for r in range(side.height):
            if band[0] < side.z_of(r) < band[1]:
                cols = coords[mask[r]]
                if len(cols):
                    lo.append(cols.min())
                    hi.append(cols.max())
        return (float(np.median(lo)), float(np.median(hi))) if lo else (None, None)

    result["chest_front_y"] = band_edges(CHEST_BAND, side.foreground)[0]

    def front_skin(z):
        r = side.row(z)
        if r is None:
            return None
        cols = coords[side.skin[r] & front_half]
        return cols.min() if len(cols) else None

    def silhouette_back(z):
        r = side.row(z)
        if r is None:
            return None
        cols = coords[side.foreground[r]]
        return cols.max() if len(cols) else None

    result["front_skin"] = front_skin
    result["silhouette_back"] = silhouette_back
    return result


def measure_front_image(front, m):
    coords = front.coords()
    centre = np.abs(coords) < 0.06
    result = {"chin_z": front.find_chin(m["chin_z"] + 0.08, centre)}
    face_cols = np.abs(coords) < FRONT_FACE_LIMIT_X

    def face_edges(z):
        r = front.row(z)
        if r is None:
            return None
        cols = coords[front.skin[r] & face_cols]
        return (cols.min(), cols.max()) if len(cols) else None

    def silhouette_half_width(z):
        r = front.row(z)
        if r is None:
            return None
        cols = coords[front.foreground[r]]
        return (cols.max() - cols.min()) / 2.0 if len(cols) else None

    result["face_edges"] = face_edges
    result["silhouette_half_width"] = silhouette_half_width
    return result


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def fmt(value, signed=False, digits=3):
    if value is None:
        return "  n/a"
    return f"{value:+.{digits}f}" if signed else f"{value:.{digits}f}"


def diff(a, b):
    return None if a is None or b is None else a - b


def proportions_info(lines):
    candidates = []
    try:
        candidates.append(Path(__file__).resolve().parent)
    except NameError:
        pass
    if bpy.data.filepath:
        candidates.append(Path(bpy.data.filepath).resolve().parent)
    for text in bpy.data.texts:
        if text.filepath:
            candidates.append(Path(bpy.path.abspath(text.filepath)).resolve().parent)

    for base in candidates:
        path = base / PROPORTIONS_FILE
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            main = next(v for k, v in data["proportions"].items() if k.startswith("Main proportions"))
            lines.append(f"[JSON] {PROPORTIONS_FILE} ({data['version']}, 저장 시각 {data['exported_at']})")
            lines.append(
                "  HEAD_HEIGHT {HEAD_HEIGHT} / HEAD_WIDTH {HEAD_WIDTH} / HEAD_DEPTH {HEAD_DEPTH}".format(**main)
            )
            script = base / BLOCKOUT_SCRIPT
            if script.is_file():
                current = hashlib.sha256(script.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
                state = "동일함" if current == data["source_sha256"] else "이후 변경됨"
                lines.append(f"  {BLOCKOUT_SCRIPT}: {data['version']} 저장 시점과 {state}")
            return data
    lines.append(f"[JSON] {PROPORTIONS_FILE} 없음 (export_character_proportions.py를 실행하세요)")
    return None


CENTRE_NAMES = {"torso": "몸통", "pelvis": "골반", "legs": "다리"}
NECK_LINE_NAMES = {"front": "앞", "side": "옆", "back": "뒤"}


def build_report():
    lines = []
    parts = blockout_parts()
    missing = [name for name in ("Head", "Neck", "Torso") if name not in parts]
    if missing:
        return [f"오류: {BLOCKOUT_COLLECTION}에 {', '.join(missing)} 부위가 없습니다. {BLOCKOUT_SCRIPT}를 먼저 실행하세요."]

    data = proportions_info(lines)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    m = measure_model(parts, depsgraph)

    lines += [
        "",
        "== 머리 정면 폭 [모델]",
        f"  너비 {fmt(m['width'])} m (가장 넓은 높이 Z {fmt(m['widest_z'])}), 높이 {fmt(m['height'])} m",
    ]
    if data:
        main = next(v for k, v in data["proportions"].items() if k.startswith("Main proportions"))
        lines.append(
            f"  JSON 대비: 높이 {fmt(diff(m['height'], main['HEAD_HEIGHT']), True)}, "
            f"너비 {fmt(diff(m['width'], main['HEAD_WIDTH']), True)} (Subdivision으로 제어 메시보다 약간 작아짐)"
        )
    lines += [
        "== 머리 측면 깊이 [모델]",
        f"  깊이 {fmt(m['depth'])} m: 얼굴 앞 Y {fmt(m['front_y'], True)} (Z {fmt(m['front_z'])}), "
        f"뒤통수 Y {fmt(m['back_y'], True)} (Z {fmt(m['back_z'])}), 중심 Y {fmt(m['centre_y'], True)}",
        "== 턱 [모델]",
        f"  턱 아래 Z {fmt(m['chin_z'])}, Y {fmt(m['chin_y'], True)} / 턱 끝 앞 Y {fmt(m['chin_front_y'], True)}",
        "== 뒤통수 돌출 [모델]",
        f"  목 뒤쪽보다 뒤로: {fmt(m['back_y'] - m['neck_back_y'])} m",
        f"  몸통 뒤쪽보다 뒤로: {fmt(m['back_y'] - m['torso_back_y'])} m",
        f"  몸 중심(Y=0)보다 뒤로: {fmt(m['back_y'])} m",
        "== 목 연결 [모델]",
        f"  목 Z {fmt(m['neck_bottom_z'])}..{fmt(m['neck_top_z'])}, 중심 X {fmt(m['neck_centre'][0], True)} "
        f"Y {fmt(m['neck_centre'][1], True)} (머리 중심 Y {fmt(m['centre_y'], True)})",
        f"  머리 진입 Z {fmt(m['neck_entry_z'])} -> 머리 안으로 {fmt(diff(m['neck_top_z'], m['neck_entry_z']))} m, "
        f"목 축 위치의 몸통 윗면 Z {fmt(m['torso_top_on_neck_axis'])}",
        "  목 노출 길이: " + ", ".join(f"{NECK_LINE_NAMES.get(k, k)} {fmt(v)}" for k, v in m["neck_exposed"].items()),
    ]

    # ---- Side image -------------------------------------------------------
    lines += ["", "== 측면 참조 [이미지] (현재 배치된 REF_Side 기준)"]
    side_obj = find_reference("Side")
    side = None
    if side_obj is None:
        lines.append("  REF_Side가 없어 측면 비교를 건너뜁니다")
    else:
        try:
            side = ReferenceImage(side_obj, "Y")
        except RuntimeError as error:
            lines.append(f"  {error}")
    if side is not None:
        if not side.alignment_ok:
            lines.append("  경고: REF_Side가 YZ 평면에 정렬되어 있지 않아 값이 왜곡될 수 있습니다")
        s = measure_side_image(side, m)
        location = side_obj.matrix_world.translation
        lines.append(
            f"  REF_Side 위치 ({location.x:+.3f}, {location.y:+.3f}, {location.z:+.3f}), "
            f"픽셀 크기 {fmt(side.pixel_size, digits=4)} m"
        )
        lines.append(
            "  모델 중심 Y: " + ", ".join(f"{CENTRE_NAMES.get(k, k)} {fmt(v, True)}" for k, v in m["centres"].items())
            + f", 머리 {fmt(m['centre_y'], True)}"
        )
        lines.append("  중심선 차이, 이미지 - 모델 Y (음수 = 이미지가 얼굴 방향 / 화면 왼쪽):")
        used = []
        for name, (value, count) in s["align"].items():
            lines.append(f"    {name:12s} {fmt(value, True)} m  ({count}개 행)")
            if value is not None:
                used.append(value)
        lines.append("    어깨         측정 불가 (뒤쪽이 머리카락에 가려 가슴·허리로 대신함)")
        offset = float(np.mean(used)) if used else 0.0
        if abs(offset) <= 0.01:
            lines.append(f"  이미지 오프셋 (구간 평균): {offset:+.3f} m -> 정렬됨")
        else:
            lines.append(
                f"  이미지 오프셋 (구간 평균): {offset:+.3f} m -> 정렬 필요. "
                f"setup_blender_references.py의 HORIZONTAL_OFFSETS['Side']에 {-offset:+.3f}를 더하세요"
            )
        lines.append("  아래 '보정' 열은 이 남은 오프셋을 뺀 값입니다")
        lines.append(
            f"  턱 Z: 이미지 {fmt(s['chin_z'])} / 모델 {fmt(m['chin_z'])} "
            f"(모델 {fmt(diff(m['chin_z'], s['chin_z']), True)})"
        )
        lines.append("  얼굴 윤곽 (가장 앞쪽 피부 Y, 차이가 음수면 모델이 더 앞):")
        lines.append("     Z      이미지   보정     모델     차이")
        diffs = []
        if s["chin_z"] is not None:
            z = s["chin_z"] + 0.005
            while z < s["chin_z"] + 0.20:
                img = s["front_skin"](z)
                aligned = None if img is None else img - offset
                mdl = model_front_y(m, z)
                d = diff(mdl, aligned)
                if d is not None:
                    diffs.append(d)
                lines.append(f"    {z:.3f}  {fmt(img, True)}  {fmt(aligned, True)}  {fmt(mdl, True)}  {fmt(d, True)}")
                z += PROFILE_STEP
        if diffs:
            rms = math.sqrt(sum(d * d for d in diffs) / len(diffs))
            lines.append(f"  얼굴 윤곽 RMS {rms:.3f} m, 최대 차이 {max(abs(d) for d in diffs):.3f} m "
                         "(이미지에는 코·입술이 있고 블록아웃에는 없음)")
        if s["chin_z"] is not None:
            face_img = min((v for v in (s["front_skin"](s["chin_z"] + dz) for dz in (0.03, 0.06, 0.09))
                            if v is not None), default=None)
            face_mdl = min((v for v in (model_front_y(m, s["chin_z"] + dz) for dz in (0.03, 0.06, 0.09))
                            if v is not None), default=None)
            lines.append(
                f"  얼굴 앞이 가슴 앞보다 앞선 거리: 이미지 {fmt(diff(s['chest_front_y'], face_img))} m "
                f"(블라우스 기준), 모델 {fmt(diff(m['chest_front_y'], face_mdl))} m (맨몸 기준)"
            )
        margins = []
        z = m["chin_z"] + 0.12
        while z < m["top_z"] - 0.02:
            img = s["silhouette_back"](z)
            mdl = model_back_y(m, z)
            if img is not None and mdl is not None:
                margins.append(img - offset - mdl)
            z += PROFILE_STEP
        if margins:
            lines.append(
                f"  두개골 뒤 머리카락 여유: 최소 {min(margins):+.3f} / 평균 "
                f"{sum(margins) / len(margins):+.3f} m (음수 = 두개골이 머리카락 윤곽 밖으로 나옴)"
            )

    # ---- Front image ------------------------------------------------------
    lines += ["", "== 정면 참조 [이미지] (현재 배치된 REF_Front 기준)"]
    front_obj = find_reference("Front")
    front = None
    if front_obj is None:
        lines.append("  REF_Front가 없어 정면 비교를 건너뜁니다")
    else:
        try:
            front = ReferenceImage(front_obj, "X")
        except RuntimeError as error:
            lines.append(f"  {error}")
    if front is not None:
        if not front.alignment_ok:
            lines.append("  경고: REF_Front가 XZ 평면에 정렬되어 있지 않아 값이 왜곡될 수 있습니다")
        f = measure_front_image(front, m)
        lines.append(
            f"  턱 Z: 이미지 {fmt(f['chin_z'])} / 모델 {fmt(m['chin_z'])} "
            f"(모델 {fmt(diff(m['chin_z'], f['chin_z']), True)})"
        )
        lines.append(f"  아래 얼굴 반폭 (귀 아래 피부 경계, |X| < {FRONT_FACE_LIMIT_X}):")
        lines.append("     Z      이미지   모델    차이    이미지 중심 X")
        if f["chin_z"] is not None:
            for dz in (0.01, 0.025, 0.04, 0.055, 0.07):
                z = f["chin_z"] + dz
                edges = f["face_edges"](z)
                img = None if edges is None else (edges[1] - edges[0]) / 2.0
                centre = None if edges is None else (edges[1] + edges[0]) / 2.0
                mdl = model_half_width(m, z)
                lines.append(f"    {z:.3f}  {fmt(img)}  {fmt(mdl)}  {fmt(diff(mdl, img), True)}  {fmt(centre, True)}")
        hair = []
        z = m["chin_z"] + 0.15
        while z < m["top_z"] - 0.03:
            img = f["silhouette_half_width"](z)
            mdl = model_half_width(m, z)
            if img is not None and mdl is not None:
                hair.append(img - mdl)
            z += PROFILE_STEP
        if hair:
            lines.append(
                f"  두개골 바깥 머리카락 여유 (한쪽): 최소 {min(hair):+.3f} / 평균 "
                f"{sum(hair) / len(hair):+.3f} m (음수 = 두개골이 머리카락 윤곽보다 넓음)"
            )

    lines += [
        "",
        "[측정 안 함] 원본에서 머리카락·옷깃·그림자에 가려 이미지로 측정할 수 없는 항목:",
        "  - 실제 두개골 깊이와 뒤통수 형태 (위에서는 머리카락 윤곽만 측정)",
        "  - 목 길이, 굵기, 머리와 이어지는 위치",
        "  - 앞머리·옆머리에 가려진 이마·관자놀이 너비",
        "  이 항목은 정면(Numpad 1) / 오른쪽(Numpad 3) 뷰에서 X-ray(Alt+Z)를 켜고 눈으로 비교하세요.",
    ]
    return lines


def main():
    lines = build_report()
    print("\n[MainGirlfriend 프로필 검사]")
    for line in lines:
        print("  " + line)

    if not bpy.app.background and bpy.context.window_manager is not None:
        summary = [
            line for line in lines
            if line.startswith(("==", "  이미지 오프셋", "  얼굴 윤곽 RMS", "  턱 Z", "오류"))
        ]

        def draw(self, _context):
            for line in summary:
                self.layout.label(text=line.strip())
            self.layout.label(text="전체 결과: Blender 시스템 콘솔")

        bpy.context.window_manager.popup_menu(draw, title="MainGirlfriend 프로필 검사", icon="INFO")


if __name__ == "__main__":
    main()
