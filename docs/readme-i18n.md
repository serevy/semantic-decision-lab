# README i18n

公開READMEの多言語化ワークフロー。

英語の `README.md` をcanonical sourceとして、GitHub Actionsから個別言語または `all` を選び、レビュー用Artifactを生成する。生成物は自動commit・push・mergeしない。

## 対応言語

- `all` — 下記4言語を1回のrunで順番に処理
- `ja` — 日本語
- `zh-CN` — 简体中文
- `ko` — 한국어
- `fr` — Français

追加言語は、Glossary・品質確認・language switcherまで含めて段階的に追加する。

## 実行

README変更のPRでは、APIを利用しない構造・リンク検証だけを自動実行する。翻訳APIの使用は手動の `workflow_dispatch` に限定する。英語READMEのpushだけでは翻訳が始まらず、API料金も発生しない。

Actionsの **README i18n** から **Run workflow** を開き、target languageを選択する。既定値は `all`。

通常の多言語更新では `all` を選ぶ。`all` は `ja / zh-CN / ko / fr` を同じjob内で**言語ごとのtranslatorプロセスとして直列実行**し、1回のrunで全4言語を生成する。各言語でrequest counterをリセットしつつ、8秒pacingとglobal concurrencyは維持する。

個別言語は翻訳品質の再検証や障害切り分け用に残す。

別々の手動run同士はOpenAI Projectの共有10 RPM枠を超えないよう同じconcurrency groupで直列化する。ただしGitHub Actionsのconcurrencyは実行中1件に加えてpending 1件のみ保持するため、個別runを同時に大量投入せず、通常は `all` を使用する。

2026-10-09の自動翻訳runは、日本語の翻訳途中で60 HTTP attempts上限に到達し失敗した。翻訳本文の入力単位が増えると60回では足りなくなるため、手動実行のみ各言語90 attemptsまで許容する。ただし実行上限を引き上げても成功や翻訳品質を保証するものではない。API利用量とArtifactを確認してから公開する。

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
- 個別言語runは最大90 HTTP attempts
- `all` runも各言語を個別processで直列実行し、各言語最大90 HTTP attempts
- 翻訳job timeout 75分（PRの無料構造検証は5分）

request guardは完全なsecurity sandboxではない。第三者translator codeがAPI keyと公開READMEを処理する信頼境界は残る。

## 公開フロー

1. `README.md` と翻訳READMEを更新（必要な場合はREADME i18nを手動で `all` 実行）
2. 翻訳Artifactを使う場合は、対象の構造・リンクを検証
3. 手動翻訳した場合は4言語を含む `readme-all` Artifactを回収
4. PRの無料構造検証と人間レビュー
5. 必要な表現を修正
6. 翻訳READMEとlanguage switcherをPR
7. レビュー後にmerge

初回PoCの経緯・実験結果は `docs/readme-i18n-poc.md` に残す。
