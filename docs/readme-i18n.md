# README i18n

公開READMEの多言語化ワークフロー。

英語の `README.md` をcanonical sourceとして、GitHub Actionsから対象言語を1つ選び、レビュー用Artifactを生成する。生成物は自動commit・push・mergeしない。

## 対応言語

- `all` — 下記4言語を1回のrunで順番に処理
- `ja` — 日本語
- `zh-CN` — 简体中文
- `ko` — 한국어
- `fr` — Français

追加言語は、Glossary・品質確認・language switcherまで含めて段階的に追加する。

## 実行

Actionsの **README i18n** から **Run workflow** を開き、target languageを選択する。

通常の多言語更新では `all` を選ぶ。`all` は `ja / zh-CN / ko / fr` を同じtranslatorプロセスへ複数の `-t` 引数として渡し、1回のrunで全4言語を生成する。これにより実行し忘れを防ぎ、request guardの8秒pacingとrequest countも言語をまたいで共有する。

個別言語は翻訳品質の再検証や障害切り分け用に残す。

別々の手動run同士はOpenAI Projectの共有10 RPM枠を超えないよう同じconcurrency groupで直列化する。ただしGitHub Actionsのconcurrencyは実行中1件に加えてpending 1件のみ保持するため、複数の個別runを同時に大量投入せず、通常は `all` を使用する。

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

whole-line patchでは保護tokenの欠落・改変・重複を禁止する一方、対象言語の自然な語順に必要なtokenの並べ替えは許可する。並べ替えによってMarkdown構造が壊れた場合は、後段のcode/link/heading等の品質ゲートで失敗させる。

## Glossary

以下は全対応言語で英語表記を維持する。

- `semantic-decision-lab`
- `PDDR`
- `PDDR Kit`
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
- 既知のinline-code回帰ケース

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
- 1 run最大60 HTTP attempts
- job timeout 20分

request guardは完全なsecurity sandboxではない。第三者translator codeがAPI keyと公開READMEを処理する信頼境界は残る。

## 公開フロー

1. `README.md` を更新
2. README i18nを `all` で実行
3. 4言語を含む `readme-all` Artifactを回収
4. 自動品質ゲートと人間レビュー
5. 必要な表現を修正
6. 翻訳READMEとlanguage switcherをPR
7. レビュー後にmerge

初回PoCの経緯・実験結果は `docs/readme-i18n-poc.md` に残す。
