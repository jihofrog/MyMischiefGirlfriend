"""Save the current create_character_blockout.py parameters to a versioned JSON file.

The blockout script is parsed as text (it is not executed), so this works both
with plain Python and inside Blender. Nothing in the .blend file is touched.

Usage:
    python3 export_character_proportions.py              # writes character_proportions_v1.json
    python3 export_character_proportions.py --version v2
    python3 export_character_proportions.py --force      # overwrite an existing file

Inside Blender: Scripting > Text > Open this file > Run Script (uses the defaults above).
"""

import argparse
import ast
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


BLOCKOUT_SCRIPT_NAME = "create_character_blockout.py"
DEFAULT_VERSION = "v1"
OUTPUT_PATTERN = "character_proportions_{version}.json"

# Sections whose values describe the character. Everything else is exported as tool settings.
PROPORTION_SECTIONS = (
    "Main proportions",
    "Secondary proportions",
    "Depth, side view",
    "Head shape",
)

SECTION_HEADER = re.compile(r"^# =+\s*\n# (?P<title>[^\n]+)\n# =+\s*$", re.MULTILINE)


def candidate_dirs():
    try:
        yield Path(__file__).resolve().parent
    except NameError:
        pass
    if "bpy" in sys.modules:
        import bpy

        for text in bpy.data.texts:
            if text.filepath:
                yield Path(bpy.path.abspath(text.filepath)).resolve().parent
        if bpy.data.filepath:
            yield Path(bpy.data.filepath).resolve().parent
    yield Path.cwd()


def script_dir():
    """Folder that contains the blockout script (Blender's Text Editor sets __file__ inside the .blend)."""
    for base in candidate_dirs():
        if (base / BLOCKOUT_SCRIPT_NAME).is_file():
            return base
    raise FileNotFoundError(f"{BLOCKOUT_SCRIPT_NAME}을(를) 이 스크립트나 .blend 파일 옆에서 찾을 수 없습니다.")


def section_for_line(source, lineno):
    """Title of the nearest '# ====' section header above the given line."""
    offset = sum(len(line) for line in source.splitlines(keepends=True)[: lineno - 1])
    title = None
    for match in SECTION_HEADER.finditer(source):
        if match.start() > offset:
            break
        title = match.group("title").strip()
    return title


def read_parameters(source):
    sections = {}
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or not target.id.isupper():
            continue
        try:
            value = ast.literal_eval(node.value)
        except ValueError:
            continue  # computed values such as Vector(...) are not parameters
        title = section_for_line(source, node.lineno) or "Other"
        sections.setdefault(title, {})[target.id] = list(value) if isinstance(value, tuple) else value
    return sections


def derived_landmarks(params):
    crotch = params["LEG_LENGTH"]
    waist = crotch + params["PELVIS_HEIGHT"]
    shoulder_top = waist + params["TORSO_LENGTH"]
    chin = params["CHARACTER_HEIGHT"] - params["HEAD_HEIGHT"]
    return {
        "crotch_z": round(crotch, 4),
        "waist_z": round(waist, 4),
        "shoulder_top_z": round(shoulder_top, 4),
        "chin_z": round(chin, 4),
        "head_top_z": params["CHARACTER_HEIGHT"],
        "chin_to_shoulder_top": round(chin - shoulder_top, 4),
        "heads_tall": round(params["CHARACTER_HEIGHT"] / params["HEAD_HEIGHT"], 3),
    }


def export(version=DEFAULT_VERSION, force=False):
    base = script_dir()
    blockout_path = base / BLOCKOUT_SCRIPT_NAME
    output_path = base / OUTPUT_PATTERN.format(version=version)

    if output_path.exists() and not force:
        raise FileExistsError(f"{output_path.name}이(가) 이미 있습니다. --force 또는 새 --version을 사용하세요.")

    source = blockout_path.read_text(encoding="utf-8")
    sections = read_parameters(source)
    proportions = {k: v for k, v in sections.items() if k.startswith(PROPORTION_SECTIONS)}
    settings = {k: v for k, v in sections.items() if not k.startswith(PROPORTION_SECTIONS)}
    flat = {name: value for group in proportions.values() for name, value in group.items()}

    data = {
        "character": "MainGirlfriend",
        "version": version,
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_script": BLOCKOUT_SCRIPT_NAME,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "units": "metres, degrees",
        "conventions": {"front": "-Y", "up": "+Z", "soles_z": 0.0, "character_left": "+X"},
        "proportions": proportions,
        "derived": derived_landmarks(flat),
        "tool_settings": settings,
        "notes": [
            "Derived values come from the parameters. The built mesh is rescaled by AUTO_FIT_HEIGHT "
            "(about 0.1%) so the subdivided result is exactly CHARACTER_HEIGHT.",
            "HEAD_HEIGHT excludes hair; the head top of the blockout sits at CHARACTER_HEIGHT.",
        ],
    }

    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path, data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    try:
        path, data = export(args.version, args.force)
    except (FileExistsError, FileNotFoundError) as error:
        print(f"[비율 저장] {error}")
        return 1
    count = sum(len(group) for group in data["proportions"].values())
    print(f"[비율 저장] 비율 파라미터 {count}개를 저장했습니다: {path}")
    print(f"[비율 저장] 파생 값: {data['derived']}")
    return 0


if __name__ == "__main__":
    if "bpy" in sys.modules:
        # Blender passes its own arguments; only parse what follows "--".
        main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    else:
        sys.exit(main())
