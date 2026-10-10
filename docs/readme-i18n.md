# README i18n

公開READMEの多言語化ワークフロー。

英語の `README.md` をcanonical sourceとする。READMEのpush/PRでは既存4言語とのMarkdown構造一致を**外部APIなし**で検査する。翻訳用Artifactを生成する処理は手動起動に限定し、自動commit・push・mergeは行わない。

## 対応言語

- `all` — 下記4言語を1回のrunで順番に処理
- `ja` — 日本語
- `zh-CN` — 简体中文
- `ko` — 한국어
- `fr` — Français

追加言語は、Glossary・品質確認・language switcherまで含めて段階的に追加する。

## 実行

通常のREADME/翻訳README変更では、push/PRの `verify-readme-structure` が4言語の構造・保護対象を検証する。ここではOpenAI APIを呼ばず、翻訳内容の意味的な等価性までは保証しない。公開済みの言語切替行だけは各言語の選択状態を検証したうえで、他のURLの厳密な比較から除外する。

翻訳生成を試す場合のみActionsの **README i18n** から **Run workflow** を開き、target languageを選択する。既定値は `all`。

通常の多言語更新では `all` を選ぶ。`all` は `ja / zh-CN / ko / fr` を同じjob内で**言語ごとのtranslatorプロセスとして直列実行**し、1回のrunで全4言語を生成する。各言語でrequest counterをリセットしつつ、8秒pacingとglobal concurrencyは維持する。

個別言語は翻訳品質の再検証や障害切り分け用に残す。

別々の手動run同士はOpenAI Projectの共有10 RPM枠を超えないよう同じconcurrency groupで直列化する。ただしGitHub Actionsのconcurrencyは実行中1件に加えてpending 1件のみ保持するため、複数の個別runを同時に大量投入せず、通常は `all` を使用する。

### 既知の翻訳制約（2026-10-09）

長くなったcanonical READMEに対し、`md-translator` は日本語翻訳だけでも100以上の翻訳単位を処理した。HTTP request cap 60に達して失敗し、他言語の生成には進めなかった。制限はAPIキーの欠落ではなく、このワークフロー内の費用・リクエスト保護上限によるもの。

このため、有料APIを消費する自動翻訳は停止し、push/PRには無課金の構造チェックだけを残す。翻訳生成のチャンク化とリクエスト数見積もりを改善するまでは、手動 `all` 実行も完走を保証しない。必要なREADME差分は既存の訳文を見ながら慎重に反映し、保護トークン・URL・主張の範囲を確認してPRにする。上限の安易な引き上げやリトライ連打は避ける。

## 翻訳構成

- Translator: `rockbenben/md-translator`
- Pinned commit: `25d07cebc70266ed06bcfb7e5e1ef97253c3e998`
- Provider: OpenAI Chat Completions
- Model: `gpt-5.6-luna`
- Relay: disabled
- Canonical source: `README.md`
- Output: Actions Artifact only

Markdown保護はupstreamのplaceholder機構を利用する。
LLM翻訳時のみPoCで検証したwhole-line patchを実行時に適用し、inline codeやlinkの前後を含む1行全体を翻訳単位にする。

whole-line patchでは保護tokenの欠落・改変・重複を禁止する一方、対象言語の自然な語順に必要なtokenの並べ替えは許可する。保護tokenの欠落・変形を検出した場合は、その行だけ1回再翻訳する。それでも一致しなければ失敗させる。並べ替えによってMarkdown構造が壊れた場合は、後段のcode/link/heading等の品質ゲートで失敗させる。

README翻訳では再翻訳が実APIへ届くようCLI cacheを無効にする。READMEは短く、run間でcacheを永続利用していないため、破損結果を再利用しないことを優先する。

## Glossary

以下は全対応言語で英語表記を維持する。

- `semantic-decision-lab`
- `PDDR`
- `PDDR Kit`
- `GitHub Issues`
- `GitHub Issue`
- `PDDR-0001`

言語ごとのGlossary entryは `.i18n/readme-translation-settings.json` に明示する。

## 品質ゲート

`.i18n/verify-readme-translation.py` で以下を確認する。

- protected termの出現回数
- fenced code block
- inline code
- Markdown link destination
- heading hierarchy
- internal placeholder漏洩
- source READMEに対象行が存在する場合のみ、既知のinline-code回帰ケース

自動検証は「自然な翻訳」を保証しない。公開前にArtifactを人間がレビューする。

## API・安全境界

- `OPENAI_API_KEY` はActions Repository Secretから実行時のみ取得
- API keyは0600の一時設定ファイルに書き込み、終了時削除
- CLI引数・git・Artifactには含めない
- GitHub workflow permissionは `contents: read`
- checkout credentialsはpersistしない
- dependency install scriptは `--ignore-scripts`
- OpenAI公式Chat Completions URLへのPOSTのみ許可
- redirectを拒否
- Standard service tierを強制
- 送信開始を最低8秒間隔
- 個別言語runは最大60 HTTP attempts
- `all` runも各言語を個別processで直列実行し、各言語最大60 HTTP attempts
- job timeout 45分

request guardは完全なsecurity sandboxではない。第三者translator codeがAPI keyと公開READMEを処理する信頼境界は残る。

## 公開フロー

1. `README.md` を更新し、翻訳READMEとの差分を確認
2. 既存訳文を参照し、4言語へ意味と主張の範囲を保って反映（有料の翻訳生成は既知の上限問題が解消してから）
3. PR上の `verify-readme-structure` を通し、翻訳の自然さと意味を人間が確認
4. レビュー後にmergeし、mainでも構造チェックを確認

翻訳生成を再開できた場合は、従来どおりArtifactを回収・レビューしてからPRにする。

初回PoCの経緯・実験結果は `docs/readme-i18n-poc.md` に残す。
