---
id: PDDR-0001
title: Separate experiments from durable decisions
decision_date: 2026-09-18
recorded_date: 2026-09-18
decision_status: accepted
delivery_status: validated
scope:
  - project
  - process
owners:
  - serevy
evidence:
  - "Maintainer direction, 2026-09-18"
  - "README.md"
  - "AGENTS.md"
  - ".github/ISSUE_TEMPLATE/experiment.yml"
  - "https://github.com/serevy/semantic-decision-lab/pull/11"
  - "https://github.com/serevy/semantic-decision-lab/actions/runs/35356756165"
  - "Repository issue audit and durable-decision review, 2026-09-22"
related:
  - PDDR-0002
  - PDDR-0003
  - PDDR-0004
supersedes: []
superseded_by: null
---

# PDDR-0001: Separate experiments from durable decisions

## Summary

GitHub Issues are the experiment backlog and working record. PDDRs preserve only important Project, Product, or Process decisions that result from experimental evidence.

## Context and observations

- This repository exists to run multiple experiments on semantic decision layers, context selection, routing, handoffs, and real-time systems.
- Experiments produce hypotheses, tasks, intermediate observations, raw results, and follow-up questions before they produce a stable decision.
- Recording every experiment event as a PDDR would create noise and make durable decisions harder for humans and AI to retrieve safely.
- Keeping decisions only in closed Issues would make their current status, scope, consequences, and replacement history difficult to discover later.

## Options considered

### Use Issues for experiments and decisions

- Benefits: One artifact type and minimal process overhead.
- Costs / constraints: Important decisions become mixed with task discussion and raw experiment history.
- Status: rejected

### Create a PDDR for every experiment

- Benefits: Every experiment has a durable repository record.
- Costs / constraints: High maintenance cost, duplicate evidence, and a growing context burden for humans and AI.
- Status: rejected

### Separate the experiment backlog from durable decision records

- Benefits: Issues remain flexible working threads while PDDRs provide a small, reviewable set of consequential decisions.
- Costs / constraints: Maintainers must judge when experimental evidence crosses the decision threshold and add cross-links.
- Status: accepted

## Decision

- Use GitHub Issues for hypotheses, experiment plans, tasks, intermediate observations, raw evidence, and follow-ups.
- Do not create a PDDR merely because an experiment is proposed, started, changed, completed, or unsuccessful.
- Create or update a PDDR when evidence leads to an important Project, Product, or Process decision whose rationale should remain understandable after the Issue is closed.
- Link the relevant Issue from the PDDR. After a decision record exists, link it back from the Issue when practical.
- Keep raw experimental details in the Issue and summarize only decision-relevant evidence in the PDDR.
- Preserve the distinction between a proposed conclusion and a maintainer-approved decision.

The maintainer approved this boundary on 2026-09-18.

## Delivery and validation

The boundary is documented in README and AGENTS instructions. An experiment Issue template prompts for the hypothesis, method, evidence, and possible decision impact while explicitly stating that experiment completion does not automatically require a PDDR.

The repository contains the PDDR Kit validator and a GitHub Actions workflow. PR #11 was reviewed and merged, and the PDDR validation workflow succeeded on the resulting `main` commit. The documented boundary and validation path are therefore `validated`.

2026-09-22のIssue棚卸しでは、完了した実験やbackend runを機械的にPDDR化せず、そこから残った永続的なProject / Process判断だけを再点検した。その結果、backend expansion freeze、provider-neutral evaluation contract、versioned dataset evolutionをPDDR-0002〜0004として昇格する判断を行った。これにより、「実験完了時ではなく、Evidenceがdurable decisionへ変わった時にPDDR化する」という境界を実運用で再確認した。

## Consequences

- The Issue backlog can grow without creating the same number of durable decision records.
- PDDR readers receive a curated decision history instead of a chronological experiment transcript.
- Some completed experiments will correctly have no corresponding PDDR.
- Maintainers must explicitly identify consequential decisions and preserve sufficient evidence links.
- Issue wording, recency, or volume does not give a conclusion decision authority.

## Revisit when

- Important decisions are repeatedly left only in closed Issues.
- Maintainers cannot consistently determine when a result warrants a PDDR.
- The number of PDDRs becomes a material context or maintenance burden.
- Automation is introduced to propose, classify, or retrieve decision records.

## Evidence

- Maintainer direction approving the Issue/PDDR boundary, 2026-09-18.
- `README.md`
- `AGENTS.md`
- `.github/ISSUE_TEMPLATE/experiment.yml`
- `.github/workflows/pddr.yml`
- [Adoption PR #11](https://github.com/serevy/semantic-decision-lab/pull/11)
- [Merged `main` validation](https://github.com/serevy/semantic-decision-lab/actions/runs/35356756165)
- Repository issue audit and durable-decision review, 2026-09-22.
- PDDR-0002 through PDDR-0004, promoted only after the audit identified durable decisions.

## Related records

- PDDR-0002: Freeze backend expansion after methodologically distinct coverage
- PDDR-0003: Keep semantic-provider evaluation behind one provider-neutral contract
- PDDR-0004: Evolve context-selection datasets by versioned pre-output freezes
