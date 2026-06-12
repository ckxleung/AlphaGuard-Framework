# -*- coding: utf-8 -*-
"""Layer 3 registration boundary."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.module_manifest import MODULE_SPECS


def main() -> int:
    modules = [spec.code for spec in MODULE_SPECS if spec.layer == "layer_3_compliance"]
    print(",".join(modules))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
