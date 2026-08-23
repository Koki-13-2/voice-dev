# Claude Codeアカウント管理機能

## 背景・目的

Claude Code CLIは1台のPC上で `~/.claude/.credentials.json` に1アカウント分のログイン情報のみを保持する。
複数のClaudeアカウント（例: 個人用/仕事用、複数のMaxプラン契約）を使い分けたい場合、
その都度 `claude auth login` / `claude auth logout` をターミナルで手動実行する必要があり不便。

このアプリ上で
- 複数アカウントのログイン情報を保存
- アカウントの手動切替
- アカウントごとの利用量（トークン使用量の目安）確認

を行えるようにする。

## 既知の制約（重要）

- Anthropic / Claude Code CLIは「残りトークンクォータ（5時間/週次の利用上限に対する残量）」を
  取得できる公開APIやCLIコマンドを提供していない。`claude auth status` はログイン状態・メールアドレス・
  組織名・プラン種別（`subscriptionType`）のみを返す。
- そのため「残トークン」は **正確な残量ではなく、アプリ経由でclaude CLIを呼び出した際の
  累計使用トークン数（入力/出力/キャッシュ）を自己集計した目安カウンター** として実装する。
  ユーザーが手動でカウンターをリセットできるようにする（利用上限リセットのタイミングに合わせて）。
- ログイン自体（OAuthブラウザ認証）はアプリ内で完結させない。ユーザーが `claude auth login` を
  ターミナルで実行してログイン後、アプリの「現在ログイン中のアカウントを保存」ボタンで
  そのログイン情報（`~/.claude/.credentials.json`）をスナップショットとして登録する運用とする。
- WSL/Linux環境ではOSキーチェーンを使わずファイル (`~/.claude/.credentials.json`) に
  認証情報を保存する前提（このマシンでの `claude auth status` / `.credentials.json` の実在で確認済み）。

## 実装方針

### データ保存先

`~/.voice-dev/accounts/<アカウント名>/`
- `credentials.json` — `~/.claude/.credentials.json` のスナップショット（600権限）
- `meta.json` — `{label, email, org_name, subscription_type, auth_method, saved_at, last_switched_at}`
- `usage.json` — `{since, calls, input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens, total_cost_usd, last_used_at}`

`~/.voice-dev/accounts/active.json` — `{"name": "現在アクティブなアカウント名"}`（アプリ経由の切替を追跡するマーカー。
アプリ外で `claude auth login` された場合はズレる可能性があるため、一覧表示時に現在の
`~/.claude/.credentials.json` の内容とスナップショットを比較して active 判定する）。

### バックエンド

- `server/account_store.py`（新規）
  - `list_accounts()` / `save_current_as(name, label)` / `switch_to(name)` /
    `delete_account(name)` / `record_usage(name, usage)` / `reset_usage(name)` / `get_active_name()`
  - `save_current_as`: `claude auth status` で現在のログイン情報を取得し保存。未ログイン時はエラー。
  - `switch_to`: 切替前に現在アクティブな既知アカウントの資格情報を最新化してから保存し
    （トークンリフレッシュ分を失わないため）、対象アカウントの `credentials.json` を
    `~/.claude/.credentials.json` へ書き戻す。
- `server/claude_client.py`
  - `send_message` / `run_oneshot` の最終 `result` イベントから `usage` / `total_cost_usd` を取り出し、
    `{"type": "usage", "usage": {...}, "cost_usd": ...}` チャンクとして追加yieldする。
- `server/main.py`
  - `_run_chat` / `_generate_oneshot` で `type == "usage"` のチャンクを検知したら
    `account_store.record_usage(現在のactive account, usage)` を呼び、UIには転送しない。
  - API: `GET /api/accounts`, `GET /api/accounts/whoami`, `POST /api/accounts`,
    `POST /api/accounts/{name}/switch`, `DELETE /api/accounts/{name}`,
    `POST /api/accounts/{name}/usage/reset`

### フロントエンド（client/index.html）

- ヘッダーに「👤 アカウント」ボタンを追加し、既存の秘密情報モーダル（`fp-overlay`パターン）と
  同様のオーバーレイでアカウント一覧モーダルを表示する。
- 一覧: ラベル・メール・プラン種別・アクティブ状態・累計使用トークン数（+リセットボタン）・
  切替ボタン・削除ボタン。
- フッターに「現在ログイン中のアカウントを保存」フォーム（名前入力 + 保存ボタン）。
  保存前に `GET /api/accounts/whoami` で現在ログイン中の情報を表示して確認できるようにする。

## 実装状態

- [x] 設計MD作成
- [x] `server/account_store.py`
- [x] `server/claude_client.py` usageチャンク追加
- [x] `server/main.py` API + usage記録フック
- [x] `client/index.html` アカウント管理UI（ヘッダー 👤 ボタン → モーダル）
- [x] 動作確認（`py_compile`、`node --check`、実サーバー起動＋全API疎通テスト（保存/切替/使用量リセット/削除）で確認済み）

### 使い方

1. ターミナルで `claude auth login` を実行し、追加したいアカウントにログインする
2. アプリのヘッダー 👤 ボタン → 「現在ログイン中のアカウントを保存」に名前を入力して保存
3. 別アカウントも同様にログイン→保存を繰り返す
4. 一覧の「切替」ボタンでアクティブなアカウントを切り替える（`~/.claude/.credentials.json` を書き換える）
5. 累計使用トークン数が一覧に表示される。上限リセットのタイミングで「使用量リセット」を押すと0に戻せる

### 既知の限界

- 表示される使用量は「このアプリ経由でclaude CLIを呼び出した分の累計」であり、Anthropic側の
  実際の残クォータとは一致しない（ブラウザやターミナルなど他経路での利用は反映されない）
- アカウント切替時、既存の会話セッションは自動的にリセットされる（別アカウントのセッションIDで
  `--resume` すると401エラーになるため）
