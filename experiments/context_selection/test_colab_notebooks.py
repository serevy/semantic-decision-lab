#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
NOTEBOOKS = [
    ROOT / "open_jev_v0_1_colab.ipynb",
    ROOT / "open_jev_v0_2_colab.ipynb",
]


def main() -> None:
    for path in NOTEBOOKS:
        data = json.loads(path.read_text())
        code_cells = [cell for cell in data.get("cells", []) if cell.get("cell_type") == "code"]
        if not code_cells:
            raise SystemExit(f"{path.name}: no code cells found")
        for index, cell in enumerate(code_cells):
            source = cell.get("source", [])
            if not isinstance(source, list):
                raise SystemExit(f"{path.name}: code cell {index} source is not a list")
            for line in source:
                if "\\n" in line:
                    raise SystemExit(
                        f"{path.name}: code cell {index} contains literal \\n instead of a newline"
                    )
        print(f"{path.name}: ok")


if __name__ == "__main__":
    main()
