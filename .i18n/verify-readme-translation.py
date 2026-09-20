#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: verify-readme-translation.py SOURCE TRANSLATED")

source = Path(sys.argv[1]).read_text(encoding="utf-8")
translated = Path(sys.argv[2]).read_text(encoding="utf-8")
errors: list[str] = []

for term in ["semantic-decision-lab", "PDDR", "PDDR Kit", "GitHub Issue", "PDDR-0001"]:
    if source.count(term) != translated.count(term):
        errors.append(
            f"protected term count changed: {term!r}: "
            f"{source.count(term)} -> {translated.count(term)}"
        )

placeholder_re = re.compile(r"<<<[A-Z_]+_\d+>>>")
if placeholder_re.search(translated):
    errors.append("internal Markdown placeholder leaked into translated output")

tick = chr(96)
fence = tick * 3
fence_re = re.compile(
    r"(?ms)^" + re.escape(fence) + r"[^\n]*\n.*?^" + re.escape(fence) + r"[ \t]*$"
)
if fence_re.findall(source) != fence_re.findall(translated):
    errors.append("fenced code blocks changed")

inline_code_re = re.compile(
    r"(?<!" + re.escape(tick) + r")"
    + re.escape(tick)
    + r"[^" + re.escape(tick) + r"\n]+"
    + re.escape(tick)
    + r"(?!" + re.escape(tick) + r")"
)
if inline_code_re.findall(source) != inline_code_re.findall(translated):
    errors.append("inline code spans changed")

link_dest_re = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
if link_dest_re.findall(source) != link_dest_re.findall(translated):
    errors.append("Markdown link/image destinations changed")

heading_re = re.compile(r"(?m)^(#{1,6})\s")
if [len(x) for x in heading_re.findall(source)] != [
    len(x) for x in heading_re.findall(translated)
]:
    errors.append("heading hierarchy changed")


def prose_lines_outside_fences(text: str) -> list[str]:
    result: list[str] = []
    in_fence = False
    opening_fence = ""

    for line in text.splitlines():
        stripped = line.lstrip()
        backtick_fence = chr(96) * 3
        tilde_fence = "~" * 3

        if not in_fence and (
            stripped.startswith(backtick_fence) or stripped.startswith(tilde_fence)
        ):
            in_fence = True
            opening_fence = stripped[:3]
            continue

        if in_fence:
            if stripped.startswith(opening_fence):
                in_fence = False
                opening_fence = ""
            continue

        result.append(line)

    return result


needle_a = ".pddr/template.md"
needle_b = "docs/records/"
regression_lines = [
    line
    for line in prose_lines_outside_fences(translated)
    if needle_a in line or needle_b in line
]
if (
    len(regression_lines) != 1
    or needle_a not in regression_lines[0]
    or needle_b not in regression_lines[0]
):
    errors.append("inline-code regression prose line was split, lost, or duplicated")

if errors:
    for error in errors:
        print(f"::error::{error}")
    raise SystemExit(1)

print("README translation structural checks passed.")
