# -*- coding: utf-8 -*-
"""Fail-closed repository validator for AlphaGuard development."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.module_manifest import MODULE_SPECS, validate_manifest


REQUIRED_LAYERS = (
    "layer_1_telemetry",
    "layer_2_valuation",
    "layer_3_compliance",
    "layer_4_strategy",
)
FORBIDDEN_MARKERS = ("TODO", "NotImplementedError")


def _validate_kernel_file(path: Path) -> tuple[str, ...]:
    errors: list[str] = []
    source = path.read_text(encoding="utf-8")
    for marker in FORBIDDEN_MARKERS:
        if marker in source:
            errors.append(f"{path}: forbidden placeholder marker '{marker}'.")

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as error:
        return (f"{path}: syntax error: {error}",)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                errors.append(f"{path}:{node.lineno}: empty function implementation.")
    return tuple(errors)


def validate_repository(root: Path = ROOT) -> dict[str, Any]:
    """Validate structure, manifest, and all registered implementations."""
    errors = list(validate_manifest())
    kernel_root = root / "evaluation_kernels"

    for layer in REQUIRED_LAYERS:
        if not (kernel_root / layer).is_dir():
            errors.append(f"Missing required layer directory: {layer}")

    for path in kernel_root.rglob("*.py"):
        errors.extend(_validate_kernel_file(path))

    for spec in MODULE_SPECS:
        if spec.status != "IMPLEMENTED":
            continue
        implementation = root / spec.implementation_path
        if not implementation.is_file():
            errors.append(
                f"Module {spec.module_id} implementation is missing: "
                f"{spec.implementation_path}"
            )

    return {
        "valid": not errors,
        "errors": tuple(errors),
        "module_counts": {
            "total": len(MODULE_SPECS),
            "implemented": sum(
                spec.status == "IMPLEMENTED" for spec in MODULE_SPECS
            ),
            "specified": sum(spec.status == "SPECIFIED" for spec in MODULE_SPECS),
            "spec_required": sum(
                spec.status == "SPEC_REQUIRED" for spec in MODULE_SPECS
            ),
        },
    }


def main() -> int:  # pragma: no cover
    result = validate_repository()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["valid"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
