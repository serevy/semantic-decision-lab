from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from .probes import load_matrix, load_source_fixture, materialize_fixture, validate_matrix
except ImportError:
    from probes import load_matrix, load_source_fixture, materialize_fixture, validate_matrix


ROOT = Path(__file__).resolve().parent
CLEF_ROOT = ROOT.parent
HOSTED_RUNNER = CLEF_ROOT / "run_workers_ai_smoke.py"

STOP_STAGES = {
    "configuration-error",
    "http-error",
    "transport-error",
    "response-read-error",
    "response-decode-error",
    "response-parse-error",
    "request-validation-error",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--matrix", default=str(ROOT / "probe-matrix.v0.1.json"))
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    matrix_path = Path(args.matrix)
    matrix = load_matrix(matrix_path)
    validate_matrix(matrix)
    source = load_source_fixture(matrix)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)

    failures: list[dict[str, str]] = []
    completed: list[str] = []

    with tempfile.TemporaryDirectory(prefix="clef-phase1a-") as temp_directory:
        temp_root = Path(temp_directory)

        for variant in matrix["variants"]:
            variant_id = variant["id"]
            fixture = materialize_fixture(variant, source)
            fixture_path = temp_root / f"{variant_id}.json"
            fixture_path.write_text(
                json.dumps(fixture, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            evidence_path = output_dir / f"{variant_id}.json"
            completed_process = subprocess.run(
                [
                    sys.executable,
                    str(HOSTED_RUNNER),
                    "--fixture",
                    str(fixture_path),
                    "--model",
                    "clef-flash",
                    "--output",
                    str(evidence_path),
                    "--timeout",
                    str(args.timeout),
                ],
                check=False,
            )
            completed.append(variant_id)

            if completed_process.returncode != 0:
                stage = "missing-evidence"
                if evidence_path.is_file():
                    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                    stage = str(evidence.get("stage"))
                failures.append({"variant": variant_id, "stage": stage})
                if stage in STOP_STAGES:
                    break

    summary = {
        "schema_version": "0.1",
        "experiment": matrix["experiment"],
        "completed_variants": completed,
        "failures": failures,
    }
    (output_dir / "run-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
