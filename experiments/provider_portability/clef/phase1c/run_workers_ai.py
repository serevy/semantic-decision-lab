from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from .probes import DEFAULT_MANIFEST, load_manifest, materialize_case, validate_manifest
except ImportError:
    from probes import DEFAULT_MANIFEST, load_manifest, materialize_case, validate_manifest


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
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    cases = validate_manifest(manifest, manifest_path)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    completed = []
    failures = []

    with tempfile.TemporaryDirectory(prefix="clef-phase1c-") as temp_directory:
        temp_root = Path(temp_directory)
        for case in cases:
            fixture_id = case["fixture_id"]
            variant_id = case["variant"]["id"]
            repeat_index = case["repeat_index"]
            case_id = f"{fixture_id}/{variant_id}/repeat-{repeat_index}"

            evidence_dir = output_dir / fixture_id / variant_id
            evidence_dir.mkdir(parents=True, exist_ok=True)
            temp_fixture_dir = temp_root / fixture_id / variant_id
            temp_fixture_dir.mkdir(parents=True, exist_ok=True)

            fixture_path = temp_fixture_dir / f"repeat-{repeat_index}.json"
            fixture_path.write_text(
                json.dumps(materialize_case(case), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            evidence_path = evidence_dir / f"repeat-{repeat_index}.json"

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
            completed.append(case_id)

            evidence = None
            if evidence_path.is_file():
                evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                if (
                    evidence.get("request_sha256") != case["canonical_request_sha256"]
                    or evidence.get("wire_request_sha256") != case["wire_request_sha256"]
                ):
                    failures.append(
                        {"case": case_id, "stage": "evidence-hash-mismatch"}
                    )
                    break

            if completed_process.returncode != 0:
                stage = "missing-evidence"
                if evidence is not None:
                    stage = str(evidence.get("stage"))
                failures.append({"case": case_id, "stage": stage})
                if stage in STOP_STAGES:
                    break

    summary = {
        "schema_version": "0.1",
        "experiment": manifest["experiment"],
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "expected_provider_calls": manifest["expected_provider_calls"],
        "completed_calls": completed,
        "failures": failures,
    }
    (output_dir / "run-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
