---
id: PDDR-0006
title: Safe context consumption and policy separation
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
  - "docs/specification.md#consumption-contract"
  - "evals/pddr-recorder/consumption-cases.json"
  - "python scripts/validate_skill_evals.py evals/pddr-recorder/consumption-cases.json"
  - "python -m unittest discover -s tests -v"
  - "https://github.com/serevy/pddr-kit/pull/7"
  - "evals/pddr-recorder/results/2026-09-18-consumption-gpt-5.6-sol.json"
  - "evals/pddr-recorder/results/2026-09-18-consumption-gpt-5.6-luna.json"
  - "evals/pddr-recorder/results/2026-09-18-consumption-adjudication.json"
  - "python scripts/validate_skill_eval_results.py"
  - "https://github.com/serevy/pddr-kit/pull/10"
  - "https://github.com/serevy/pddr-kit/commit/2608035f2a364aa713eac9b80fbefc11ec2679bb"
  - "https://github.com/serevy/pddr-kit/actions/runs/35331363019"
related:
  - PDDR-0004
  - PDDR-0005
supersedes: []
superseded_by: null
---

# PDDR-0006: Safe context consumption and policy separation

## Summary

PDDRを無条件の命令やPolicyとして適用せず、現在のタスクに必要な記録だけを、状態・範囲・根拠に基づいて安全に解釈するConsumption Contractを導入する。

## Context and observations

- PDDRは判断を正確に保存できても、受け取り手が文章の強さ、時系列、反復回数を権限と誤認すると行動が歪む。
- 個別の失敗から作られた強い教訓を、適用条件なしに一般化すると過剰補正が起こり得る。
- すべてのPDDRを既定でAI contextへ投入すると、無関係・失効済みの判断が現在の作業へ影響し、記録量自体も負債になる。
- `accepted`は判断の採用状態を示すが、全状況へ適用されるPolicyであることを意味しない。
- 既存の評価証跡を現在版と混同しないため、評価時点のSkill、仕様、テンプレートも固定して参照する必要がある。

## Options considered

### 全PDDRを常に読み込む

- Benefits: 関連情報を取りこぼしにくい。
- Costs / constraints: context肥大化、無関係な判断の混入、古い判断による過剰補正が起こる。
- Status: rejected

### `accepted`なPDDRをPolicyとして扱う

- Benefits: 解釈規則が単純になる。
- Costs / constraints: 局所判断の一般化、現在の明示的Policyとの競合、適用範囲の消失につながる。
- Status: rejected

### 記録と適用を分離するConsumption Contractを持つ

- Benefits: 履歴を保存したまま、現在のタスクへ必要な範囲だけ安全に利用できる。
- Costs / constraints: context selectionと意味解釈の評価が別途必要になる。
- Status: accepted

## Decision

- PDDRはDecision ContextとEvidenceであり、それ自体を実行可能なPolicyとして扱わない。
- 現在のユーザー指示と承認済みProject / Organization Policyを優先する。
- status、scope、前提、例外、Evidenceを使って適用可能性を判断する。
- `proposed`と`needs-confirmation`は非拘束、`rejected`と`superseded`は履歴として扱う。
- 現在のタスクに必要な最小限の関連記録だけを選ぶ。
- 個別の事故を恒常的なPolicyへ昇格する場合は、別の明示的な承認を必要とする。

PR #7のレビューとマージにより、この判断は承認された。

## Delivery and validation

仕様、Skill、テンプレート、READMEへConsumption Contractを反映し、4件の評価ケースとCIによる構造検証を追加した。既存のモデル評価は参照資料スナップショットへ固定した。

更新後のSkill・仕様・テンプレートを使い、期待値と他モデルの出力を伏せてSol / mediumとLuna / mediumを独立実行した。両モデルとも4件すべてに合格し、禁止行動は観測されなかった。生出力、参照資料のハッシュ、調整役による意味判定、集計の整合性は記録済みである。

PR #10で評価証跡がレビューされ、CI成功後にmainへマージされた。これを独立した人による意味確認の証拠とし、提供状態を`validated`とする。

## Consequences

- PDDRを多く保存しても、すべてを毎回AIへ投入する必要はない。
- 文章の強さや新しさより、明示された権限、状態、適用範囲を優先できる。
- 古い判断は削除せず歴史として残しながら、現在の動作への影響を制限できる。
- context selectionの品質が新たな検証対象になる。
- PDDRをPolicyへ昇格するワークフローは本記録の対象外であり、必要になった時点で別途設計する。

## Revisit when

- PDDRの件数増加により、手動の関連記録選択が実用的でなくなった場合。
- 異なるAIが同じ記録群から一貫した適用判断をできない場合。
- Project / Organization Policyの機械可読な表現を導入する場合。
- Jevなど任意アダプターによるcontext selectionを本体へ接続する場合。

## Evidence

- `docs/specification.md#consumption-contract`
- `evals/pddr-recorder/consumption-cases.json`
- `python scripts/validate_skill_evals.py evals/pddr-recorder/consumption-cases.json`
- `python -m unittest discover -s tests -v`
- [PR #7](https://github.com/serevy/pddr-kit/pull/7)
- `evals/pddr-recorder/results/2026-09-18-consumption-gpt-5.6-sol.json`
- `evals/pddr-recorder/results/2026-09-18-consumption-gpt-5.6-luna.json`
- `evals/pddr-recorder/results/2026-09-18-consumption-adjudication.json`
- `python scripts/validate_skill_eval_results.py`
- [PR #10](https://github.com/serevy/pddr-kit/pull/10)
- [Merge commit 2608035](https://github.com/serevy/pddr-kit/commit/2608035f2a364aa713eac9b80fbefc11ec2679bb)
- [Validation run 35331363019](https://github.com/serevy/pddr-kit/actions/runs/35331363019)

## Related records

- PDDR-0004: Skill evaluation contract
- PDDR-0005: Unknown delivery state
