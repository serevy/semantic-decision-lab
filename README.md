# semantic-decision-lab

**English** | [日本語](README.ja.md) | [简体中文](README.zh-CN.md) | [한국어](README.ko.md) | [Français](README.fr.md)

Experiments on semantic decision layers for AI orchestration, context selection, routing, handoffs, and real-time systems.

## Working model

This repository separates experimental work from durable project decisions.

| Artifact | Purpose | Typical contents |
|---|---|---|
| GitHub Issue | Experiment backlog and working thread | Hypothesis, setup, tasks, intermediate observations, raw results, follow-ups |
| PDDR | Durable record of an important decision | Evidence-backed adoption, rejection, deferral, scope, consequences, revisit conditions |

Running or completing an experiment does not automatically create a PDDR. Create or update a PDDR only when the evidence leads to an important Project, Product, or Process decision whose rationale should survive the Issue lifecycle.

Issues and PDDRs should link to each other when a decision is made, while keeping raw experimental detail in the Issue.

## PDDR

This repository uses [PDDR Kit](https://github.com/serevy/pddr-kit) `v0.1.0-rc.1`.

Create a record from `.pddr/template.md`, save it under `docs/records/`, and validate it before review:

```bash
cp .pddr/template.md docs/records/PDDR-0002-short-title.md
python .pddr/pddr.py validate
```

The first record, [`PDDR-0001`](docs/records/PDDR-0001-separate-experiments-from-decisions.md), defines the boundary between Issues and decision records.
