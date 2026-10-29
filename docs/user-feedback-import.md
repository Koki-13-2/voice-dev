# ユーザーフィードバック取り込み（Supabase 連携）

## 概要

提案画面の「👤 意見取込」ボタンで、対象アプリの Supabase からユーザー投稿の改善提案
（`get_improvement_proposals_admin`）とフィードバック（`get_user_feedbacks_admin`）を取得し、
proposals/ のタスクチェックリストに追加する。

- API: `POST /api/proposals/import-user-feedback`（`server/main.py`）
- フロント: `importUserFeedback()`（`client/index.html`）
- 依存: `httpx`（`server/requirements.txt` に追加済み）

## Supabase キーの解決順序（実装済み）

1. voice-dev シークレット（対象アプリ名のスコープ）:
   `SUPABASE_SERVICE_ROLE_KEY` → `SUPABASE_ANON_KEY` → `VITE_SUPABASE_ANON_KEY`
2. フォールバック: 対象プロジェクトの `.env.local` / `.env` から同名キーを読む
3. いずれも無ければ 400 エラー（登録方法をメッセージで案内）

`SUPABASE_URL` も同様にシークレット → プロジェクト .env → 既定値の順で解決する。

## エラーハンドリング（実装済み）

- Supabase への HTTP 通信失敗（`httpx.HTTPError`）は 502 でエラーメッセージを返す。

## 障害記録: 2026-10-29 サーバー起動不能

キー解決フォールバック実装の途中、`try:` ブロックに対応する `except` が無いまま
`server/main.py` が保存されており、SyntaxError でサーバーが起動直後にクラッシュしていた
（スマホから「サーバに接続できませんでした」となる直接原因）。
`except httpx.HTTPError` 節を追加して修正し、サーバー再起動・Tailscale 経由
（https://100.65.1.43:8000 = 200 OK）で復旧を確認した。

### スマホ接続の注意

- 推奨URL: `https://kokinagao.taila7a9c1.ts.net:8000`（Tailscale証明書がこのDNS名で発行されているため）
- IP直（`https://100.65.1.43:8000`）は証明書名不一致の警告が出る。iOS Safari では
  WebSocket が黙って失敗する場合がある（`start.sh` のコメント参照）。
- サーバーが落ちている場合は WSL 側で `./start.sh` を実行する（tmux セッション `voice-dev`）。
