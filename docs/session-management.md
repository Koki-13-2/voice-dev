# セッション管理機能

## 概要

複数のClaudeセッションを並行して管理・操作できるようにする。
各セッションへのアクセス・中断・削除と、並行作業（複数セッション同時実行）を実現する。

## 実装方針

### Backend

#### `server/claude_client.py`
- `CLI_LOCK = asyncio.Lock()` → `asyncio.Semaphore(3)` に変更
  - 最大3セッションの並行CLI実行を許可
  - OAuth 401エラーの既存リトライ機構でカバー

#### `server/main.py`
- `SessionMeta` データクラスを追加（id / client / name / project / timestamps）
- `sessions` dict を `dict[str, ClaudeClient]` → `dict[str, SessionMeta]` に変更
- WebSocket ハンドラでセッションメタデータを更新（project_path, last_active）
- REST API を追加:
  - `GET /api/sessions` — 全セッション一覧
  - `POST /api/sessions` — セッション新規作成
  - `DELETE /api/sessions/{id}` — セッション削除（実行中は中断してから）
  - `POST /api/sessions/{id}/cancel` — 実行中セッションを中断

### Frontend (`client/index.html`)

- `SESSION_ID` の生成を `localStorage` → `sessionStorage` のみに変更
  - 新しいタブは自動的に独立した新規セッションを取得
  - URLパラメータ `?new_session=1` で強制新規セッション
- セッション管理モーダルを追加
  - 全セッション一覧（ステータス・プロジェクト名・最終アクティブ時刻）
  - 中断・削除ボタン
  - 新規セッション（新タブで開く）ボタン
- ヘッダーに「セッション」ボタンを追加

## 変更スコープ

| ファイル | 変更種別 |
|---|---|
| `server/claude_client.py` | Lock → Semaphore(3) |
| `server/main.py` | SessionMeta追加・REST API追加・WS更新 |
| `client/index.html` | SESSION_ID生成変更・モーダル追加・ヘッダーボタン追加 |

## ステータス

- [ ] 実装中
- [ ] 実装完了
