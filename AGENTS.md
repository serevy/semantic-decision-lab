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

### Pending checkpoint marker

PR本文に `## PDDR checkpoint` と `Review: pending` がある場合は、signalに関係するrecent Issues / PRs / Evidenceだけを対象にbounded auditします。

- SignalはPDDR作成義務ではありません。
- 実験開始・変更・完了やraw observationだけではPDDRへ昇格させません。
- durableなProject / Product / Process判断がなければno-opを正常結果とします。
- review後はPR本文のcurrent stateを `Review: completed` へ更新します。
- 過去のCheck / Job Summaryはsignal発生時点の履歴として扱い、同期更新しません。

At a checkpoint:

- Review recent Issues and PRs for decisions that remain important after the underlying work is closed.
- Create or update a PDDR only when the evidence has produced a durable Project, Product, or Process decision.
- Do not promote routine implementation details, raw observations, or experiment completion itself into a PDDR.
- Prefer linking existing Evidence over duplicating experiment logs.
- If no durable decision is found, record nothing; the checkpoint is an audit, not a requirement to create a PDDR.

## Validation

Run `python .pddr/pddr.py validate` after changing files under `docs/records/`.

## PDDR CI authoring defaults

Apply these defaults when adding or changing PDDR CI; see the [PDDR Kit adoption guide](https://github.com/serevy/pddr-kit/blob/main/docs/adoption.md) and [Kit issue #47](https://github.com/serevy/pddr-kit/issues/47).

- Set an explicit job timeout. Lightweight PDDR validation, checkpoint, and marker jobs use `timeout-minutes: 5`; justify a different budget from the actual work.
- Cancel superseded validator runs only within the same workflow and pull request. Include the ref and run ID in non-PR groups so separate main or manual runs remain independent.
- Keep checkpoint detection read-only, including PR body and label events and complete base/head comparison. Marker writes use trusted default-branch code in the separate `workflow_run` job, without PR code or artifacts and without cancellation.
- Preserve required-check identities, trigger/path coverage, validation flags, runtime versions, action pins, and permissions. Review those contracts before combining or splitting jobs.
- Add caching, matrices, parallel jobs, or artifacts only when their benefit justifies the extra work. A lightweight validator may share an existing read-only job only after preserving coverage, failure behavior, and check requirements.
- Record job counts and native execution time from normal CI in the PR; separate expected savings from measured results. These defaults retain existing project, review, and publication authority.
