---
id: PDDR-0007
title: Safe upgrades for adopted projects
decision_date: 2026-09-18
recorded_date: 2026-09-18
decision_status: accepted
delivery_status: validated
scope:
  - product
  - process
owners:
  - serevy
evidence:
  - "scripts/pddr.py"
  - "tests/test_pddr_cli.py"
  - "python -m unittest discover -s tests -v"
  - "https://github.com/serevy/pddr-kit/pull/8"
  - "https://github.com/serevy/obs-audio-guardian/pull/23"
  - "https://github.com/serevy/obs-audio-guardian/commit/ccf676e9d668f656cd5a2550e9e752e8f94b91bb"
  - "https://github.com/serevy/obs-audio-guardian/actions/runs/35302756162"
  - "https://github.com/serevy/obs-audio-guardian/actions/runs/35302756200"
related:
  - PDDR-0002
  - PDDR-0003
  - PDDR-0006
supersedes: []
superseded_by: null
---

# PDDR-0007: Safe upgrades for adopted projects

## Summary

導入済みプロジェクトへPDDR Kitの更新を届けるため、Kit管理ファイルだけをハッシュで追跡し、利用側の変更を検知した場合は書き込み前に停止する`upgrade`を導入する。

## Context and observations

- 最初の外部導入先へConsumption Contractを反映する必要が生じたが、既存の`init`は非破壊性を優先し、内容が異なるファイルを更新しない。
- 手動コピーだけでは、どのファイルをKitが管理し、どのファイルを導入先が所有するかが曖昧になり、複数プロジェクトで更新漏れや上書き事故が起こり得る。
- PDDR記録、設定、CI、AI向け規則はプロジェクト固有であり、共通Kitが自動上書きすべきではない。
- 既存の導入先には、導入時ファイルのハッシュを記録したマニフェストがない。

## Options considered

### 更新のたびに手動コピーする

- Benefits: 実装が不要。
- Costs / constraints: 更新対象と利用側変更の判別を毎回人が行い、再利用可能な導入経路を検証できない。
- Status: rejected

### Kit管理ファイルを常に上書きする

- Benefits: 更新手順が単純になる。
- Costs / constraints: 利用側の変更を消失させる可能性があり、非破壊性を満たさない。
- Status: rejected

### マニフェストとハッシュで安全に更新する

- Benefits: Kit管理範囲を限定し、変更・欠落・追跡外ファイルを競合として検知できる。
- Costs / constraints: マニフェスト導入前のプロジェクトでは、人が現状を確認して初期基準を作る必要がある。
- Status: accepted

## Decision

- `init`は`.pddr/manifest.json`を作り、Kitの版と管理ファイルのSHA-256を記録する。
- 管理対象は`.pddr/pddr.py`、`.pddr/specification.md`、`.pddr/template.md`とする。
- `upgrade`は新しいPDDR Kit側から実行し、`--dry-run`で更新予定を表示する。
- 既存ファイルが記録済みハッシュと異なる場合は、どのファイルも変更せず停止する。
- `.pddr/config.json`、PDDR記録、導入先のドキュメント・規則・CIは自動更新しない。
- マニフェスト導入前の環境では、人による確認後に`--bootstrap-manifest`で現状のハッシュだけを登録し、同じ実行で更新しない。

PR #8のレビューとマージにより、この判断は承認された。

## Delivery and validation

`init`のマニフェスト作成と`upgrade`を実装した。正常更新、dry-run、利用側変更による全体停止、旧導入先のマニフェスト初期化をunit testで検証した。

既存導入先のOBS Audio Guardianでは、導入済み管理ファイルが初回導入時のKitと一致することを確認した後、`--bootstrap-manifest --dry-run`、マニフェスト作成、`upgrade --dry-run`、実更新を順に実行した。設定、既存PDDR、CI、製品コードを変更せず、最新版のCLI・仕様・テンプレートへ更新できた。

Audio GuardianのPR #23でPDDR検証とWindowsのconfigure、build、test、artifact uploadが成功し、mainへマージされたため、提供状態を`validated`とする。

## Consequences

- PDDR Kitの共通仕様・テンプレート・CLIを、利用側の記録や設定から分離して更新できる。
- 管理ファイルを直接編集した導入先では自動更新が停止し、手動統合が必要になる。
- マニフェストを持たない既存導入先の初回移行には、人の確認が残る。
- 新しい管理ファイルの追加時も、同名ファイルが存在すれば競合として停止する。

## Revisit when

- 複数バージョンを跨ぐ移行処理や仕様変換が必要になった場合。
- 管理ファイルへの利用側カスタマイズを三方マージする要望が生じた場合。
- パッケージマネージャーや署名付き配布物を提供する場合。

## Evidence

- `scripts/pddr.py`
- `tests/test_pddr_cli.py`
- `python -m unittest discover -s tests -v`
- [PDDR Kit PR #8](https://github.com/serevy/pddr-kit/pull/8)
- [Audio Guardian PR #23](https://github.com/serevy/obs-audio-guardian/pull/23)
- [Audio Guardian merge commit](https://github.com/serevy/obs-audio-guardian/commit/ccf676e9d668f656cd5a2550e9e752e8f94b91bb)
- [Audio Guardian PDDR validation](https://github.com/serevy/obs-audio-guardian/actions/runs/35302756162)
- [Audio Guardian Windows CI](https://github.com/serevy/obs-audio-guardian/actions/runs/35302756200)

## Related records

- PDDR-0002: Portable initialization and validation
- PDDR-0003: First external adoption findings
- PDDR-0006: Safe context consumption and policy separation
