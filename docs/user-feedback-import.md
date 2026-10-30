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

## 変更スコープ: 2026-10-30 一覧選択モーダル化 + DB ステータス管理

### 実装方針

- ボタンを押すと即取り込みではなく、未処理フィードバックの一覧ポップアップを表示
- チェックボックスで複数選択 → 「取込」または「棄却」ボタンで処理
- 取込時は Claude でエンジニア向けに文章を書き直してから proposals MD に追加（Supabase の原文は変更しない）
- 取込・棄却ともに Supabase の `import_status` カラムを更新する

### DB 変更（Supabase / gh-portal）

`supabase/migrations/20261030000001_add_import_status.sql`：

- `public.user_feedbacks` に `import_status text` 列追加（null = 未処理, 'imported', 'rejected'）
- `public.improvement_proposals` に同カラム追加
- 両 RPC 関数を `import_status` 返却対応に更新（`CREATE OR REPLACE FUNCTION`）

gh-portal アプリ側のコードは RPC の戻り型変更のみで、既存の INSERT/UPDATE クエリに影響なし。
`database.types.ts` は自動生成のため `supabase gen types typescript` で再生成推奨（動作には影響なし）。

### API 変更（voice-dev / server/main.py）

| メソッド | パス | 役割 |
|---|---|---|
| GET | `/api/proposals/pending-feedbacks` | `import_status IS NULL` のフィードバックを返す |
| POST | `/api/proposals/process-feedbacks` | 選択アイテムを取込/棄却処理する |

既存の `POST /api/proposals/import-user-feedback` はそのまま維持（後方互換）。
`_load_supabase_creds()` ヘルパーを抽出して両エンドポイントで共有。

### フロント変更（client/index.html）

- `importUserFeedback()` をモーダル起動に変更
- モーダル内：タイプ別一覧 / チェックボックス / 全選択 / 取込・棄却ボタン

### gh-portal 追加マイグレーション

`supabase/migrations/20261030000002_set_import_status_rpc.sql`：

- `set_feedback_import_status(p_type, p_id, p_status)` RPC を追加
- SECURITY DEFINER で anon キーからも UPDATE 可能にする

`src/pages/admin/AdminFeedback.tsx`：

- `Proposal` / `Opinion` 型に `import_status` フィールド追加
- 取込済 / 棄却済バッジを各カードに表示

### 実装ステータス

- [x] DB マイグレーション（import_status カラム）: 20261030000001
- [x] gh-portal: set_import_status_rpc マイグレーション: 20261030000002
- [x] server/main.py: pending-feedbacks / process-feedbacks エンドポイント
- [x] client/index.html: フィードバック取込モーダル JS 実装（スクリプト構造バグ修正含む）
- [x] gh-portal AdminFeedback.tsx: import_status バッジ

---

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
