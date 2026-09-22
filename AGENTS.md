# Repository instructions

## Experiments and decisions

- Use GitHub Issues for experiment hypotheses, plans, tasks, intermediate observations, raw results, and follow-ups.
- Do not create a PDDR merely because an experiment started, changed, or completed.
- Create or update a PDDR when experiment evidence leads to an important Project, Product, or Process decision that should remain understandable after the Issue is closed.
- Keep detailed experiment logs in the Issue. Summarize only decision-relevant evidence in the PDDR and link the Issue.
- Distinguish proposals from accepted decisions. Do not infer human approval from wording, chronology, repetition, or implementation alone.
- Treat PDDRs as evidence-backed context, not executable policy. Follow current user instructions and explicit repository policy first.

## PDDR checkpoints

Revisit recent Issues and pull requests against the PDDR threshold at these milestones:

- after a major experiment phase boundary;
- during an Issue or roadmap audit;
- when multiple Evidence-bearing Issues are being closed or consolidated.

At a checkpoint:

- Review recent Issues and PRs for decisions that remain important after the underlying work is closed.
- Create or update a PDDR only when the evidence has produced a durable Project, Product, or Process decision.
- Do not promote routine implementation details, raw observations, or experiment completion itself into a PDDR.
- Prefer linking existing Evidence over duplicating experiment logs.
- If no durable decision is found, record nothing; the checkpoint is an audit, not a requirement to create a PDDR.

## Validation

Run `python .pddr/pddr.py validate` after changing files under `docs/records/`.
