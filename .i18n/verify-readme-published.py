#!/usr/bin/env python3
"""Check committed localized READMEs against the canonical README, without API calls."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import sys

LANGUAGES = [
    ("English", "README.md"),
    ("日本語", "README.ja.md"),
    ("简体中文", "README.zh-CN.md"),
    ("한국어", "README.ko.md"),
    ("Français", "README.fr.md"),
]

if len(sys.argv) != 3:
    raise SystemExit("usage: verify-readme-published.py README.md README.<lang>.md")

source = Path(sys.argv[1])
translated = Path(sys.argv[2])
if source.name != "README.md" or translated.name not in {path for _, path in LANGUAGES if path != "README.md"}:
    raise SystemExit("expected canonical README.md and a published localized README")


def without_nav(text: str, active_file: str) -> str:
    lines = text.splitlines(keepends=True)
    if len(lines) < 4:
        raise ValueError("missing language navigation line")
    actual = lines[2].rstrip("\r\n")
    expected = " | ".join(
        f"**{label}**" if filename == active_file else f"[{label}]({filename})"
        for label, filename in LANGUAGES
    )
    if actual != expected:
        raise ValueError(f"invalid language navigation for {active_file}: {actual!r}")
    # Navigation has different self-links by design; keep all other Markdown
    # links subject to the existing strict destination and token checks.
    lines[2] = "\n"
    return "".join(lines)


try:
    left = without_nav(source.read_text(encoding="utf-8"), source.name)
    right = without_nav(translated.read_text(encoding="utf-8"), translated.name)
except ValueError as exc:
    raise SystemExit(str(exc)) from exc

with TemporaryDirectory() as temp:
    src = Path(temp) / "source.md"
    dst = Path(temp) / "translated.md"
    src.write_text(left, encoding="utf-8")
    dst.write_text(right, encoding="utf-8")
    validator = Path(__file__).with_name("verify-readme-translation.py")
    result = subprocess.run([sys.executable, str(validator), str(src), str(dst)], check=False)
    if result.returncode:
        raise SystemExit(result.returncode)
print(f"Published README structure and language navigation passed: {translated.name}")
