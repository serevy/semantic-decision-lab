# semantic-decision-lab

[English](README.md) | **日本語**

AIオーケストレーション、コンテキスト選択、ルーティング、ハンドオフ、リアルタイムシステムにおけるセマンティック意思決定レイヤーの実験。

## 運用モデル

このリポジトリでは、実験作業と、長期的に残すべきプロジェクト上の意思決定を分離します。

| 成果物 | 目的 | 主な内容 |
|---|---|---|
| GitHub Issue | 実験バックログと作業スレッド | 仮説、セットアップ、タスク、途中経過の観察、未加工の結果、フォローアップ |
| PDDR | 重要な意思決定を長期保存する記録 | 根拠に基づく採用、却下、保留、スコープ、影響、再検討条件 |

実験を実行または完了しただけでは、PDDR は自動的には作成しません。実験の根拠から、その理由を Issue のライフサイクルを越えて残すべき重要な Project、Product、または Process の意思決定に至った場合にのみ、PDDR を作成または更新します。

意思決定を行った場合は Issue と PDDR を相互にリンクし、実験の未加工データや詳細は Issue に残します。

## PDDR

このリポジトリでは、[PDDR Kit](https://github.com/serevy/pddr-kit) `v0.1.0-rc.1` を使用します。

`.pddr/template.md` をもとに記録を作成し、`docs/records/` 配下に保存して、レビュー前に検証します。

```bash
cp .pddr/template.md docs/records/PDDR-0002-short-title.md
python .pddr/pddr.py validate
```

最初の記録である [`PDDR-0001`](docs/records/PDDR-0001-separate-experiments-from-decisions.md) は、Issue と意思決定記録の境界を定義します。
