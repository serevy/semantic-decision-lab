---
id: PDDR-0005
title: Evaluate context selection through frozen downstream decision behavior
decision_date: 2026-09-23
recorded_date: 2026-09-23
decision_status: proposed
delivery_status: not-started
scope:
  - product
  - process
owners:
  - serevy
evidence:
  - "https://github.com/serevy/semantic-decision-lab/issues/2"
  - "https://github.com/serevy/semantic-decision-lab/issues/74"
  - "https://github.com/serevy/semantic-decision-lab/pull/69"
  - "https://github.com/serevy/semantic-decision-lab/pull/72"
  - "https://github.com/serevy/semantic-decision-lab/pull/73"
related:
  - PDDR-0002
  - PDDR-0003
  - PDDR-0004
supersedes: []
superseded_by: null
---

# PDDR-0005: Evaluate context selection through frozen downstream decision behavior

## Summary

PDDR Context Selectionをretrieval goldだけで評価し続けず、凍結済みのcontext selectionが実際のproject decision behaviorを保つかを、provider-neutralなdownstream task contractで別レイヤーとして評価する。

## Context and observations

- v0.2のreduced-context Top-2ではkeyword 11/12、first-512 embedding 10/12、complete-record chunked + max 9/12とrequired-context recallが分かれた。
- input diagnosticsにより、original embedding armは全12 PDDR passageが512 tokensでtruncationしていた。
- complete-record chunkingはctx-002を救済した一方でctx-006 / ctx-007を新たにmissし、全文可視化だけではrequired recallが単調改善しなかった。
- 同じ12 retrieval labelsへchunk sizeやaggregationを追従させると、diagnostic datasetへの最適化とdownstream usefulnessを混同しやすい。
- Experiment #2の初期protocolはdownstream task successをprimary metricに含めている。
- PDDR-0004は、gold selection以外の主評価としてdownstream task successを追加する場合を明示的なRevisit条件としている。

## Options considered

### Retrieval goldだけを最適化し続ける

- Benefits: evaluatorが単純で、既存Evidenceとの比較が容易。
- Costs / constraints: record IDのhitが実task behaviorを保つか確認できず、同一12 labelsへの過適応を招きやすい。
- Status: rejected

### Free-form downstream taskを直ちにLLM judgeで採点する

- Benefits: 実利用に近い複雑なoutputを評価できる。
- Costs / constraints: generatorとjudgeの品質、rubric解釈、文体差が同時に混ざり、初回sliceとしてfailure原因を切り分けにくい。
- Status: rejected for the first downstream slice

### Bounded project-action tasksをpre-output freezeし、同一downstream modelでcontext armだけ変える

- Benefits: context selectionの差を保ったままproject-specific behaviorをexact scoringでき、ABSTAINとwrong actionも分離できる。
- Costs / constraints: open-ended engineering qualityを直接表すbenchmarkではなく、choice wording biasも残る。
- Status: proposed

## Proposed decision

Maintainer approval is required before this section becomes accepted.

- 12 downstream casesをctx-001〜012へ1:1で対応させ、scenario / A-D options / gold action / source decisionをdownstream model outputを見る前にfreezeする。
- model promptへgold choice、source PDDR ID、rationaleを渡さない。
- A-Dのgold labelは12 casesで均等にし、`ABSTAIN`を許可する。
- 初回sliceでは次の6 context armsを固定して比較する。
  - no-context negative control
  - required-only oracle/minimal-context control
  - full-context control
  - frozen keyword Top-2
  - frozen first-512 embedding Top-2
  - frozen complete-record chunked Top-2
- retrieval armは再実行・再最適化せず、既存Evidenceのselectionをそのままdownstream inputへ使う。
- 一つのrun内では同一downstream model / sampling configurationを全armsへ適用する。
- primary metricsはgold action accuracyとwrong-action rateとし、abstention、full-contextとのbehavior preservation、no-context正解率を補助診断として記録する。
- v0.1 outputを見た後のscenario / option / gold / prompt contract変更は同versionへ上書きせず、新しいversionとして扱う。
- このbounded taskの結果だけでproduction selectorやopen-ended task qualityを一般化しない。

## Delivery and validation

Proposed. Issue #74 and the associated freeze PR define the candidate dataset, arms, validator, and metric semantics. No downstream-model output has been observed yet.

## Consequences

- retrieval recallと実decision behaviorを別レイヤーで比較できる。
- no-context controlにより、task wordingだけで正解できるcaseをprompt leakage signalとして観測できる。
- required-only controlにより、最小の正解contextがdownstream modelへ十分かを診断できる。
- wrong actionとabstentionを分離でき、危険な誤判断と慎重な未回答を同一failureへ潰さない。
- 初回sliceはbounded choiceであり、free-form implementation qualityは後続課題として残る。

## Revisit when

- no-context正解率が高く、scenario / options自体が回答を強く示している場合。
- required-onlyでもdownstream behaviorが安定せず、taskまたはmodelが主要bottleneckになった場合。
- free-form output、複数正解、複数required recordsを評価する必要が生じた場合。
- downstream outputに合わせてselection policy自体を最適化する独立phaseへ進む場合。

## Evidence

- [Issue #2: PDDR Context Selection](https://github.com/serevy/semantic-decision-lab/issues/2)
- [Issue #74: downstream task-success v0.1 freeze](https://github.com/serevy/semantic-decision-lab/issues/74)
- [PR #69: embedding input-length diagnostics](https://github.com/serevy/semantic-decision-lab/pull/69)
- [PR #72: complete-record chunked embedding condition](https://github.com/serevy/semantic-decision-lab/pull/72)
- [PR #73: chunked embedding Evidence freeze](https://github.com/serevy/semantic-decision-lab/pull/73)

## Related records

- PDDR-0002: Freeze backend expansion after methodologically distinct coverage
- PDDR-0003: Keep semantic-provider evaluation behind one provider-neutral contract
- PDDR-0004: Evolve context-selection datasets by versioned pre-output freezes
