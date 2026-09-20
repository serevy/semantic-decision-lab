---
id: PDDR-0002
title: Portable initialization and validation
decision_date: 2026-09-17
recorded_date: 2026-09-17
decision_status: accepted
delivery_status: validated
scope:
  - product
  - process
owners:
  - serevy
evidence:
  - "python -m unittest discover -s tests -v"
  - "python scripts/pddr.py validate"
related:
  - PDDR-0001
supersedes: []
superseded_by: null
---

# PDDR-0002: Portable initialization and validation

## Summary

PDDR Kitの初期導入と最小検証を、Python標準ライブラリだけで動く単一CLIとGitHub Actionsで提供する。

## Context and observations

- 手作業でテンプレートをコピーするだけでは、導入先ごとに配置や検証方法が揺れやすい。
- 既存プロジェクトへ導入する際は、既存ファイルを壊さないことが重要である。
- ローカルとCIで別の検証ロジックを持つと、判定が一致しない可能性がある。
- PDDR本文の意味やEvidenceの十分性は機械的に保証できず、人のレビューが必要である。

## Options considered

### Shell scriptで初期化し、CIに個別の検査を書く

- Benefits: 短い実装で開始できる。
- Costs / constraints: OS差異が生じやすく、ローカルとCIの検査が重複する。
- Status: rejected

### 外部YAMLライブラリを使うCLIを提供する

- Benefits: YAMLの広い構文を扱える。
- Costs / constraints: 初期導入にパッケージインストールが必要になる。
- Status: rejected for v0.1

### Python標準ライブラリだけの単一CLIを提供する

- Benefits: Windows・macOS・Linuxで同じ入口を使え、追加パッケージなしで導入と検証ができる。
- Costs / constraints: v0.1のfront matterはトップレベルのscalarとlistに制限される。
- Status: accepted

## Decision

- `scripts/pddr.py`に`init`と`validate`を実装する。
- `init`は導入先へ設定、CLI、仕様、テンプレート、記録ディレクトリの案内を配置する。
- 既存ファイルと内容が異なる場合は、何も書き込まず停止する。
- `validate`は形式・状態・必須項目・ID・参照の最小整合性を検査する。
- GitHub Actionsも同じCLIを使い、CLI自身のunit testとPDDR Kit内の記録検証を行う。
- 意味の妥当性とEvidenceの十分性は、人によるレビューの責務として残す。

## Delivery and validation

CLI、unit test、GitHub Actions、導入ドキュメントを実装した。初回導入、同一内容での再実行、競合時に一切書き込まないこと、正常・異常レコードの判定をunit testで確認した。PDDR Kit自身の記録も同じCLIで検証した。

## Consequences

- 導入先はPython 3.10以降だけで基本運用を開始できる。
- ローカルとGitHub Actionsで同じ判定を利用できる。
- YAML全仕様には対応せず、v0.1で必要な単純なmetadata形式に限定する。
- 導入済みファイルの自動更新はまだ行わず、更新時は差分確認が必要になる。

## Revisit when

- Python 3.10が導入障壁になる利用環境が確認された場合。
- metadataへネスト構造が必要になった場合。
- 複数プロジェクトへの導入で、安全な更新・移行機能が必要になった場合。
- 検証ルールの誤検知または見逃しが継続的に発生した場合。

## Evidence

- `python -m unittest discover -s tests -v`
- `python scripts/pddr.py validate`
- `.github/workflows/validate.yml`

## Related records

- PDDR-0001: Why PDDR Kit exists
