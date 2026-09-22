---
id: PDDR-0003
title: Keep semantic-provider evaluation behind one provider-neutral contract
decision_date: 2026-09-22
recorded_date: 2026-09-22
decision_status: accepted
delivery_status: validated
scope:
  - product
  - process
owners:
  - serevy
evidence:
  - "Maintainer approval during repository audit, 2026-09-22 (private)"
  - "https://github.com/serevy/semantic-decision-lab/pull/37"
  - "https://github.com/serevy/semantic-decision-lab/pull/53"
  - "https://github.com/serevy/semantic-decision-lab/pull/56"
  - "https://github.com/serevy/semantic-decision-lab/pull/60"
  - "https://github.com/serevy/semantic-decision-lab/pull/63"
related:
  - PDDR-0001
  - PDDR-0002
  - PDDR-0004
supersedes: []
superseded_by: null
---

# PDDR-0003: Keep semantic-provider evaluation behind one provider-neutral contract

## Summary

Semantic Decision LabではJevや特定open backendを研究primitiveとして固定せず、provider固有のresponseを共通のtyped decision contractへ正規化し、ranking、Top-k、評価指標をproviderから分離する。

## Context and observations

- PDDR Context Selectionでは、backendごとにHTTP shape、batching、packing、calibration、model identity、context lengthが異なる。
- backendごとに独自thresholdやselectorを許すと、provider品質とdownstream selection policyの差を分離できない。
- v0.1では各PDDR候補を`required / useful / irrelevant`の確率分布へ正規化し、共通selectorでTop-2を選ぶcontractを実装した。
- Open Jev、Laya、Zefan Open-Jev、typed-decision-bertで同じevaluatorとselection policyを維持でき、provider-specific failureをadapter/input/runtime側へ切り分けられた。
- Open Jev v0.1では同一input化を検出し、v0.2でpackingをversioned変更した。これはprovider-neutral evaluatorを変更せずにadapter failureを診断できることを示した。
- 2026-09-22の棚卸しで、この分離を一時的な実装ではなくrepositoryの継続的な研究方法として維持する判断が承認された。

## Options considered

### backendごとに最適なselectorとthresholdを持つ

- Benefits: 各backendの出力特性へ個別最適化しやすい。
- Costs / constraints: provider比較とselection policy比較が混ざり、結果を同じ実験として解釈しにくい。
- Status: rejected for shared comparisons

### Jev固有のresponse contractをrepository全体の中心にする

- Benefits: 一つのproviderへ実装を最適化できる。
- Costs / constraints: open/local backendや将来の実装を比較しにくく、provider変更がdownstream evaluatorへ波及する。
- Status: rejected

### provider固有adapterの後ろに共通typed decision contractを置く

- Benefits: evaluatorとselection policyを固定したまま、異なるbackendのpacking、transport、inference方式を比較できる。
- Costs / constraints: adapterで確率意味、abstention、identity、calibration provenanceを正確に扱う必要がある。
- Status: accepted

## Decision

- semantic backendは共通`SemanticDecisionProvider`境界の後ろへ置く。
- PDDR Context Selectionでは、各候補を`required / useful / irrelevant`の確率分布として`CandidateDecision`へ正規化する。
- 共通selection policyは、`required_probability`降順、`useful_probability`降順、PDDR ID tie-breakの順でrankingし、凍結されたTop-kを適用する。
- providerが明示的にabstainした場合の扱いも共通contract側で定義する。
- batching、HTTP/local execution、model-specific packing、tokenizationなどはadapter責務とし、evaluator意味論へ持ち込まない。
- provider-specific thresholdやtask wordingをprovider output確認後に変更して共有比較へ混ぜない。必要なら新しいexperiment versionとする。
- exact input preflight、runtime/model identity、revision、calibration、raw result provenanceをEvidenceとして保存する。
- 共通contractを使うことは、異なるproviderの確率が同じcalibration品質または意味精度を持つことを意味しない。

## Delivery and validation

PR #37で`SemanticDecisionProvider`、`CandidateDecision`、共通validationとTop-2 selectorを導入した。

その後、Open Jev v0.2、Laya multilingual v0.1、Zefan Open-Jev 2B v0.1、typed-decision-bert / JevBERT P0.5 v0.1を同じdownstream evaluatorへ接続し、provider固有条件をEvidenceとして分離した。各runでadapter mappingとinput/runtime provenanceを確認できた。

複数の異なるbackend familyで同じcontractを継続利用できたため、提供状態を`validated`とする。

## Consequences

- backend比較で、provider出力とselection policyの責務を分けられる。
- adapter bugやpacking failureをevaluatorの失敗と混同しにくい。
- 新backendは共通contractへmapできるかを先に検証する必要がある。
- calibrationやconfidenceの意味が異なるprovider間で、数値を無条件に同等扱いしない。
- 将来Top-kやranking policyを変える場合、それ自体を別の実験変数としてversion管理する必要がある。

## Revisit when

- 新しいbackendが`required / useful / irrelevant`分布へ無理なくmapできない場合。
- abstention、multi-label、hierarchical selectionなど新しいdecision primitiveが必要になった場合。
- provider間calibrationを直接比較する独立実験を設計する場合。
- downstream task successに合わせてselection policy自体を最適化する別フェーズへ進む場合。

## Evidence

- Maintainer approval during repository audit, 2026-09-22 (private).
- [SemanticDecisionProvider contract PR #37](https://github.com/serevy/semantic-decision-lab/pull/37)
- [Open Jev v0.2 Evidence PR #53](https://github.com/serevy/semantic-decision-lab/pull/53)
- [Laya multilingual Evidence PR #56](https://github.com/serevy/semantic-decision-lab/pull/56)
- [Zefan Open-Jev 2B Evidence PR #60](https://github.com/serevy/semantic-decision-lab/pull/60)
- [typed-decision-bert Evidence PR #63](https://github.com/serevy/semantic-decision-lab/pull/63)

## Related records

- PDDR-0001: Separate experiments from durable decisions
- PDDR-0002: Freeze backend expansion after methodologically distinct coverage
- PDDR-0004: Evolve context-selection datasets by versioned pre-output freezes
