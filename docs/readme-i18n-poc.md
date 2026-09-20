# README英日翻訳PoC

既存翻訳エンジンの採用可否を検証する実験。正式採用・全リポジトリ展開を決定したものではない。

## 対象と実行

- 原本は公開済み `README.md` のみ。出力先は日本語の `README.ja.md`。
- `rockbenben/md-translator` を `25d07cebc70266ed06bcfb7e5e1ef97253c3e998` に固定。
- `workflow_dispatch` の手動実行のみ。生成物はArtifactへ保存し、自動commit/push/mergeは行わない。
- 現行の接続先はOpenAI公式Chat Completions、モデルは `gpt-5.6-luna`。無料GTXを使った初期試験とは設定が異なる。
- `OPENAI_API_KEY` をActions Repository Secretに登録する。翻訳以外のステップに明示的に渡さない。
- 修正後は古いrunの「Re-run jobs」ではなく、対象ブランチの「Run workflow」で新規実行する。

## 10 RPMへの対策

`.i18n/translation-fetch-guard.mjs` をCLIより先に読み込み、既存エンジンのglobal fetch経路を制御する。
通常翻訳・接続確認・用語集再翻訳・HTTP再試行を同じキューに通し、送信開始を最低8秒間隔にする。
このプロセスの送信は任意の60秒間で最大8件。失敗したHTTP/通信の試行も数える。
429の `Retry-After` を尊重し、ヘッダーがなければ60秒待つ。ガード自身は再試行せず、上流の再試行を制御する。
1実行で最大60リクエスト、ジョブ全体で20分を上限とする。同名workflowの多重実行も直列化する。

これは**当該プロセスのRPM対策**であり、他のクライアントが使う共有枠、TPM、課金残高、支出上限を保証しない。
翻訳側の並列数も1にし、各レスポンスのトークン上限を2048にする。上限により出力が打ち切られた場合は失敗として調査する。

## 秘密情報と通信

- RepositoryのGitHub権限は `contents: read`。checkout認証情報を作業ツリーに残さない。
- 翻訳APIキーは実行時に権限0600の一時設定ファイルへ埋め込み、終了時に削除する。CLI引数・git・Artifactには含めない。
- ガードはOpenAIの指定URLへのPOSTのみ許可し、Standard (`service_tier: default`)を指定する。リダイレクトは追従せず失敗する。
- Relayは無効。依存インストールスクリプトも `--ignore-scripts` で無効。
- ガードは**セキュリティサンドボックスではない**。別のHTTPライブラリや任意の悪意あるコードまで隔離しない。
- 第三者コードが翻訳APIキーと公開READMEを処理する信頼境界は残る。プロバイダーの保持・学習利用条件は別に確認する。
- キャッシュと秘密を含む設定ファイルはArtifactへアップロードしない。Artifactは生成された公開READMEに限定する。

## 検証

`node --test .i18n/translation-fetch-guard.test.mjs` はモック通信と仮想時計を使い、APIキーも外部APIも使わない。
並列呼び出し、再試行、429、キャンセル、回数上限、接続先制限、プリロードを検証する。
モックテスト合格と、実APIでの認証成功・翻訳品質・完全な通信監査は別である。

現状の自動品質チェックは出力ファイルの存在と指定用語の存在のみ。Markdownの構造、コード、リンク、パス、
用語の全出現箇所、自然な日本語、欠落の有無はArtifactを人間がレビューする。失敗時も生成済みファイルは回収する。

試験のためdefault branchを一時変更した場合は、実行結果回収後に `main` へ戻す。
