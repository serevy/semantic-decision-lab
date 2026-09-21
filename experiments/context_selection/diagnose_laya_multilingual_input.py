#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
import types
from collections import defaultdict
from pathlib import Path

from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer

from laya_multilingual_provider import build_laya_question


SOURCE_REVISION = "42626c348753fbb17572a813127df2278a1ec527"
MODEL_ID = "convaiinnovations/laya-multilingual"
MODEL_REVISION = "4bb4d65403a3a7b8abd9e6876ccb5e75cf923b5c"
MAX_LEN = 4096
HEAD_MAX_LEN = 256


def load_docs(path: Path) -> dict[str, str]:
    docs = {}
    for p in sorted(path.glob("PDDR-*.md")):
        if p.stem.startswith("PDDR-"):
            docs[p.stem[:9]] = p.read_text()
    return docs


def sha256_ints(values: list[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(int(value).to_bytes(4, "little", signed=False))
    return digest.hexdigest()


def import_laya_common(source_dir: Path):
    """Import Laya's pure token-packing helpers without installing torch.

    The diagnostic only uses build_sequence/render_options. The pinned common.py
    imports torch because model/training helpers live in the same module, so
    provide the minimum import-time symbols required for class/function
    definitions.
    """
    torch_stub = types.ModuleType("torch")
    nn_stub = types.ModuleType("torch.nn")

    class Module:
        pass

    class Tensor:
        pass

    class DType:
        pass

    nn_stub.Module = Module
    torch_stub.nn = nn_stub
    torch_stub.Tensor = Tensor
    torch_stub.dtype = DType
    torch_stub.bfloat16 = object()
    torch_stub.float16 = object()

    previous = {
        name: sys.modules.get(name)
        for name in ("torch", "torch.nn")
    }
    sys.modules["torch"] = torch_stub
    sys.modules["torch.nn"] = nn_stub

    spec = importlib.util.spec_from_file_location(
        "laya_common_pinned",
        source_dir / "laya" / "common.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load pinned Laya common.py")
    common = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(common)
    finally:
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    return common


def load_tokenizer(model_dir: Path | None):
    if model_dir is not None:
        return AutoTokenizer.from_pretrained(model_dir / "tokenizer")
    return AutoTokenizer.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        subfolder="tokenizer",
    )


def load_checkpoint_config(model_dir: Path | None) -> dict:
    if model_dir is not None:
        path = model_dir / "rl_agent_config.json"
    else:
        path = Path(
            hf_hub_download(
                repo_id=MODEL_ID,
                revision=MODEL_REVISION,
                filename="rl_agent_config.json",
            )
        )
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases")
    parser.add_argument("corpus_dir")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--model-dir")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    model_dir = Path(args.model_dir).resolve() if args.model_dir else None
    common = import_laya_common(source_dir)
    tok = load_tokenizer(model_dir)
    checkpoint_cfg = load_checkpoint_config(model_dir)

    if int(checkpoint_cfg.get("max_len", 0)) != 1024:
        raise SystemExit(f"unexpected checkpoint max_len: {checkpoint_cfg.get('max_len')}")
    if int(checkpoint_cfg.get("head_max_len", 0)) != HEAD_MAX_LEN:
        raise SystemExit(
            f"unexpected checkpoint head_max_len: {checkpoint_cfg.get('head_max_len')}"
        )
    if int(getattr(tok, "model_max_length", 0)) < MAX_LEN:
        raise SystemExit(
            f"tokenizer model_max_length={tok.model_max_length} < frozen max_len={MAX_LEN}"
        )

    cases = json.loads(Path(args.cases).read_text())
    docs = load_docs(Path(args.corpus_dir))
    results = []
    hashes_by_record: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for case in cases:
        for pddr_id in case["corpus"]:
            qdef = build_laya_question(task=case["task"], pddr_id=pddr_id)
            q = {
                "t": qdef["type"],
                "ins": qdef["instructions"],
                "crit": qdef["criteria"],
            }

            mask_tok = tok.mask_token
            head_raw = tok(
                "%s question: %s" % (
                    q["t"],
                    str(q["ins"]).replace(mask_tok, " "),
                ),
                add_special_tokens=False,
            )["input_ids"]

            rendered_options = common.render_options(q)
            option_rows = []
            option_ids = []
            for option in rendered_options:
                full = tok(
                    " " + option.replace(mask_tok, " "),
                    add_special_tokens=False,
                )["input_ids"]
                initial = [tok.mask_token_id] + full[:48]
                option_rows.append(
                    {
                        "rendered": option,
                        "raw_token_count": len(full) + 1,
                        "truncated_by_48_cap": len(full) > 48,
                    }
                )
                option_ids.append(initial)

            original_option_lengths = [len(x) for x in option_ids]
            opt_budget = HEAD_MAX_LEN - sum(original_option_lengths)
            head_budget = max(8, opt_budget)
            if opt_budget < 16:
                per = max(4, (HEAD_MAX_LEN - 16) // max(1, len(option_ids)))
                option_ids = [o[:per] for o in option_ids]
                opt_budget = HEAD_MAX_LEN - sum(len(o) for o in option_ids)
                head_budget = max(8, opt_budget)

            further_option_truncation = [
                max(0, before - len(after))
                for before, after in zip(original_option_lengths, option_ids)
            ]
            head_dropped = max(0, len(head_raw) - head_budget)

            prefix_len = (
                1
                + min(len(head_raw), head_budget)
                + 1
                + sum(len(o) for o in option_ids)
                + 1
            )
            state_room = max(0, MAX_LEN - prefix_len - 1)
            state_tokens = tok(
                common.serialize_state(docs[pddr_id]).replace(mask_tok, " "),
                add_special_tokens=False,
            )["input_ids"]
            state_dropped = max(0, len(state_tokens) - state_room)

            seq, markers = common.build_sequence(
                tok,
                docs[pddr_id],
                q,
                MAX_LEN,
                HEAD_MAX_LEN,
            )

            option_cap_truncated = any(
                row["truncated_by_48_cap"] for row in option_rows
            )
            option_budget_truncated = any(x > 0 for x in further_option_truncation)

            if head_dropped:
                raise SystemExit(
                    f"{case['case_id']} {pddr_id}: question instructions truncated "
                    f"by {head_dropped} tokens"
                )
            if option_cap_truncated or option_budget_truncated:
                raise SystemExit(
                    f"{case['case_id']} {pddr_id}: one or more criteria were truncated"
                )
            if state_dropped:
                raise SystemExit(
                    f"{case['case_id']} {pddr_id}: PDDR state truncated "
                    f"by {state_dropped} tokens"
                )
            if len(markers) != 3:
                raise SystemExit(
                    f"{case['case_id']} {pddr_id}: expected 3 markers, got {len(markers)}"
                )

            input_hash = sha256_ints(seq)
            hashes_by_record[pddr_id].append((case["case_id"], input_hash))
            results.append(
                {
                    "case_id": case["case_id"],
                    "pddr_id": pddr_id,
                    "max_len": MAX_LEN,
                    "head_max_len": HEAD_MAX_LEN,
                    "head_token_count": len(head_raw),
                    "head_budget": head_budget,
                    "head_dropped_token_count": head_dropped,
                    "option_token_counts": [
                        row["raw_token_count"] for row in option_rows
                    ],
                    "option_truncated": (
                        option_cap_truncated or option_budget_truncated
                    ),
                    "state_token_count": len(state_tokens),
                    "state_room": state_room,
                    "state_dropped_token_count": state_dropped,
                    "marker_count": len(markers),
                    "input_ids_count": len(seq),
                    "input_ids_sha256": input_hash,
                }
            )

    cross_case_checks = {}
    for pddr_id, items in sorted(hashes_by_record.items()):
        hashes = [h for _, h in items]
        distinct = len(set(hashes)) == len(hashes)
        cross_case_checks[pddr_id] = {
            "cases": [
                {"case_id": case_id, "input_ids_sha256": digest}
                for case_id, digest in items
            ],
            "all_case_inputs_distinct": distinct,
        }
        if not distinct:
            raise SystemExit(
                f"{pddr_id}: identical final input detected across different tasks"
            )

    output = {
        "experiment_version": "laya-multilingual-v0.1",
        "source_revision": SOURCE_REVISION,
        "model_repository": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "checkpoint_default_max_len": checkpoint_cfg["max_len"],
        "checkpoint_default_head_max_len": checkpoint_cfg["head_max_len"],
        "inference_max_len": MAX_LEN,
        "inference_head_max_len": HEAD_MAX_LEN,
        "requests_checked": len(results),
        "all_questions_fully_preserved": all(
            row["head_dropped_token_count"] == 0 for row in results
        ),
        "all_options_fully_preserved": all(
            not row["option_truncated"] for row in results
        ),
        "all_records_fully_preserved": all(
            row["state_dropped_token_count"] == 0 for row in results
        ),
        "cross_case_checks": cross_case_checks,
        "diagnostic": results,
    }

    Path(args.output).write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
