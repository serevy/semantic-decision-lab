# semantic-decision-lab

**English** | [日本語](README.ja.md) | [简体中文](README.zh-CN.md) | [한국어](README.ko.md) | [Français](README.fr.md)

> **Provider-neutral experiments on semantic decision layers:** turning ambiguous state into typed, probabilistic decisions that deterministic systems can consume.

The core question is not “can an LLM do everything?” It is:

> **Can semantic judgment be isolated as a small, testable software primitive while deterministic code keeps control of execution, policy, and safety?**

This repository explores that question across orchestration, context selection, typed handoffs, state interpretation, domain gates, real-time systems, and interchangeable semantic-decision providers.

## Core idea

A semantic layer should answer **what the current state means**. Deterministic systems remain responsible for **what happens next**.

![Semantic decision core architecture](docs/assets/semantic-decision-core.svg)

This separation lets us test semantic judgment independently from execution logic. It also makes uncertainty, abstention, escalation, and provider replacement explicit instead of hiding them inside a monolithic agent.

## Research map

| Area | Research question | Main threads |
|---|---|---|
| Orchestration | Can semantic routing reduce cost or latency without degrading successful outcomes? | [#1 AI Work Routing](https://github.com/serevy/semantic-decision-lab/issues/1) |
| Context & memory | Can we select smaller context while preserving decision-critical information? | [#2 PDDR Context Selection](https://github.com/serevy/semantic-decision-lab/issues/2), [#74 downstream task-success evaluation](https://github.com/serevy/semantic-decision-lab/issues/74) |
| Handoffs | Can free-form agent state become a compact typed handoff without losing important constraints? | [#3 Typed Handoff](https://github.com/serevy/semantic-decision-lab/issues/3) |
| State interpretation | Can we represent decision state, pragmatic state, and semantic trajectories without inventing unsupported certainty? | [#4](https://github.com/serevy/semantic-decision-lab/issues/4), [#5](https://github.com/serevy/semantic-decision-lab/issues/5), [#9](https://github.com/serevy/semantic-decision-lab/issues/9) |
| Domain gates & discovery | Where do semantic classification, scoring, retrieval, and ranking help in bounded domain workflows? | [#6 Trading Strategy Gate](https://github.com/serevy/semantic-decision-lab/issues/6), [#7 VTuber Discovery](https://github.com/serevy/semantic-decision-lab/issues/7), [#8 Taste Discovery](https://github.com/serevy/semantic-decision-lab/issues/8) |
| Real-time / embodied | Can low-latency semantic decisions improve interactive systems while hard safety remains independent? | [#10 Real-time / Embodied Decision Layer](https://github.com/serevy/semantic-decision-lab/issues/10) |
| Provider portability | Can the same typed-decision application move across hosted and local providers without leaking provider-specific assumptions downstream? | [#81 System One provider portability](https://github.com/serevy/semantic-decision-lab/issues/81) |

The repository treats established task shapes such as classification, scoring, routing, retrieval, and verification as building blocks. The research focus is how those primitives compose into reliable software architectures and how they behave under real evaluation constraints.

## Provider-neutral by design

Jev is an important provider and reference point in this work, but it is **not the definition of the research**. Experiments aim to keep application logic behind a common typed-decision boundary wherever practical.

![Provider-neutral semantic decision architecture](docs/assets/provider-neutral-architecture.svg)

Provider comparisons keep separate dimensions separate:

- **contract compatibility** — can the same request/response shape be used?
- **semantic quality** — are decisions correct for the task?
- **calibration** — do probabilities mean what downstream automation assumes they mean?
- **robustness** — option order, context length, packing, abstention, and failure behavior
- **systems cost** — latency, memory, hardware, throughput, and external API cost

**API compatibility is not semantic parity.** A provider may be easy to swap in while behaving differently enough to require different thresholds or deployment constraints.

## How experiments work

The lab is evidence-first. Experiment design and raw evidence stay separate from durable project decisions.

![Experiment evidence and PDDR workflow](docs/assets/experiment-evidence-pddr.svg)

Common rules:

- freeze evaluation conditions before scored provider output;
- preserve first-run evidence instead of rewriting it after failures are discovered;
- version protocol, packing, dataset, or prompt changes explicitly;
- compare against deterministic and/or conventional baselines where relevant;
- distinguish coverage from correctness when a provider rejects or truncates inputs;
- treat upstream benchmark claims as related-work evidence until reproduced;
- respect provider terms before publishing provider-specific benchmark results.

## Results and visualizations

The README is intentionally **not** a live leaderboard.

Stable, frozen findings may be promoted here later as small charts or summary figures. Dense result breakdowns, provenance, diagnostics, and interactive views belong in experiment artifacts, `docs/`, or a future GitHub Pages site.

This keeps the landing page readable while avoiding a common failure mode: attractive charts that silently outlive the experiment version that produced them.

## Repository layout

| Path | Purpose |
|---|---|
| `experiments/` | Reproducible experiment code, datasets, evaluators, and evidence-oriented assets |
| `docs/records/` | Accepted PDDR decision records |
| `.pddr/` | PDDR Kit tooling, schema, validation, and checkpoint support |
| `docs/` | Supporting documentation and research notes that do not belong in the landing page |
| GitHub Issues | Hypotheses, protocols, intermediate observations, raw results, failures, and follow-ups |

For external implementations and papers that may influence future experiments, see [#70 External reference radar](https://github.com/serevy/semantic-decision-lab/issues/70).

## Issues vs PDDR

This repository separates **experimental work** from **durable project decisions**.

| Artifact | Purpose | Typical contents |
|---|---|---|
| GitHub Issue | Experiment backlog and working thread | Hypothesis, setup, tasks, intermediate observations, raw results, follow-ups |
| PDDR | Durable record of an important decision | Evidence-backed adoption, rejection, deferral, scope, consequences, revisit conditions |

Running or completing an experiment does **not** automatically create a PDDR. Create or update one only when evidence leads to an important Project, Product, or Process decision whose rationale should survive the Issue lifecycle.

Issues and PDDRs should link to each other when a durable decision is made, while raw experimental detail remains in the Issue or experiment evidence.

## PDDR

This repository uses [PDDR Kit](https://github.com/serevy/pddr-kit) `v0.2.1`.

It also uses the hardened optional checkpoint CI. The PR-head signal workflow is read-only, while marker writes are handled by a trusted default-branch writer. A checkpoint signal requests a bounded review; it does not mean a PDDR is required, and routine experiment completion is not promoted automatically.

Create a record from `.pddr/template.md`, save it under `docs/records/`, and validate it before review:

```bash
cp .pddr/template.md docs/records/PDDR-0002-short-title.md
python .pddr/pddr.py validate
```

The first record, [`PDDR-0001`](docs/records/PDDR-0001-separate-experiments-from-decisions.md), defines the boundary between Issues and durable decision records.

## Documentation direction

`README.md` is the landing page and source README. The existing readme-i18n workflow propagates stabilized README content to translated versions.

As the project accumulates stable experiment results, richer architecture diagrams, result dashboards, and deeper methodology pages can move to GitHub Pages without turning the README into a documentation wall.

---

**Current documentation refresh:** [#83](https://github.com/serevy/semantic-decision-lab/issues/83)
