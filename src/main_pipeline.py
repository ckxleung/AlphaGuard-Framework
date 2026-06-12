# -*- coding: utf-8 -*-
"""One-command AlphaGuard pipeline entry point."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_auditor import BaseAuditor
from src.module_manifest import MODULE_SPECS
from src.repository_validator import validate_repository


def _load_json_object(path: Path) -> dict[str, Any]:  # pragma: no cover
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _load_auditor(implementation_path: str, class_name: str) -> BaseAuditor:
    path = ROOT / implementation_path
    spec = importlib.util.spec_from_file_location(
        f"alphaguard_runtime_{path.stem}",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load auditor module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    auditor_class = getattr(module, class_name)
    if not issubclass(auditor_class, BaseAuditor):
        raise TypeError(f"{class_name} must inherit from BaseAuditor.")
    return auditor_class()


def run_pipeline(
    ai_output: dict[str, Any],
    ground_truth: dict[str, Any],
) -> dict[str, Any]:
    """Execute every implemented kernel and validate every scorecard."""
    validation = validate_repository()
    if not validation["valid"]:
        raise RuntimeError("Repository validation failed before pipeline execution.")

    results: dict[str, Any] = {}
    for specification in MODULE_SPECS:
        if specification.status != "IMPLEMENTED":
            continue
        auditor = _load_auditor(
            specification.implementation_path,
            specification.class_name,
        )
        scorecard = auditor.execute_audit(dict(ai_output), dict(ground_truth))
        results[specification.code] = BaseAuditor.validate_scorecard(scorecard)

    return {
        "executed_modules": len(results),
        "results": results,
        "repository_status": validation["module_counts"],
    }


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai-output", type=Path)
    parser.add_argument("--ground-truth", type=Path)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the repository without executing kernels.",
    )
    arguments = parser.parse_args()

    if arguments.validate_only:
        report = validate_repository()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["valid"] else 1

    if not arguments.ai_output or not arguments.ground_truth:
        parser.error("--ai-output and --ground-truth are required for execution.")

    report = run_pipeline(
        _load_json_object(arguments.ai_output),
        _load_json_object(arguments.ground_truth),
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
