---
id: PDDR-0001
title: Why PDDR Kit exists
decision_date: 2026-09-16
recorded_date: 2026-09-17
decision_status: accepted
delivery_status: validated
scope:
  - project
  - product
  - process
owners:
  - serevy
evidence:
  - "Project planning conversation, 2026-09-16 to 2026-09-17 (private)"
  - "First adoption into a separate existing project, 2026-09-17 (private)"
related:
  - PDDR-0003
supersedes: []
superseded_by: null
---

# PDDR-0001: Why PDDR Kit exists

## Summary

プロジェクトごとに判断記録の方法を作り直す負担を減らし、人とAIが判断の背景から実装・検証までを引き継げる共通キットを、公開OSSとして作る。

## Context and observations

- コードや設計書だけでは、現在の形に至った理由が失われやすい。
- 実装担当には「何をするか」だけでなく「何のためか」も必要になる。
- 提案、採用、実装済み、検証済みが混同されると、AIを含む次の担当者が誤った前提で作業する。
- 各プロジェクトで同じ仕組みを一から設計するのは重複になる。
- ADR / DDRは重要な判断を残す成熟した方法だが、この取り組みでは判断前の観測と判断後の実装・検証までの接続を重視する。

## Options considered

### 各プロジェクトで個別運用する

- Benefits: そのプロジェクトだけに最適化しやすい。
- Costs / constraints: 再設計が必要で、形式や品質が揺れやすい。
- Status: rejected

### 共通キットとして切り出す

- Benefits: 新規・既存プロジェクトへ再利用でき、改善を共有できる。
- Costs / constraints: 共通仕様と固有の記録を分離し、過剰な汎用化を避ける必要がある。
- Status: accepted

## Decision

- 名称を**PDDR Kit**とする。
- PDDRの正式名称を**Project Design Decision Record**とし、Project / Product / Processに関する判断を対象に含める。
- リポジトリ`pddr-kit`をPublic、MIT Licenseで公開する。
- 共通リポジトリには仕様、テンプレート、Skill、検証方法を置き、各プロジェクト固有の記録は各プロジェクト側へ置く。
- ADR / DDRを置き換えず、経緯・実装・検証をつなぐレイヤーとして共存する。
- Jevなどの有償サービスは任意拡張とし、本体の必須依存にはしない。

## Delivery and validation

リポジトリ作成、MIT License、仕様、テンプレート、Skill、導入・検証CLI、CIを実装した。2026-09-17に、PDDR Kitとは別の既存プロジェクトへ共通仕様を変更せず導入し、導入先のPDDR検証CIと既存CIがともに成功した。これにより、PDDR-0001で定めた初期の再利用性検証条件を満たした。

新規プロジェクトを含む複数形態での検証は、引き続きRoadmapの対象とする。

## Consequences

- 利用者はMarkdownだけで開始できる。
- 特定のAIや外部サービスを必須にしない。
- 有償連携の有無にかかわらず、基本機能と記録の可搬性を保つ。
- 自動化を急ぐ前に、記録の意味と人間による確認方法を固める必要がある。
- 公開用記録には私的な会話全文や機密情報を含めない。

## Revisit when

- Project / Product / Processの範囲が広すぎて、一貫した運用ができない場合。
- 既存ADR / DDRとの重複が利用者を混乱させる場合。
- 二つ目のプロジェクトへの導入で、共通化できない前提が見つかった場合。

## Evidence

- 2026-09-16から2026-09-17に行った非公開の企画会話を、人間が確認した内容に基づき要約。
- READMEの「参考文献・謝辞」に着想元と関連資料を記載。
- 2026-09-17、別の既存プロジェクトへ非破壊で導入し、PDDR検証CIと導入先の既存CIが成功した。非公開プロジェクトのURLや内容は公開記録へ転記しない。

## Related records

- PDDR-0003: First external adoption findings
