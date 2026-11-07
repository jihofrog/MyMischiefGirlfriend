"""Place the MainGirlfriend front / side / back reference images in Blender.

Run inside Blender (4.x / 5.x):
    - Scripting workspace > Text > Open > this file > Run Script, or
    - Blender Models/MainGirlfriend_Base.blend --python setup_blender_references.py

Conventions:
    - Character faces -Y. Soles at Z = 0, head top at Z = CHARACTER_HEIGHT.
    - Front image: XZ plane, behind the model as seen from Front view (Numpad 1).
    - Side image:  YZ plane, behind the model as seen from Right view (Numpad 3).
    - Back image:  XZ plane, behind the model as seen from Back view (Ctrl + Numpad 1).

Re-running the script updates the existing reference objects instead of duplicating them.
Nothing outside the Reference_Images collection is modified or deleted.
"""

import json
import math
from pathlib import Path

import bpy


# ---------------------------------------------------------------------------
# Adjustable settings
# ---------------------------------------------------------------------------

CHARACTER_HEIGHT = 1.65  # metres, sole to head top

COLLECTION_NAME = "Reference_Images"
REFERENCE_DIR_NAME = "References"
LAYOUT_FILE_NAME = "reference_layout.json"

# Absolute path (or Blender "//" relative path) to the References folder.
# Leave empty to locate it automatically next to this script / the .blend file.
REFERENCE_DIR_OVERRIDE = ""

# Distance of each image plane from the origin (metres).
FRONT_BACK_DISTANCE = 1.0
SIDE_DISTANCE = 1.0

# Horizontal nudge per view (metres, along the image's own right direction),
# e.g. to line up the side view's body centre with Y = 0.
HORIZONTAL_OFFSETS = {
    "Front": 0.0,
    # Side.png is centred on its bounding box (hair and boot toes included), which puts the body
    # 0.063 m toward -Y. Value = mean of the chest, pelvis and leg centreline offsets.
    "Side": 0.063,
    "Back": 0.0,
}

OPACITY = 0.5
LOCK_SELECTION = True        # reference images cannot be clicked in the viewport
SHOW_IN_PERSPECTIVE = False  # show only in orthographic views
ONLY_AXIS_ALIGNED = True     # show only when the view looks straight at the image


# ---------------------------------------------------------------------------

TAG = "mmg_reference_view"

VIEWS = {
    "Front": {
        "file": "Front.png",
        "location": (0.0, FRONT_BACK_DISTANCE, 0.0),
        "rotation_deg": (90.0, 0.0, 0.0),
        "right_axis": (1.0, 0.0, 0.0),
    },
    "Side": {
        "file": "Side.png",
        "location": (-SIDE_DISTANCE, 0.0, 0.0),
        "rotation_deg": (90.0, 0.0, 90.0),
        "right_axis": (0.0, 1.0, 0.0),
    },
    "Back": {
        "file": "Back.png",
        "location": (0.0, -FRONT_BACK_DISTANCE, 0.0),
        "rotation_deg": (90.0, 0.0, 180.0),
        "right_axis": (-1.0, 0.0, 0.0),
    },
}


def candidate_base_dirs():
    try:
        yield Path(__file__).resolve().parent
    except NameError:
        pass

    for text in bpy.data.texts:
        if text.filepath:
            text_path = Path(bpy.path.abspath(text.filepath))
            if text_path.name == "setup_blender_references.py":
                yield text_path.parent

    if bpy.data.filepath:
        blend_dir = Path(bpy.data.filepath).parent
        yield blend_dir
        yield blend_dir.parent


def resolve_reference_dir():
    if REFERENCE_DIR_OVERRIDE:
        reference_dir = Path(bpy.path.abspath(REFERENCE_DIR_OVERRIDE))
        if not reference_dir.is_dir():
            raise RuntimeError(f"REFERENCE_DIR_OVERRIDE 경로가 없습니다: {reference_dir}")
        return reference_dir

    for base in candidate_base_dirs():
        reference_dir = base / REFERENCE_DIR_NAME
        if reference_dir.is_dir():
            return reference_dir

    raise RuntimeError(
        f"'{REFERENCE_DIR_NAME}' 폴더를 찾을 수 없습니다. prepare_reference_images.py를 먼저 실행하거나, "
        ".blend 파일을 MainGirlfriend 폴더 안에 저장하거나, REFERENCE_DIR_OVERRIDE를 지정하세요."
    )


def load_layout(reference_dir):
    layout_path = reference_dir / LAYOUT_FILE_NAME
    if not layout_path.is_file():
        print(f"[참조 이미지] {LAYOUT_FILE_NAME} 없음: 이미지 전체 높이를 머리 꼭대기~발바닥으로 가정합니다.")
        return {}
    return json.loads(layout_path.read_text(encoding="utf-8")).get("views", {})


def blender_path(path):
    if bpy.data.filepath:
        blend_dir = Path(bpy.data.filepath).resolve().parent
        try:
            return bpy.path.relpath(str(Path(path).resolve()), start=str(blend_dir))
        except ValueError:
            pass
    return str(path)


def ensure_collection(scene):
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
    if collection not in scene.collection.children_recursive:
        scene.collection.children.link(collection)
    return collection


def find_tagged(datablocks, view):
    for block in datablocks:
        if block.get(TAG) == view:
            return block
    return None


def ensure_image(view, path):
    image = find_tagged(bpy.data.images, view)
    if image is None:
        image = bpy.data.images.load(str(path), check_existing=False)
        image.name = f"REF_{view}"
        image[TAG] = view

    image.filepath = blender_path(path)
    image.reload()
    if image.size[0] == 0 or image.size[1] == 0:
        raise RuntimeError(f"참조 이미지를 불러오지 못했습니다: {path}")
    return image


def ensure_empty(view, collection):
    obj = find_tagged(bpy.data.objects, view)
    if obj is None:
        obj = bpy.data.objects.new(f"REF_{view}", None)
        obj[TAG] = view
    if obj.name not in collection.objects:
        collection.objects.link(obj)
    return obj


def set_if_present(obj, attr, value):
    if hasattr(obj, attr):
        setattr(obj, attr, value)


def image_layout(view, image, layout):
    width, height = image.size
    info = layout.get(view, {})
    if info.get("width") != width or info.get("height") != height:
        if info:
            print(f"[참조 이미지] {view}: 레이아웃 크기가 이미지와 달라 이미지 전체 높이를 사용합니다.")
        info = {}
    return (
        width,
        height,
        info.get("head_top_px", 0),
        info.get("sole_px", height),
        info.get("center_x_px", width / 2),
    )


def configure_empty(obj, view, image, layout):
    settings = VIEWS[view]
    width, height, head_top_px, sole_px, center_x_px = image_layout(view, image, layout)

    metres_per_px = CHARACTER_HEIGHT / (sole_px - head_top_px)

    obj.empty_display_type = "IMAGE"
    obj.data = image
    obj.empty_display_size = max(width, height) * metres_per_px
    # Offsets are fractions of the image size: put the character centre at local X = 0
    # and the soles at local Y = 0 (image Y grows upwards in Blender).
    obj.empty_image_offset = (
        -center_x_px / width,
        -(height - sole_px) / height,
    )

    offset = HORIZONTAL_OFFSETS.get(view, 0.0)
    obj.location = tuple(
        loc + axis * offset for loc, axis in zip(settings["location"], settings["right_axis"])
    )
    obj.rotation_mode = "XYZ"
    obj.rotation_euler = tuple(math.radians(angle) for angle in settings["rotation_deg"])
    obj.scale = (1.0, 1.0, 1.0)

    obj.color = (1.0, 1.0, 1.0, OPACITY)
    set_if_present(obj, "use_empty_image_alpha", True)
    set_if_present(obj, "empty_image_depth", "BACK")
    set_if_present(obj, "empty_image_side", "FRONT")
    set_if_present(obj, "show_empty_image_orthographic", True)
    set_if_present(obj, "show_empty_image_perspective", SHOW_IN_PERSPECTIVE)
    set_if_present(obj, "show_empty_image_only_axis_aligned", ONLY_AXIS_ALIGNED)
    obj.hide_select = LOCK_SELECTION
    obj.hide_render = True


def main():
    reference_dir = resolve_reference_dir()
    layout = load_layout(reference_dir)
    collection = ensure_collection(bpy.context.scene)

    for view, settings in VIEWS.items():
        path = reference_dir / settings["file"]
        if not path.is_file():
            raise RuntimeError(f"참조 이미지가 없습니다: {path}. prepare_reference_images.py를 먼저 실행하세요.")

        image = ensure_image(view, path)
        obj = ensure_empty(view, collection)
        configure_empty(obj, view, image, layout)
        print(f"[참조 이미지] {obj.name}: {image.filepath}, 위치 {tuple(round(v, 3) for v in obj.location)}")

    print(f"[참조 이미지] 완료. 컬렉션 '{COLLECTION_NAME}', 캐릭터 키 {CHARACTER_HEIGHT} m.")


if __name__ == "__main__":
    main()
