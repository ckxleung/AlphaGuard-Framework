# -*- coding: utf-8 -*-
"""Layer 4 registration boundary."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.module_manifest import MODULE_SPECS


def main() -> int:
    modules = [
        {
            "code": spec.code,
            "status": spec.status,
        }
        for spec in MODULE_SPECS
        if spec.layer == "layer_4_strategy"
    ]
    import json

    print(json.dumps(modules, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
