---
id: PDDR-0006
title: Add advisory checkpoint CI without promoting routine experiments
decision_date: 2026-09-24
recorded_date: 2026-09-24
decision_status: accepted
delivery_status: implemented
scope:
  - project
  - process
owners:
  - serevy
evidence:
  - "Maintainer approved early adoption of hardened checkpoint CI, 2026-09-24 (private)"
  - "https://github.com/serevy/pddr-kit/releases/tag/v0.2.1"
  - ".pddr/pddr_checkpoint.py"
  - ".github/workflows/pddr-checkpoint.yml"
  - ".github/workflows/pddr-checkpoint-marker.yml"
related:
  - PDDR-0001
supersedes: []
superseded_by: null
---

# PDDR-0006: Add advisory checkpoint CI without promoting routine experiments

## Summary

Semantic Decision Labで重要判断の取りこぼしを減らすため、PDDR Kit v0.2.1のoptional checkpoint CIをrepository-side advisory safety netとして導入する。

CIは実験開始・変更・完了を自動的にPDDRへ昇格させず、high-confidence signalに対してbounded auditを促すだけとする。

## Context and observations

- PDDR-0001で、Issuesをexperiment backlog / working record、PDDRをdurable decision recordとして分離した。
- repositoryは実験数が多く、Agent Skillが常時activeでない変更経路ではmilestone audit自体を取りこぼす可能性がある。
- PR本文のcheckpoint sectionは既に実運用上のreview surfaceとして使われている。
- 自動化がPDDR requiredを判定すると、実験完了数に比例してPDDRを増やす誤ったquotaを再導入する。
- PDDR Kit v0.2.1では、PR headを観測するread-only workflowとtrusted default-branch writerへ権限分離されたCheckpoint CIが提供されている。

## Options considered

### Agent / AGENTS guidanceだけを使う

- Benefits: workflow追加なしで軽量。
- Costs / constraints: Agent contextが読み込まれない変更経路ではcheckpoint signalが残らない。
- Status: rejected as the only mechanism

### 実験完了を自動でPDDR候補にする

- Benefits: 見落としは減らしやすい。
- Costs / constraints: PDDR-0001のexperiment / decision境界を壊し、noiseを大量に増やす。
- Status: rejected

### High-confidence signalだけのadvisory CIを追加する

- Benefits: existing boundaryを維持しつつreview漏れを補完できる。
- Costs / constraints: 最終的なsemantic auditはAgent / maintainerに残る。
- Status: accepted

## Decision

- PDDR Kit v0.2.1のhardened Checkpoint CIを導入する。
- signal workflowはPR headを観測するがread-onlyとする。
- PR本文 / commentへのwriteはdefault branchのtrusted `workflow_run` writerだけが担当する。
- privileged writerはPR headのcode / artifactを実行しない。
- Checkpoint SignalはPDDR requiredを意味しない。
- 実験開始・変更・完了、raw observation、backend runだけではPDDRを作成しない。
- durableなProject / Product / Process判断がEvidenceから生じた場合のみPDDRを作成・更新する。
- no durable decisionならno-opを正常結果とする。
- PDDR-0001のexperiment / decision境界を維持する。

## Delivery and validation

detector、read-only signal workflow、trusted marker writer、AGENTS pending-marker guidanceを実装した。

PDDR Kit v0.2.1側では同じ2段構成がgreenfield exampleでE2E検証済みである。Semantic Decision Lab自身では、writerがdefault branchへ入る前の導入PRではwrite pathを検証できないため、現時点のdeliveryは `implemented` とする。

導入後のhigh-signal PRでpending marker write、bounded audit、completed回収を確認した時点で `validated` を再評価する。

## Consequences

- Agent contextが一時的に失われてもcheckpoint候補をrepo側へ残せる。
- 実験量が多くてもPDDR量を機械的に増やさない。
- Issue / experiment logとdurable PDDRの責務分離を維持できる。
- write-capable tokenとPR head code executionを同じjobに置かない。
- GitHub Actions workflowが増えるが、provider / experiment runtimeには影響しない。

## Revisit when

- false positive / false negativeが継続する場合。
- Evidence-bearing Issue consolidationを安全にsignal化できる場合。
- experiment / decision boundary自体を見直すEvidenceが出た場合。
- GitHub Actions以外へCIを移行する場合。

## Evidence

- Maintainer approval of early hardened checkpoint CI adoption, 2026-09-24 (private).
- [PDDR Kit v0.2.1](https://github.com/serevy/pddr-kit/releases/tag/v0.2.1)
- `.pddr/pddr_checkpoint.py`
- `.github/workflows/pddr-checkpoint.yml`
- `.github/workflows/pddr-checkpoint-marker.yml`
- `AGENTS.md`

## Related records

- PDDR-0001: Separate experiments from durable decisions
