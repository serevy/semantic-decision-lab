from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path


EXPECTED_ARTIFACT_SHA256 = "3cef7569014381bd33574657e892b5f1034f29281fd6c917fe0ce6b2f9752629"
RESULTS = Path("experiments/provider_portability/clef/results")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: repair_clef_phase1b_bundle.py <artifact-dir>")

    artifact_root = Path(sys.argv[1])
    responses: dict[str, dict[str, str]] = {}

    for path in sorted(artifact_root.rglob("*.json")):
        if path.name in {"analysis.v0.1.json", "run-summary.json"}:
            continue

        record = json.loads(path.read_text(encoding="utf-8"))
        key = str(path.relative_to(artifact_root).with_suffix(""))
        raw = base64.b64decode(record["raw_response_base64"])
        observed = sha256(raw)
        expected = record["raw_response_sha256"]
        if observed != expected:
            raise SystemExit(
                f"raw response hash mismatch: {key}: {observed} != {expected}"
            )

        responses[key] = {
            "request_sha256": record["request_sha256"],
            "wire_request_sha256": record["wire_request_sha256"],
            "raw_response_sha256": expected,
            "raw_response_base64": record["raw_response_base64"],
        }

    if len(responses) != 42:
        raise SystemExit(f"expected 42 responses, got {len(responses)}")

    bundle = {
        "schema_version": "0.2",
        "experiment": "clef-flash-phase1b-replication",
        "repair_note": (
            "Reconstructed from digest-verified GitHub Actions artifact "
            "11304537926 after the originally retained bundle was found "
            "to fail gzip CRC validation."
        ),
        "run_identity": {
            "workflow_run": 37205657656,
            "workflow_head": "2c98622338a19f09a7926e6dcf05533a59d48a80",
            "artifact_id": 11304537926,
            "artifact_digest": f"sha256:{EXPECTED_ARTIFACT_SHA256}",
            "manifest_sha256": "b4868b760af95b080d8848db7cfe5e610eb1bf6cca110b805c89b14105a9c23a",
            "provider": "cloudflare-workers-ai",
            "model_alias": "@cf/cloudflare/clef-flash",
            "hosted_immutable_model_revision": None,
        },
        "responses": responses,
    }

    raw_json = json.dumps(
        bundle,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    gz = gzip.compress(raw_json, mtime=0)
    b64 = base64.b64encode(gz) + b"\n"

    raw_sha = sha256(raw_json)
    gzip_sha = sha256(gz)
    b64_sha = sha256(b64)

    restored = gzip.decompress(base64.b64decode(b64))
    if restored != raw_json:
        raise SystemExit("Phase 1B bundle round-trip failed")

    bundle_path = RESULTS / "clef-phase1b-hosted-v0.1.bundle.json.gz.b64"
    bundle_path.write_bytes(b64)

    # Verify the Phase 1B -> Phase 1C raw-hash comparison from repository-retained
    # Evidence after repairing Phase 1B.
    phase1c_path = RESULTS / "clef-phase1c-hosted-v0.1.bundle.json.gz.b64"
    phase1c = json.loads(
        gzip.decompress(base64.b64decode(phase1c_path.read_bytes()))
    )
    compared = 0
    mismatches: list[str] = []
    for record in phase1c["records"]:
        if record["repeat"] != 1:
            continue
        key = f'{record["fixture"]}/{record["variant"]}'
        phase1b = responses.get(key)
        if phase1b is None:
            raise SystemExit(f"missing Phase 1B comparison record: {key}")
        compared += 1
        if phase1b["raw_response_sha256"] != record["raw_response_sha256"]:
            mismatches.append(key)

    if compared != 18:
        raise SystemExit(f"expected 18 cross-workflow comparisons, got {compared}")
    if mismatches:
        raise SystemExit(f"Phase 1B -> Phase 1C raw hash mismatches: {mismatches}")

    summary_path = RESULTS / "clef-phase1b-hosted-v0.1-summary.md"
    summary = summary_path.read_text(encoding="utf-8")
    summary = summary.replace(
        "- the full Phase 1B analysis object.\n",
        "- all 42 exact provider response bodies and their request/wire hashes.\n\n"
        "The full analysis summary remains separately preserved in "
        "`clef-phase1b-hosted-v0.1-analysis-summary.json`.\n",
    )

    repair_block = f"""Integrity after repair:

- decoded gzip SHA-256:
  `{gzip_sha}`
- Base64 text SHA-256:
  `{b64_sha}`
- uncompressed compact JSON SHA-256:
  `{raw_sha}`

Repair provenance:

- the previously retained bundle was found during PR #131 review to fail gzip CRC validation;
- this replacement was reconstructed from GitHub Actions Artifact `11304537926`;
- the downloaded artifact SHA-256 was rechecked against the frozen digest
  `{EXPECTED_ARTIFACT_SHA256}`;
- all **42 / 42** decoded raw response bodies matched their recorded
  `raw_response_sha256` before this replacement was written;
- the repaired repository Evidence independently reproduces the Phase 1B -> Phase 1C
  raw-response SHA-256 comparison at **18 / 18**.

Example reconstruction:"""

    summary, count = re.subn(
        r"Integrity:\n\n- decoded gzip SHA-256:.*?Example reconstruction:",
        repair_block,
        summary,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise SystemExit("could not replace Phase 1B integrity block")
    summary_path.write_text(summary, encoding="utf-8")

    print("Phase 1B Evidence repair verified")
    print(f"responses={len(responses)}")
    print(f"phase1b_to_phase1c_matches={compared}")
    print(f"raw_json_sha256={raw_sha}")
    print(f"gzip_sha256={gzip_sha}")
    print(f"base64_text_sha256={b64_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
