---
id: PDDR-0005
title: Evaluate context selection through frozen downstream decision behavior
decision_date: 2026-09-23
recorded_date: 2026-09-23
decision_status: accepted
delivery_status: validated
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
  - "Maintainer approval to merge PR #75, 2026-09-23 (private)"
  - "https://github.com/serevy/semantic-decision-lab/actions/runs/35940937705"
  - "https://github.com/serevy/semantic-decision-lab/issues/97"
  - "https://github.com/serevy/semantic-decision-lab/actions/runs/36035143735"
  - "https://github.com/serevy/semantic-decision-lab/issues/102"
  - "https://github.com/serevy/semantic-decision-lab/actions/runs/36099039635"
  - "https://github.com/serevy/semantic-decision-lab/issues/106"
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

## Decision

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
- downstream accuracyをretrieval behavior preservationのEvidenceとして扱うには、no-context negative controlがscenario / optionsだけではgold actionを十分に決められないことを示す必要がある。
- no-contextがsaturateした場合、そのrunはbenchmark-design diagnosticとしてfreezeし、同versionのcase/optionsをprovider outputへ合わせて修正しない。context dependenceをhardeningした新versionへ進む。
- wording difficultyだけを上げてもno-context推論が残る場合は、matched counterfactual pairなどcontext dependenceを構造的に保証できる評価へ移行する。pair内のprompt-visible taskを同一にし、Decision Contextだけでaccepted actionが変わる設計を優先する。
- 後続versionではlive output前にcaseごとのcontext-dependence auditと、no-context対context-bearing controlの意味ある分離を要求するnumeric diagnostic gateをfreezeする。
- matched-counterfactual evaluationでdownstream context fidelityが確認できた後にretrievalを再接続し、selectorのrequired-context hit/missとdownstream action / abstention / wrong actionを同じEvidenceで対応づける。
- retrieval-coupled evaluationでは、selectorのquery、candidate passage、Top-k、model/revision、ranking policyをdownstream output前にfreezeし、downstream labelへ合わせて同version内で調整しない。

## Delivery and validation

Maintainer approval to merge PR #75 was given on 2026-09-23. The downstream v0.1 dataset, frozen arm replay, evaluator contract, validator, and metric-semantics smoke are implemented in that PR.

The first live run completed on 2026-09-24 with OpenAI `gpt-5.6-luna`: 72/72 valid responses, 0 API/transport errors, and 0 exact-choice parse errors. All six arms scored 12/12, including the no-context negative control. This validates the execution/evaluation envelope and simultaneously triggers this record's benchmark-design revisit condition. Issue #97 owns the versioned context-dependence hardening; v0.1 remains frozen as diagnostic Evidence.

The first v0.2 live run completed with the same downstream model and 72/72 valid responses. No-context improved to 10/12 with 2 ABSTAIN, while required-only/full-context and all three replayed retrieval arms still scored 12/12. The pre-output gate failed because no-context remained above the frozen 8/12 maximum. The retrieval arms also remained 12/12 despite required-record coverage of 11/12, 10/12, and 9/12 respectively. This shows that harder wording alone did not make downstream success sufficiently dependent on retrieved project context. Issue #102 owns the matched-counterfactual v0.3 follow-up.

The first v0.3 live run completed with 48/48 valid responses and passed the full frozen context-fidelity gate. No-context produced 12/12 ABSTAIN, correct-context produced 12/12 project-gold actions, all 6 matched pairs flipped correctly when the accepted Decision Context changed, and both-contexts produced 12/12 ABSTAIN. The wrong-context arm followed the supplied sibling decision in 12/12 cases. This establishes, for the bounded matched-counterfactual slice, that Decision Context materially controls downstream behavior and that incorrectly retrieved accepted context can redirect the action. Issue #106 therefore recouples retrieval as the next experiment variable.

## Consequences

- retrieval recallと実decision behaviorを別レイヤーで比較できる。
- no-context controlにより、task wordingだけで正解できるcaseをprompt leakage signalとして観測できる。v0.1では1.0、v0.2では0.8333となり改善したが、retrieval差をmaskするには依然高すぎることを検出した。
- required-only controlにより、最小の正解contextがdownstream modelへ十分かを診断できる。
- wrong actionとabstentionを分離でき、危険な誤判断と慎重な未回答を同一failureへ潰さない。
- v0.3ではwrong-context 12/12 followが観測され、Decision Contextが正しければ強い一方、selectorが誤ったaccepted contextを供給するとdownstream actionも誤方向へ動くことが明確になった。
- 初回sliceはbounded choiceであり、free-form implementation qualityは後続課題として残る。

## Revisit when

- no-context正解率が高く、scenario / options自体が回答を強く示している場合。**2026-09-24にtriggered**: v0.1は12/12 → Issue #97。**v0.2でも再triggered**: 10/12、frozen gate fail → Issue #102。
- required-onlyでもdownstream behaviorが安定せず、taskまたはmodelが主要bottleneckになった場合。
- free-form output、複数正解、複数required recordsを評価する必要が生じた場合。
- downstream outputに合わせてselection policy自体を最適化する独立phaseへ進む場合。

## Evidence

- [Issue #2: PDDR Context Selection](https://github.com/serevy/semantic-decision-lab/issues/2)
- [Issue #74: downstream task-success v0.1 freeze](https://github.com/serevy/semantic-decision-lab/issues/74)
- [PR #69: embedding input-length diagnostics](https://github.com/serevy/semantic-decision-lab/pull/69)
- [PR #72: complete-record chunked embedding condition](https://github.com/serevy/semantic-decision-lab/pull/72)
- [PR #73: chunked embedding Evidence freeze](https://github.com/serevy/semantic-decision-lab/pull/73)
- Maintainer approval to merge PR #75, 2026-09-23 (private).
- [Workflow run 35940937705: GPT-5.6 Luna downstream v0.1](https://github.com/serevy/semantic-decision-lab/actions/runs/35940937705)
- [Issue #97: downstream v0.2 context-dependent benchmark hardening](https://github.com/serevy/semantic-decision-lab/issues/97)
- [Workflow run 36035143735: GPT-5.6 Luna downstream v0.2](https://github.com/serevy/semantic-decision-lab/actions/runs/36035143735)
- [Issue #102: downstream v0.3 matched counterfactual stress](https://github.com/serevy/semantic-decision-lab/issues/102)
- [Workflow run 36099039635: GPT-5.6 Luna downstream v0.3](https://github.com/serevy/semantic-decision-lab/actions/runs/36099039635)
- [Issue #106: downstream v0.4 retrieval-coupled matched-snapshot evaluation](https://github.com/serevy/semantic-decision-lab/issues/106)

## Related records

- PDDR-0002: Freeze backend expansion after methodologically distinct coverage
- PDDR-0003: Keep semantic-provider evaluation behind one provider-neutral contract
- PDDR-0004: Evolve context-selection datasets by versioned pre-output freezes
