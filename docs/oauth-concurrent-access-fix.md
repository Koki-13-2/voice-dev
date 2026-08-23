# 複数デバイス同時接続時のOAuthエラー対策

## 背景・症状

PCとスマホなど複数デバイスから同じvoice-devサーバーに同時接続し、それぞれで
Claude Codeとのやり取り（チャット送信・要件定義書/提案のワンショット生成）が
ほぼ同時に走ると、`claude` CLIが401 OAuthエラーを返すことがある。

`SESSION_ID` はブラウザごとに `crypto.randomUUID()` で生成され `localStorage` に
保存されるため、PC/スマホは別々の `ClaudeClient` インスタンス（別プロセス）を持つ。
しかし両者が起動する `claude` CLIは、同一OSユーザーの単一ファイル
`~/.claude/.credentials.json` に保存されたOAuthトークン（ローテーション式・
使い切り）を共有しており、ここにロックが無い。2つの `claude` プロセスがほぼ同時に
起動しトークンリフレッシュを試みると、片方のリフレッシュが失効し401になる。

`server/claude_client.py` の `send_message` には既に「401検知→セッションリセット→
1回だけ再試行」の仕組みがあるが、`run_oneshot`（アイデアDB/改善提案の一括生成で
使用）には同等の保護が無い。また `_AUTH_ERROR_PATTERNS` によるエラー判定は
`send_message` 側にしか使われていなかった。

## 実装方針

1. **`claude` CLIサブプロセス呼び出しを直列化する**
   `server/claude_client.py` にプロセス全体で共有する `CLI_LOCK = asyncio.Lock()` を
   追加し、`_send_message_impl` と `run_oneshot`（内部実装）のサブプロセス起動〜
   終了までを `async with CLI_LOCK:` で囲む。これにより同一サーバープロセス内で
   `claude` CLIが同時に複数起動することがなくなり、OAuthトークンリフレッシュの
   競合を防ぐ。
2. **`run_oneshot` にも401リトライ保護を追加する**
   `send_message` と同じパターン（`_is_auth_error` 判定→1回だけ再試行）を
   `run_oneshot` にも実装し、内部実装を `_run_oneshot_impl` に切り出す。
3. **スコープ外（既知の残課題）**
   `server/autodev.py` の自動開発スケジューラも `claude` CLIを起動するが、
   1タスク最大25分かかるため、これを同じロックに含めると対話チャットが
   最大25分ブロックされうる。今回の報告（スマホ接続時のOAuthエラー）は
   対話的な複数デバイス利用が主因のため、autodev は今回のスコープ外とする。
   autodevとの競合が問題になった場合は別途対応する。

## 実装状態

- [x] 設計MD作成
- [x] `server/claude_client.py` に `CLI_LOCK` 追加、`_send_message_impl`/
      `run_oneshot` のCLI呼び出しを直列化
- [x] `run_oneshot` に401検知＋1回リトライを追加（`_run_oneshot_impl` に分離）
- [x] `python -m py_compile server/claude_client.py` で構文確認済み
- [ ] 実機での動作確認（PC+スマホ同時接続で401が再現しないこと）は未実施。
      実際のClaude Code CLI呼び出しを伴うため、週次利用上限を消費しないよう
      ユーザー側での確認を推奨する。
