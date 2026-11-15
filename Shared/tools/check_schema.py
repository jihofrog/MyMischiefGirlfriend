#!/usr/bin/env python3
"""Validate the shared JSON files against Shared/schemas with the standard library only.

Supports the subset of JSON Schema the schemas use: type, const, enum, pattern, minimum, minItems, maxItems,
uniqueItems, required, properties, additionalProperties (false or schema), items, oneOf, $ref (local "#/..." and
"<file>.schema.json[#/...]").

usage: python3 Shared/tools/check_schema.py            # checks every known file, exit code 1 on any error
"""
import json
import re
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parents[1]
SCHEMAS = SHARED / "schemas"
TARGETS = [
    ("catalog.schema.json", SHARED / "samples" / "catalog_mainGirlfriend_v1.json"),
    ("catalog.schema.json", SHARED / "testcases" / "appearance" / "catalog_rules_test.json"),
    ("testcases.schema.json", SHARED / "testcases" / "appearance" / "cases_equipment.json"),
    ("testcases.schema.json", SHARED / "testcases" / "appearance" / "cases_resolve.json"),
]

_cache = {}


def load_schema(name):
    if name not in _cache:
        _cache[name] = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    return _cache[name]


def resolve_ref(ref, root_name):
    file_part, _, pointer = ref.partition("#")
    name = file_part or root_name
    node = load_schema(name)
    for key in [p for p in pointer.split("/") if p]:
        node = node[key]
    return node, name


TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def validate(value, schema, root, path, errors):
    if "$ref" in schema:
        target, name = resolve_ref(schema["$ref"], root)
        validate(value, target, name, path, errors)
        return
    if "oneOf" in schema:
        matches = 0
        for option in schema["oneOf"]:
            sub = []
            validate(value, option, root, path, sub)
            matches += not sub
        if matches != 1:
            errors.append(f"{path}: matches {matches} of oneOf options (need exactly 1)")
        return
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(TYPES[t](value) for t in types):
            errors.append(f"{path}: expected {types}, got {type(value).__name__}")
            return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, str) and "pattern" in schema and not re.search(schema["pattern"], value):
        errors.append(f"{path}: {value!r} does not match {schema['pattern']}")
    if TYPES["number"](value) and "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{path}: {value} < minimum {schema['minimum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen = [json.dumps(v, sort_keys=True) for v in value]
            if len(seen) != len(set(seen)):
                errors.append(f"{path}: items are not unique")
        if "items" in schema:
            for i, item in enumerate(value):
                validate(item, schema["items"], root, f"{path}[{i}]", errors)
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required '{key}'")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in props:
                validate(item, props[key], root, f"{path}.{key}", errors)
            elif extra is False:
                errors.append(f"{path}: unknown property '{key}'")
            elif isinstance(extra, dict):
                validate(item, extra, root, f"{path}.{key}", errors)


def main():
    failed = False
    for schema_name, target in TARGETS:
        errors = []
        validate(json.loads(target.read_text(encoding="utf-8")), load_schema(schema_name), schema_name, "$", errors)
        rel = target.relative_to(SHARED.parent)
        if errors:
            failed = True
            print(f"FAIL {rel} ({schema_name}): {len(errors)} error(s)")
            for e in errors[:50]:
                print("   ", e)
        else:
            print(f"ok   {rel} ({schema_name})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
