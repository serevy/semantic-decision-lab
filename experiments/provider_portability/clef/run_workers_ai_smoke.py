from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from contract import load_fixture, validate_response


ROOT = Path(__file__).resolve().parent


def canonical_json(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        default=str(ROOT / "systemone-contract.v0.1.json"),
    )
    parser.add_argument("--model", choices=("clef", "clef-flash"), default="clef-flash")
    parser.add_argument("--output")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    fixture = load_fixture(args.fixture)
    request_body = json.loads(json.dumps(fixture["request"]))
    request_body["model"] = args.model
    request_sha256 = hashlib.sha256(canonical_json(request_body)).hexdigest()
    model_id = f"@cf/cloudflare/{args.model}"

    if args.dry_run:
        print(
            json.dumps(
                {
                    "mode": "dry-run",
                    "transport": "Cloudflare Workers AI REST API",
                    "url_template": (
                        "https://api.cloudflare.com/client/v4/accounts/"
                        "{CLOUDFLARE_ACCOUNT_ID}/ai/run/" + model_id
                    ),
                    "model_id": model_id,
                    "request_sha256": request_sha256,
                    "request": request_body,
                    "required_environment": [
                        "CLOUDFLARE_ACCOUNT_ID",
                        "CLOUDFLARE_AUTH_TOKEN",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    auth_token = os.environ.get("CLOUDFLARE_AUTH_TOKEN")
    if not account_id or not auth_token:
        raise SystemExit(
            "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_AUTH_TOKEN are required for a live run"
        )
    if not args.output:
        raise SystemExit("--output is required for a live run")

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/ai/run/{model_id}"
    )
    request = urllib.request.Request(
        url,
        data=canonical_json(request_body),
        headers={
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            raw_body = response.read()
            http_status = response.status
    except urllib.error.HTTPError as exc:
        raw_body = exc.read()
        raise RuntimeError(
            f"Workers AI returned HTTP {exc.code}: "
            f"{raw_body.decode('utf-8', errors='replace')}"
        ) from exc
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    payload = json.loads(raw_body)
    normalized = validate_response(
        payload,
        request_body,
        probability_tolerance=float(
            fixture["contract_expectations"]["probability_tolerance_after_rounding"]
        ),
    )

    evidence = {
        "schema_version": "0.1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "cloudflare-workers-ai",
        "model_id": model_id,
        "model_selector": args.model,
        "hosted_model_revision": None,
        "hosted_revision_note": (
            "Workers AI exposes a model alias here; no immutable underlying model "
            "revision is recorded by this runner."
        ),
        "request_sha256": request_sha256,
        "http_status": http_status,
        "elapsed_ms_client_observed": elapsed_ms,
        "request": request_body,
        "raw_response": payload,
        "normalized_systemone_response": normalized,
    }

    output = Path(args.output)
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing evidence: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
