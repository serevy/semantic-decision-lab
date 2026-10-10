# semantic-decision-lab

[English](README.md) | **日本語** | [简体中文](README.zh-CN.md) | [한국어](README.ko.md) | [Français](README.fr.md)

[![PDDR validation](https://github.com/serevy/semantic-decision-lab/actions/workflows/pddr.yml/badge.svg?branch=main)](https://github.com/serevy/semantic-decision-lab/actions/workflows/pddr.yml)
[![README structure](https://github.com/serevy/semantic-decision-lab/actions/workflows/readme-i18n.yml/badge.svg?branch=main)](https://github.com/serevy/semantic-decision-lab/actions/workflows/readme-i18n.yml)
[![GitHub Pages](https://github.com/serevy/semantic-decision-lab/actions/workflows/pages.yml/badge.svg?branch=main)](https://github.com/serevy/semantic-decision-lab/actions/workflows/pages.yml)
[![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/serevy/semantic-decision-lab?utm_source=oss&utm_medium=github&utm_campaign=serevy%2Fsemantic-decision-lab&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)](https://coderabbit.ai)

> **意味決定層におけるプロバイダー中立の実験：**曖昧な状態を、決定論的システムが利用できる型付きの確率的な決定へと変換します。

核心となる問いは「LLMは何でもできるか」ではなく、次のとおりです。

> **意味的判断を、実行・ポリシー・安全性の制御を決定論的なコードが担い続ける中で、小さくテスト可能なソフトウェアプリミティブとして分離できるだろうか？**

このリポジトリでは、オーケストレーション、コンテキスト選択、型付きハンドオフ、状態の解釈、ドメインゲート、リアルタイムシステム、交換可能な意味決定プロバイダーの観点から、その問いを検討します。

## 核となる考え方

セマンティックレイヤーは、**現在の状態が何を意味するのか**を答えるべきです。決定論的システムは、**次に何が起こるのか**を引き続き担います。

![セマンティック意思決定コアアーキテクチャ](docs/assets/semantic-decision-core.svg)

この分離により、実行ロジックとは独立して意味的判断をテストできます。また、不確実性、棄権、エスカレーション、プロバイダーの置き換えを、一枚岩のエージェントの内部に隠すのではなく、明示的に扱えるようになります。

## 研究の境界

2026年の先行研究調査では、モデルルーティング／カスケード、コンテキストとプロンプトの圧縮、構造化されたエージェント間の引き継ぎ、対話／行動状態の追跡、語用論の評価、軌跡／プロセスの監督、高水準の身体化プランニング、中間表現などに、すでに多くの研究があることが分かりました。

そのため、このラボではこれらの手法を**構成要素や比較用のベースライン**として扱い、それ自体の新規性は主張しません。共通の研究課題は、より明確な範囲に絞ります。

> **曖昧な意味的判断を、不確実性を明示した型付きの状態と遷移として表現し、下流の振る舞いを保ちながら、実用的な範囲でプロバイダー間の移植性を確保し、決定論的な実行・認可・ポリシー・ハードセーフティに従属させられるか？**

実験では可能な限り既存手法を再利用し、独自の実装は意味的な忠実性、キャリブレーション、棄権、状態遷移、下流への影響、権限の境界に重点を置きます。

根拠と研究範囲の決定については、[PDDR-0007](docs/records/PDDR-0007-focus-typed-semantic-state.md) と [#70 外部リファレンスレーダー](https://github.com/serevy/semantic-decision-lab/issues/70)を参照してください。
## 研究マップ

| 領域 | 研究課題 | 主な論点 |
|---|---|---|
| オーケストレーション | セマンティックルーティングによって、タスク全体の成功率、コスト、レイテンシー、エスカレーションや再作業を合わせて改善できるか？ | [#1 AI Work Routing](https://github.com/serevy/semantic-decision-lab/issues/1) |
| コンテキストとメモリ | 意思決定履歴のコンテキストをどこまで削減しても、下流の意思決定における振る舞いを維持できるか？ | [#2 PDDR コンテキスト選択](https://github.com/serevy/semantic-decision-lab/issues/2)、[#74 下流タスク成功評価](https://github.com/serevy/semantic-decision-lab/issues/74) |
| 引き継ぎ | 制約、不確実性、根拠の出所、次に必要なアクションを保てる最小の型付き引き継ぎ情報は何か？ | [#3 型付き引き継ぎ](https://github.com/serevy/semantic-decision-lab/issues/3) |
| 状態の解釈 | 意思決定状態、語用論的状態、意味的遷移を、根拠のない確実性や権限を捏造せずに表現できるか？ | [#4](https://github.com/serevy/semantic-decision-lab/issues/4), [#5](https://github.com/serevy/semantic-decision-lab/issues/5), [#9](https://github.com/serevy/semantic-decision-lab/issues/9) |
| ドメインゲートと発見 | 範囲を限定したドメインのワークフローで、意味的分類、スコアリング、検索、ランキングはどこに役立つか？ | [#6 取引戦略ゲート](https://github.com/serevy/semantic-decision-lab/issues/6)、[#7 VTuber発見](https://github.com/serevy/semantic-decision-lab/issues/7)、[#8 好みの発見](https://github.com/serevy/semantic-decision-lab/issues/8) |
| リアルタイム／身体性 | 遅延、ドリフト、モデルのポリシー変更があっても、決定論的なハードセーフティを独立させたまま、低遅延の意味的状態によって対話を改善できるか？ | [#10 リアルタイム／身体性意思決定層](https://github.com/serevy/semantic-decision-lab/issues/10) |
| プロバイダーの可搬性 | 型付き意思決定の契約によって、API形式だけでなく、意味、キャリブレーション、観測可能な機能をホステッド／ローカルのプロバイダー間で維持できるか？ | [#81 System One provider portability](https://github.com/serevy/semantic-decision-lab/issues/81) |

このリポジトリでは、分類、スコアリング、ルーティング、検索、圧縮、構造化された引き継ぎ、検証、軌跡分析、型付きIRなどの既存手法を構成要素として扱います。研究の焦点は、それらを組み合わせたときに、型付きの意味的状態と遷移が下流の振る舞いをどこまで維持できるかです。

## プロバイダーに依存しない設計

Jevはこの作業における重要なプロバイダーであり、参照点ですが、**研究の定義ではありません**。実験では、実用上可能な限り、アプリケーションロジックを共通の型付き意思決定境界の背後に置くことを目指します。

![プロバイダーに依存しないセマンティック意思決定アーキテクチャ](docs/assets/provider-neutral-architecture.svg)

プロバイダーの比較では、個別の側面を分けて扱います。

- **契約互換性** — 同じリクエスト／レスポンス形式を使用できるか？
- **意味的品質** — タスクに対する判断は正しいか？
- **キャリブレーション** — 確率は、下流の自動化が想定している意味どおりのものになっているか？
- **堅牢性** — オプションの順序、コンテキスト長、パッキング、棄権、失敗時の動作
- **システムコスト** — レイテンシ、メモリ、ハードウェア、スループット、外部APIコスト

**API互換性は意味的同等性ではありません。** プロバイダーは簡単に置き換えられても、動作が十分に異なるため、異なるしきい値やデプロイメント上の制約が必要になる場合があります。

## 実験の仕組み

このラボでは証拠を最優先します。実験設計と生の証拠は、永続的なプロジェクト上の決定とは分けて扱います。

![実験のエビデンスとPDDRワークフロー](docs/assets/experiment-evidence-pddr.svg)

共通ルール：

- 採点対象のプロバイダー出力前に評価条件を凍結する。
- 初回実行時の証拠は、失敗が発見された後に書き換えるのではなく、そのまま保持する。
- バージョン、プロトコル、パッケージング、データセット、またはプロンプトの変更を明示的に記載する。
- 関連する場合は、決定論的および／または従来型のベースラインと比較する；
- プロバイダーが入力を拒否または切り捨てる場合は、網羅性と正確性を区別する。
- 上流ベンチマークの主張は、再現されるまでは関連研究の根拠として扱う。
- プロバイダー固有のベンチマーク結果を公開する前に、プロバイダーの利用規約を遵守してください。

## 結果と可視化

README は意図的に **ライブリーダーボードではありません**。

安定した凍結済みの結果は、後から小さなチャートや概要図としてここに掲載できる可能性があります。詳細な結果の内訳、出所情報、診断結果、インタラクティブなビューは、実験アーティファクト、`docs/`、または[GitHub Pages サイト](https://serevy.github.io/semantic-decision-lab/)に置くものとします。

これにより、実験バージョンが生成したチャートがそのバージョンよりも長く残ってしまうというよくある失敗を避けつつ、ランディングページの読みやすさを保てます。

## リポジトリのレイアウト

| パス | 目的 |
|---|---|
| `experiments/` | 再現可能な実験コード、データセット、評価器、およびエビデンス重視のアセット |
| `docs/records/` | 承認済みPDDR判定記録 |
| `.pddr/` | PDDR Kit のツール、スキーマ、検証、およびチェックポイントのサポート |
| `docs/` | ランディングページに含めない補足ドキュメントおよび調査メモ |
| GitHub Issues | 仮説、プロトコル、中間観察結果、生データ、失敗、およびフォローアップ |

将来の実験に影響を与える可能性のある外部の実装や論文については、[#70 外部リファレンスレーダー](https://github.com/serevy/semantic-decision-lab/issues/70)を参照してください。

## 研究記録

作業中の実験の詳細は GitHub Issues に残します。PDDR は、実験そのものを超えて保存する価値のある、永続的なプロジェクト、製品、またはプロセスに関する決定に証拠がつながった場合にのみ作成されます。

| 成果物 | 役割 |
|---|---|
| GitHub Issue | 仮説、プロトコル、観察結果、生の証拠、失敗、およびフォローアップ |
| PDDR | 根拠に裏付けられた採用、却下、延期、範囲、結果、および再検討条件 |

このリポジトリでは、[PDDR Kit](https://github.com/serevy/pddr-kit/releases/tag/v0.3.0) の管理対象コアに `v0.3.0` を使用しています（[PR #145](https://github.com/serevy/semantic-decision-lab/pull/145) で更新）。実験のEvidence、意思決定記録、任意のSkillsは今回のコア移行の対象外です。[`PDDR-0001`](docs/records/PDDR-0001-separate-experiments-from-decisions.md) は、実験作業と永続的な意思決定記録の境界を定義します。
