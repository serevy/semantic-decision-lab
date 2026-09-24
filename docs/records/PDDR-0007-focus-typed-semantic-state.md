---
id: PDDR-0007
title: Focus research contribution on typed semantic state and downstream fidelity
decision_date: 2026-09-25
recorded_date: 2026-09-25
decision_status: accepted
delivery_status: implemented
scope:
  - project
owners:
  - serevy
evidence:
  - "https://github.com/serevy/semantic-decision-lab/issues/70"
  - "https://github.com/serevy/semantic-decision-lab/issues/1"
  - "https://github.com/serevy/semantic-decision-lab/issues/2"
  - "https://github.com/serevy/semantic-decision-lab/issues/3"
  - "https://github.com/serevy/semantic-decision-lab/issues/4"
  - "https://github.com/serevy/semantic-decision-lab/issues/5"
  - "https://github.com/serevy/semantic-decision-lab/issues/9"
  - "https://github.com/serevy/semantic-decision-lab/issues/10"
  - "https://github.com/serevy/semantic-decision-lab/issues/81"
  - "Maintainer approval in project chat, 2026-09-25 (private)"
  - "https://github.com/serevy/semantic-decision-lab/pull/101"
related:
  - PDDR-0001
  - PDDR-0003
  - PDDR-0005
supersedes: []
superseded_by: null
---

# PDDR-0007: Focus research contribution on typed semantic state and downstream fidelity

## Summary

A 2026-09-25 prior-art refresh across academic research, open-source implementations, and patent publications found that several primitives already used by Semantic Decision Lab have substantial existing work: model routing/cascading, context and prompt compression, structured agent handoff, dialogue/action-state tracking, pragmatic-language evaluation, trajectory/process supervision, high-level embodied planning with grounded control, and intermediate representations.

This record keeps those primitives as reusable building blocks and moves the Lab's project-level research boundary upward:

> Represent ambiguous semantic judgment as typed, uncertainty-aware state and transitions that preserve downstream behavior, remain provider-portable where practical, and stay subordinate to deterministic execution, authorization, and hard safety.

The individual Experiments remain useful as evaluation surfaces. The accepted change is where the Lab claims research contribution and where new implementation effort should be spent.

## Context and observations

- #1 already recognized generic model routing as an established TypeSafe/Jev use-case family. Broader literature now includes mature routing/cascading frameworks and reusable implementations such as RouteLLM.
- #2 already separated generic retrieval from the PDDR-specific question. Prompt-compression systems such as LongLLMLingua reinforce that token/context reduction itself is not the distinctive research target.
- #3 has direct overlapping 2026 work showing that schema-constrained or action-state handoffs can outperform free-form narrative summaries on downstream constraint preservation.
- #4 sits adjacent to mature Dialogue State Tracking / Action State Tracking and newer formal authorization work, but its reaction-versus-approval-versus-execution-authorization boundary remains a useful domain-specific semantic question.
- #5 can reuse existing pragmatics surveys and benchmarks instead of constructing the basic phenomenon taxonomy from scratch.
- #9 is adjacent to established trajectory/process-supervision work. The stronger question is whether typed semantic transitions provide useful reusable structure across domains.
- #10's broad high-level semantic planning + grounded low-level control pattern is established by embodied-agent work such as SayCan.
- #81 is adjacent to growing typed-IR work; the useful research boundary is semantic/provider portability rather than the existence of an IR itself.
- Patent publications also cover nearby routing, prompt compression, explicit approval gates, agent risk actions, and LLM-generated IR patterns. These references are landscape evidence only and are not a freedom-to-operate conclusion.
- Recent Bonsai 2 ternary refusal/abliteration experiments provide adjacent robustness evidence that learned refusal behavior can shift sharply under targeted weight intervention while broad benchmark capability changes much less in the reported paired evaluations. The same work also exposed empty-completion and context-truncation evaluation traps. This does not equate refusal with authorization, but it strengthens the decision to keep semantic-model behavior separate from deterministic authorization and hard-safety authority.
- Existing frozen experiment evidence must not be retroactively changed to incorporate newly discovered baselines.

## Options considered

### Continue treating each semantic primitive as a separate novelty target

- Description: Keep routing, compression, typed handoff, trajectory evaluation, and IR boundaries as primary research claims.
- Benefits: Minimal changes to current experiment titles and descriptions.
- Costs / constraints: Duplicates mature external work, spends implementation time rebuilding available components, and weakens the Lab's shared research identity.
- Status: rejected

### Drop Experiments that overlap prior art

- Description: Close or remove overlapping Experiments and keep only apparently novel topics.
- Benefits: Narrow backlog and fewer experiments.
- Costs / constraints: Loses valuable evaluation surfaces, domain evidence, and reusable baselines. Prior art does not make a bounded empirical question useless.
- Status: rejected

### Keep the Experiments but move the common research boundary upward

- Description: Reuse established routing, retrieval, compression, handoff, pragmatics, trajectory, embodied-planning, and IR techniques as baselines/building blocks while focusing on typed semantic state, uncertainty, transitions, downstream behavioral fidelity, provider portability, and deterministic authority boundaries.
- Benefits: Reduces reinvention, preserves existing evidence, creates a clearer cross-domain Lab identity, and leaves individual Experiments useful as testbeds.
- Costs / constraints: Requires careful wording so the repository does not imply novelty for established primitives; some Experiment protocols need future versioned baseline additions rather than retroactive edits.
- Status: accepted

## Decision

**Accepted on 2026-09-25 by the maintainer.**

- Treat established semantic primitives as building blocks, not project-level novelty claims.
- Keep #1/#2/#3/#4/#5/#9/#10/#81 as bounded Experiments and evaluation surfaces.
- Prefer reuse of external methods and OSS where licensing permits instead of rebuilding equivalent components.
- Center cross-project research contribution on:
  - typed semantic state;
  - explicit uncertainty / abstention;
  - typed semantic transitions over time;
  - downstream behavioral / constraint fidelity;
  - provider capability and semantic portability;
  - separation of semantic inference from deterministic execution, authorization, policy, and hard safety.
- Do not retroactively mutate frozen experiment evidence. New prior-art baselines enter only through explicitly versioned future experiments.
- Route patent-relevant commercialization or filing questions through IP Radar / claim-level review before drawing freedom-to-operate or patentability conclusions.

## Delivery and validation

Implemented.

As part of the same prior-art refresh, Issues #1, #2, #3, #4, #5, #9, #10, #70, and #81 were updated with:
- established-prior-art boundaries;
- reusable baseline/reference candidates;
- revised Lab-specific research focus;
- explicit preservation of frozen evidence where applicable.

Maintainer approval was confirmed on 2026-09-25. README/research-map wording is updated in the same PR to reflect the accepted project boundary.

Validation checks:
- README/research-map wording does not imply novelty for established primitives;
- future Experiment versions should cite/reuse appropriate prior work before custom implementation;
- frozen historical evidence remains unchanged;
- downstream-fidelity and authority-boundary metrics appear in the relevant future protocols.

## Consequences

- The Lab becomes less of an “idea catalog for semantic classifiers” and more of a study of semantic state as a composable software boundary.
- Existing Experiments are retained, but their novelty claims become narrower and more defensible.
- More engineering effort can go to evaluation design, state semantics, calibration, transition behavior, and downstream effects instead of rebuilding routers/compressors/protocols.
- External OSS can accelerate experiments, but licensing must be checked before code reuse. A paper or public repository alone does not imply reusable code rights.
- Patent-landscape evidence is tracked as risk/context, not as a legal conclusion.
- Provider-neutrality remains important, but wire/API compatibility must not be confused with semantic parity.

## Revisit when

- Evidence shows that one of the proposed “established building blocks” is materially unsuitable as a baseline for the Lab's workloads.
- A new experiment demonstrates that typed semantic state does not improve downstream behavior or portability enough to justify the abstraction.
- Provider semantics cannot be normalized without substantial application-specific branching.
- A patent filing or commercialization path requires a narrower claim-level prior-art/FTO analysis.
- A future research area emerges that does not fit the typed-state / downstream-fidelity boundary.

## Evidence

- [#70 External reference radar](https://github.com/serevy/semantic-decision-lab/issues/70)
- [#1 AI Work Routing](https://github.com/serevy/semantic-decision-lab/issues/1)
- [#2 PDDR Context Selection](https://github.com/serevy/semantic-decision-lab/issues/2)
- [#3 Typed Handoff](https://github.com/serevy/semantic-decision-lab/issues/3)
- [#4 Decision State Classification](https://github.com/serevy/semantic-decision-lab/issues/4)
- [#5 Pragmatic State](https://github.com/serevy/semantic-decision-lab/issues/5)
- [#9 Semantic Trajectory State](https://github.com/serevy/semantic-decision-lab/issues/9)
- [#10 Real-time / Embodied Decision Layer](https://github.com/serevy/semantic-decision-lab/issues/10)
- [#81 System One provider portability / local backend matrix](https://github.com/serevy/semantic-decision-lab/issues/81)
- RouteLLM: https://github.com/lm-sys/RouteLLM
- LongLLMLingua: https://github.com/microsoft/LLMLingua
- State Compression in Two-Agent LLM Relays: https://arxiv.org/abs/2607.18265
- PACT: https://arxiv.org/abs/2606.05304
- ABCD / Action State Tracking: https://arxiv.org/abs/2104.00783
- CEI pragmatic reasoning benchmark: https://arxiv.org/abs/2603.09993
- TrajAD: https://arxiv.org/abs/2602.06443
- SayCan: https://arxiv.org/abs/2204.01691
- SkCC: https://arxiv.org/abs/2605.03353
- FAVA: https://arxiv.org/abs/2607.27267
- Bonsai 2 uncensored shootout: https://huggingface.co/spaces/BoldingBuilds/bonsai-2-uncensored-shootout
- Hikari ternary Bonsai 2 abliterated preview: https://huggingface.co/Hikari07jp/Ternary-Bonsai-2-27B-Abliterated-GGUF
- BoldingBuilds ternary Bonsai 2 abliterated PTQ1_0: https://huggingface.co/BoldingBuilds/Ternary-Bonsai-2-27B-Abliterated-PTQ1_0-GGUF
- Prompt routing patent publication: https://patents.google.com/patent/WO2025038558A1/en
- Multi-stage prompt compression patent: https://patents.google.com/patent/US12632446B1/en
- LLM-agent API approval patent: https://patents.google.com/patent/KR102707512B1/en
- Agent-browser risk approval publication: https://patents.google.com/patent/US20260067335A1/en
- LLM-generated IR publication: https://patents.google.com/patent/US20250306874A1/en

- [PR #101: prior art scope refresh](https://github.com/serevy/semantic-decision-lab/pull/101)
- `README.md` research boundary / research-map update

## Related records

- PDDR-0001: Separate experiments from durable decisions
- PDDR-0003: Keep semantic-provider evaluation behind one provider-neutral contract
- PDDR-0005: Evaluate context selection through frozen downstream decision behavior
