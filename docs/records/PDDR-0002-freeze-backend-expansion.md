---
id: PDDR-0002
title: Freeze backend expansion after methodologically distinct coverage
decision_date: 2026-09-22
recorded_date: 2026-09-22
decision_status: accepted
delivery_status: validated
scope:
  - project
  - process
owners:
  - serevy
evidence:
  - "Maintainer approval during repository audit, 2026-09-22 (private)"
  - "https://github.com/serevy/semantic-decision-lab/issues/38"
  - "https://github.com/serevy/semantic-decision-lab/pull/53"
  - "https://github.com/serevy/semantic-decision-lab/pull/56"
  - "https://github.com/serevy/semantic-decision-lab/pull/60"
  - "https://github.com/serevy/semantic-decision-lab/pull/63"
  - "https://github.com/serevy/semantic-decision-lab/pull/64"
related:
  - PDDR-0001
  - PDDR-0003
  - PDDR-0004
supersedes: []
superseded_by: null
---

# PDDR-0002: Freeze backend expansion after methodologically distinct coverage

## Summary

Experiment #2で方法論的に異なる比較armが揃った時点で、open/local backendを見つけるたびに追加する運用を停止し、dataset拡張、failure analysis、downstream評価など実験の深さを優先する。

## Context and observations

- PDDR Context Selectionでは、keyword、multilingual embedding、small typed-decision model、multilingual typed-decision model、2B Qwen-based decision head、zero-shot NLI cross-encoderなど、異なる比較点を実測した。
- 各backendの接続には、adapter、exact input preflight、runtime identity、Colab実行、raw Evidence固定が必要であり、候補数を増やすほど検証コストが増える。
- 外部ではJev互換・類似backendやbenchmark indexが継続的に増えており、候補を見つけた順に実行すると研究目的よりbackend収集が支配的になる。
- 3-case pilotではbackend間のRequired Hit差より、dataset規模、長文context、task sensitivity、packing failureなど次に検証すべき問題が明確になった。
- Issue棚卸しで、既存armと方法論的に重複する候補を追加し続けるより、datasetと評価を深くする方針が明示的に承認された。

## Options considered

### 発見したbackendを順次すべて比較する

- Benefits: backend landscapeを広く網羅できる。
- Costs / constraints: 比較armが無制限に増え、dataset・failure analysis・downstream評価が進まない。各runのprovenance維持コストも増える。
- Status: rejected

### 現在のbackend集合を永久に固定する

- Benefits: 比較条件を完全に固定できる。
- Costs / constraints: 将来、既存armでは検証できない新しい方法論やresearch questionが出ても追加できない。
- Status: rejected

### 現フェーズではbackend expansionをfreezeし、方法論的な穴がある場合だけ再開する

- Benefits: 実験の幅と深さを分離でき、候補発見を研究目的より優先しない。必要な新armは明示的なhypothesisとversionで追加できる。
- Costs / constraints: backend landscapeの網羅性は目的にしないため、新しい実装を即時比較しない場合がある。
- Status: accepted

## Decision

- Experiment #2の現フェーズでは、open/local backendの追加を一旦freezeする。
- Benchmark Heavenなどのlandscapeはcandidate discovery / related-work indexとして利用し、掲載モデルを片端から実行しない。
- 新backendを追加するのは、既存armでは答えられない明示的なresearch questionまたは方法論的な穴を埋める場合に限る。
- 条件を追加・変更する場合は既存Evidenceを上書きせず、新しいIssueまたはexperiment versionとして扱う。
- 現在の優先順位は、dataset拡張、failure patternの分析、long-context handling、downstream task successの導入とする。
- 現在のbackend集合が一般的に十分、最良、または将来も固定であるとは主張しない。

## Delivery and validation

Issue #38でopen/local backend integrationを進め、Open Jev v0.2、Laya multilingual v0.1、Zefan Open-Jev 2B v0.1、typed-decision-bert / JevBERT P0.5 v0.1のvalid run Evidenceを固定した。

2026-09-22の棚卸しでbackend expansion freezeを明示し、Issue #38を完了として閉じた。その後、PR #64で3-case pilotを12 cases / 2 corpus snapshotsへ拡張し、研究作業がbackend追加からdataset depthへ移行した。

この方針がIssue状態と次の実験作業へ反映されたため、提供状態を`validated`とする。

## Consequences

- 新しいbackend発見は研究Inboxに残せるが、即時runの義務にはならない。
- 比較armの追加より、同じ評価面での失敗分析とdatasetの代表性を改善しやすくなる。
- 将来backendを再開するときは、「新しいから」ではなく、何のresearch gapを埋めるかを先に定義する必要がある。
- 外部benchmarkの順位や主張を、そのまま本repositoryのPDDR Context Selection品質へ転用しない。

## Revisit when

- 既存armでは評価できない新しいsemantic-decision primitiveまたはarchitectureが現れた場合。
- dataset拡張後のfailure analysisで、特定の方法論を追加比較する必要が生じた場合。
- provider-neutral contract自体が新しいbackend familyを表現できない場合。
- Experiment #2とは別のresearch questionでbackend diversityが主要変数になる場合。

## Evidence

- Maintainer approval during repository audit, 2026-09-22 (private).
- [Issue #38: Connect open typed-decision backends](https://github.com/serevy/semantic-decision-lab/issues/38)
- [Open Jev v0.2 Evidence PR #53](https://github.com/serevy/semantic-decision-lab/pull/53)
- [Laya multilingual Evidence PR #56](https://github.com/serevy/semantic-decision-lab/pull/56)
- [Zefan Open-Jev 2B Evidence PR #60](https://github.com/serevy/semantic-decision-lab/pull/60)
- [typed-decision-bert Evidence PR #63](https://github.com/serevy/semantic-decision-lab/pull/63)
- [Dataset v0.2 expansion PR #64](https://github.com/serevy/semantic-decision-lab/pull/64)

## Related records

- PDDR-0001: Separate experiments from durable decisions
- PDDR-0003: Keep semantic-provider evaluation behind one provider-neutral contract
- PDDR-0004: Evolve context-selection datasets by versioned pre-output freezes
