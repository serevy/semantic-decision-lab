#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "downstream-run.openai-luna-v0.1.json"
ALLOWED = {"A", "B", "C", "D", "ABSTAIN"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def execution_key(salt: str, request_id: str) -> str:
    return hashlib.sha256((salt + "\n" + request_id).encode("utf-8")).hexdigest()


def exact_choice(text: str) -> str | None:
    normalized = text.strip().upper()
    return normalized if normalized in ALLOWED else None


def write_checkpoint(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def post_chat_completion(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    system: str,
    user: str,
    sampling: dict,
    timeout: int,
) -> tuple[dict, dict[str, str]]:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "reasoning_effort": sampling["reasoning_effort"],
        "temperature": sampling["temperature"],
        "max_completion_tokens": sampling["max_completion_tokens"],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "semantic-decision-lab-downstream-v0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            headers = {
                key.lower(): value
                for key, value in response.headers.items()
                if key.lower()
                in {
                    "x-request-id",
                    "x-ratelimit-limit-requests",
                    "x-ratelimit-remaining-requests",
                    "x-ratelimit-reset-requests",
                }
            }
            return data, headers
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"transport error: {exc}") from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = json.loads(CONFIG.read_text())
    raw_requests = args.requests.read_bytes()
    actual_digest = sha256_bytes(raw_requests)
    expected_digest = config["request_pack"]["file_sha256"]
    if actual_digest != expected_digest:
        raise SystemExit(
            f"request-pack digest mismatch: expected {expected_digest}, got {actual_digest}"
        )

    rows = read_jsonl(args.requests)
    if len(rows) != config["request_pack"]["request_count"]:
        raise SystemExit(
            f"expected {config['request_pack']['request_count']} requests, got {len(rows)}"
        )
    request_ids = [row["request_id"] for row in rows]
    if len(request_ids) != len(set(request_ids)):
        raise SystemExit("duplicate request_id in frozen request pack")

    salt = config["execution"]["order_salt"]
    rows.sort(key=lambda row: execution_key(salt, row["request_id"]))
    order_digest = sha256_bytes(
        ("\n".join(row["request_id"] for row in rows) + "\n").encode("utf-8")
    )

    if args.dry_run:
        print(
            "downstream OpenAI Luna run config valid: "
            f"{len(rows)} requests, request_sha256={actual_digest}, "
            f"order_sha256={order_digest}, no API call made"
        )
        return

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required for live execution")

    started_at = now_iso()
    payload = {
        "run": {
            "run_id": config["run_id"],
            "provider": config["provider"]["name"],
            "api": config["provider"]["api"],
            "endpoint": config["provider"]["endpoint"],
            "model": config["provider"]["model"],
            "executed_at": started_at,
            "completed_at": None,
            "sampling": config["sampling"],
            "execution": config["execution"],
            "request_pack_sha256": actual_digest,
            "execution_order_sha256": order_digest,
            "config_sha256": sha256_bytes(CONFIG.read_bytes()),
        },
        "responses": [],
        "errors": [],
    }
    write_checkpoint(args.output, payload)

    interval = float(config["execution"]["minimum_request_start_interval_seconds"])
    timeout = int(config["execution"]["request_timeout_seconds"])
    previous_start: float | None = None
    parse_errors = 0

    for index, row in enumerate(rows, 1):
        if previous_start is not None:
            wait = interval - (time.monotonic() - previous_start)
            if wait > 0:
                time.sleep(wait)
        previous_start = time.monotonic()

        request_started_at = now_iso()
        try:
            response, response_headers = post_chat_completion(
                endpoint=config["provider"]["endpoint"],
                api_key=api_key,
                model=config["provider"]["model"],
                system=row["system"],
                user=row["user"],
                sampling=config["sampling"],
                timeout=timeout,
            )
        except Exception as exc:
            payload["errors"].append(
                {
                    "request_id": row["request_id"],
                    "prompt_sha256": row["prompt_sha256"],
                    "started_at": request_started_at,
                    "error": str(exc),
                }
            )
            write_checkpoint(args.output, payload)
            print(
                f"[{index}/{len(rows)}] {row['request_id']}: transport/API failure",
                file=sys.stderr,
            )
            raise

        try:
            choice_obj = response["choices"][0]
            message = choice_obj["message"]
            raw_text = message.get("content") or ""
            finish_reason = choice_obj.get("finish_reason")
        except (KeyError, IndexError, TypeError) as exc:
            payload["errors"].append(
                {
                    "request_id": row["request_id"],
                    "prompt_sha256": row["prompt_sha256"],
                    "started_at": request_started_at,
                    "error": "malformed Chat Completions response",
                }
            )
            write_checkpoint(args.output, payload)
            raise RuntimeError("malformed Chat Completions response") from exc

        parsed = exact_choice(raw_text)
        parse_error = None
        if parsed is None:
            parse_errors += 1
            parse_error = "response was not an exact allowed choice"

        payload["responses"].append(
            {
                "request_id": row["request_id"],
                "prompt_sha256": row["prompt_sha256"],
                "choice": parsed,
                "raw_response": raw_text,
                "parse_error": parse_error,
                "request_started_at": request_started_at,
                "response_id": response.get("id"),
                "returned_model": response.get("model"),
                "system_fingerprint": response.get("system_fingerprint"),
                "finish_reason": finish_reason,
                "usage": response.get("usage"),
                "response_headers": response_headers,
            }
        )
        write_checkpoint(args.output, payload)
        print(
            f"[{index}/{len(rows)}] {row['request_id']}: "
            f"{parsed if parsed is not None else 'PARSE_ERROR'}"
        )

    payload["run"]["completed_at"] = now_iso()
    write_checkpoint(args.output, payload)

    if parse_errors:
        raise SystemExit(
            f"completed API calls but found {parse_errors} exact-choice parse error(s)"
        )
    print(f"completed downstream run: {len(rows)} responses, 0 parse errors")


if __name__ == "__main__":
    main()
