#!/usr/bin/env python3
import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

from fastapi import FastAPI
from pydantic import BaseModel


class DecideRequest(BaseModel):
    state: Any
    questions: dict
    calibrated: bool = True


DecideFn = Callable[[Any, dict, bool], Mapping[str, Any]]


def build_app(decide_fn: DecideFn) -> FastAPI:
    """Build the v0.2 HTTP shim without loading the upstream model."""

    app = FastAPI(title="JevLite v0.2 full-context shim")

    @app.post("/decide")
    def decide(body: DecideRequest):
        return decide_fn(body.state, body.questions, body.calibrated)

    return app


def load_upstream_serve(upstream_dir: Path):
    sys.path.insert(0, str(upstream_dir))
    spec = importlib.util.spec_from_file_location(
        "open_jev_upstream_serve",
        upstream_dir / "05_serve.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load pinned upstream 05_serve.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-dir", required=True)
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--max-len", type=int, default=4096)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    upstream = Path(args.upstream_dir).resolve()
    serve = load_upstream_serve(upstream)
    engine = serve.load(args.ckpt)
    training_max_len = int(engine["max_len"])
    engine["max_len"] = int(args.max_len)

    if engine["max_len"] > 8192:
        raise SystemExit("inference max_len exceeds ModernBERT-base 8192-token context")

    print(
        f"loaded checkpoint training_max_len={training_max_len}; "
        f"inference_max_len={engine['max_len']}",
        flush=True,
    )

    import uvicorn

    app = build_app(serve.decide)
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
