---
id: PDDR-0005
title: Unknown delivery state
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
  - "evals/pddr-recorder/results/2026-09-18-gpt-5.6-sol.json"
  - "evals/pddr-recorder/results/2026-09-18-gpt-5.6-luna.json"
  - "evals/pddr-recorder/results/2026-09-18-adjudication.json"
  - "python scripts/validate_skill_eval_results.py"
  - "python -m unittest discover -s tests -v"
  - "https://github.com/serevy/pddr-kit/pull/5"
related:
  - PDDR-0002
  - PDDR-0004
supersedes: []
superseded_by: null
---

# PDDR-0005: Unknown delivery state

## Summary

実装・反映状況を確認できない判断を、未着手と推測せず記録するため、`delivery_status: unknown`を追加する。

## Context and observations

- 承認済みのベンダー判断を扱うSkill評価で、実装状況を示す証拠は与えられていなかった。
- SolとLunaはいずれも、実装証拠がないことを未着手の証拠とは扱わず、`unknown`を選んだ。
- 現行仕様には`unknown`がなく、`not-started`を選ぶと未着手という事実を補完してしまう。
- PDDRは判断状態と提供状態を独立して扱い、根拠のない状態を発明しないことを原則としている。

## Options considered

### 証拠がなければ`not-started`とする

- Benefits: 状態値を増やさずに済む。
- Costs / constraints: 未着手を確認していない場合にも事実として記録してしまう。
- Status: rejected

### `not-applicable`を使用する

- Benefits: 既存の状態値だけで表現できる。
- Costs / constraints: 実装対象ではない判断と、実装状況が不明な判断を区別できない。
- Status: rejected

### `unknown`を追加する

- Benefits: 不明な提供状態を推測せず表現できる。
- Costs / constraints: 仕様、CLI、Skill、評価契約の更新が必要になる。
- Status: accepted

## Decision

`delivery_status`へ`unknown`を追加する。実装証拠がないだけでは`not-started`とせず、提供状態を確認できない場合に`unknown`を使う。

PR #5のレビューとマージにより、この判断は承認された。

## Delivery and validation

仕様、CLI、Skill、評価ケースへ`unknown`を追加し、CLIが状態を受理するunit testを追加した。更新後のSkill、仕様、テンプレートを使ってモデル評価を再実行し、SolとLunaが対象ケースで`unknown`を選ぶことを確認した。

## Consequences

- 過去の判断を再構成するとき、判断状態だけでなく提供状態の不明も正直に表現できる。
- `not-started`は未着手を裏付ける情報がある場合に限定される。
- 既存のPDDRは変更不要であり、新しい状態値を必要な記録だけが使用する。

## Revisit when

- `unknown`が長期間放置され、確認タスクとの区別が必要になった場合。
- 提供状態に別の不確実性表現が必要になった場合。

## Evidence

- Sol / Lunaの独立forward-test
- `python scripts/validate_skill_eval_results.py`
- `python -m unittest discover -s tests -v`
- [PR #5](https://github.com/serevy/pddr-kit/pull/5)

## Related records

- PDDR-0002: Portable initialization and validation
- PDDR-0004: Skill evaluation contract
