---
id: PDDR-0004
title: Evolve context-selection datasets by versioned pre-output freezes
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
  - "https://github.com/serevy/semantic-decision-lab/issues/13"
  - "https://github.com/serevy/semantic-decision-lab/pull/64"
  - "https://github.com/serevy/semantic-decision-lab/pull/65"
related:
  - PDDR-0001
  - PDDR-0002
  - PDDR-0003
supersedes: []
superseded_by: null
---

# PDDR-0004: Evolve context-selection datasets by versioned pre-output freezes

## Summary

PDDR Context Selectionのdatasetは、provider出力を見る前にgoldとcorpus snapshotをversioned freezeし、既存pilotを変更せず新しいdataset versionとして拡張する。v0.2では12 cases / 2 real PDDR corporaへ拡張し、各corpus内の全recordがrequiredとしてちょうど1回ずつ登場するbalanced designを採用する。

## Context and observations

- v0.1はPDDR Kitの7 recordsに対する3-case pilotで、easy / semantic / trapの初期failureを確認するには有用だったが、provider品質を一般化するには小さすぎる。
- 3 casesでは、特定recordがrequiredになる頻度やtask wordingが結果へ大きく影響し得る。
- provider outputを見た後にgoldやcase wordingを変更すると、比較面自体がprovider結果へ適応し、後続runとの解釈が崩れる。
- PDDR Kit以外の実decision recordsを含めることで、同じ語彙・構造だけに最適化されたdatasetになるリスクを下げられる。
- readme-i18n-kitにはpublication、Markdown repair、terminology、runtime security、caller responsibilityと異なるdecision domainがあり、二つ目の実corpusとして利用できた。
- 2026-09-22の棚卸しで、backend数を増やすよりdatasetの年輪を増やす方針が承認された。

## Options considered

### v0.1の3 casesを直接編集して難易度を上げる

- Benefits: ファイルとcase数を増やさずに改善できる。
- Costs / constraints: 既存Evidenceが参照したgoldとtaskが変わり、過去runの意味を壊す。
- Status: rejected

### provider出力を見ながら間違いやすいcaseへgoldを調整する

- Benefits: providerの挙動へ合わせて見かけ上の整合を取りやすい。
- Costs / constraints: evaluation leakageになり、独立した比較面を失う。
- Status: rejected

### 既存pilotを不変で残し、新versionとしてbalanced datasetを追加する

- Benefits: 過去Evidenceを保持しながらcase数とdomain diversityを増やせる。gold作成とprovider評価を時間的に分離できる。
- Costs / constraints: dataset version、corpus snapshot、manifest、validationの管理が必要になる。
- Status: accepted

## Decision

- datasetのgold、task、corpus snapshotは、そのversionのbaseline/provider outputを見る前にfreezeする。
- 既存datasetの意味を後から書き換えず、修正や拡張は新dataset versionで行う。
- source corpusはbounded snapshotとしてrepository/revision/manifestを記録し、caseが参照するrecord集合を明示する。
- v0.2ではctx-001〜003の`difficulty / task / corpus / gold`をv0.1から変更しない。
- v0.2はPDDR Kit 7 recordsとreadme-i18n-kit 5 recordsの二つの実corpus snapshot、合計12 casesを使用する。
- 各caseはrequired recordを1件持ち、各corpus内の全recordがrequiredとしてちょうど1回ずつ登場するようにして、required-label frequency priorを避ける。
- `required / useful / irrelevant`はcorpus全体をpartitionし、non-obviousなgoldにはnotesを残す。
- このbalanced designはPDDR利用全体の代表性を保証するものではなく、次のfailure analysisを改善するための実験条件である。
- long-context chunking、summary、hierarchical selectionなど入力変換を試す場合は、同じdataset versionのgoldを使っても別experiment conditionとして記録する。

## Delivery and validation

Issue #13で3-case pilotから10–20 casesへの拡張Acceptance Criteriaを管理した。

PR #64でv0.2を12 cases / 2 corpus snapshotsとしてfreezeし、validatorが次を確認するようにした。

- ctx-001〜003のpilot不変性
- corpus registry / manifest / file整合
- gold partitionの重複なし・全corpus coverage
- exactly one required per case
- each record required exactly once per corpus snapshot
- taskとrationale notesの存在

dataset v0.2 CIが成功し、PR #64がマージされた後にのみPR #65でbaseline replayを開始した。gold freezeとprovider/baseline observationの順序を実運用で分離できたため、提供状態を`validated`とする。

## Consequences

- 過去runのgoldとtaskを保持したままdatasetを成長させられる。
- dataset設計由来のfrequency biasを一つ減らせる。
- 新corpus追加時はsource revision、record identity、gold rationaleのレビューが必要になる。
- case wordingとPDDR本文のlexical overlapが強すぎる可能性など、別のdataset biasは引き続き監査対象になる。
- 12 casesでも統計的に十分または代表的とは主張せず、結果はこのbounded datasetへ限定して解釈する。

## Revisit when

- 12-case v0.2で特定difficultyまたはcorpusに偏ったfailureが見つかった場合。
- 複数required records、cross-corpus retrieval、superseded/rejected recordsを評価する必要が生じた場合。
- downstream task successをgold selection以外の主評価へ追加する場合。
- case wordingのlexical overlapや人手goldの一貫性が主要なbiasとして観測された場合。

## Evidence

- Maintainer approval during repository audit, 2026-09-22 (private).
- [Issue #13: Expand PDDR context-selection dataset](https://github.com/serevy/semantic-decision-lab/issues/13)
- [Dataset v0.2 freeze PR #64](https://github.com/serevy/semantic-decision-lab/pull/64)
- [Dataset v0.2 baseline replay PR #65](https://github.com/serevy/semantic-decision-lab/pull/65)

## Related records

- PDDR-0001: Separate experiments from durable decisions
- PDDR-0002: Freeze backend expansion after methodologically distinct coverage
- PDDR-0003: Keep semantic-provider evaluation behind one provider-neutral contract
