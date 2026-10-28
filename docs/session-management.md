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

## 追加機能: ワークスペース画面の過去チャット一覧（2026-10-28）

### 要件

- 開発タブ直下のフォルダ選択画面（hennyujuku / private-dev を選ぶ最上位画面）に、別枠で「過去のチャット」一覧を表示する
- 一覧のセッションをタップすると、過去のチャットログを復元したうえで続きの会話ができる
  （サーバー側の `claude_session_id` により Claude CLI の `--resume` で会話コンテキストも継続）
- 各セッション行を左スワイプすると「⏸ 停止」「🗑 削除」ボタンが現れ、その場で操作できる

### 実装方針

#### Backend (`server/main.py`)

- `GET /api/sessions/{id}/log` のレスポンスに `project_path` / `project_name` / `name` を追加
  - 過去セッションを開いた際にフロント側でプロジェクト選択状態を復元し、
    プロジェクト再選択なしで続きの会話を送信できるようにするため

#### Frontend (`client/index.html`)

- `showWorkspacePicker()`（開発モードのみ）: ワークスペースグリッドの下に
  「💬 過去のチャット」セクションを追加し、`GET /api/sessions` から
  `has_log || running` のセッションを最終アクティブ順に表示
- セッション行: ステータス（🟢実行中/⚪停止）・名前・プロジェクト名・最終アクティブ時刻
- 左スワイプ（Pointer Events でタッチ/マウス両対応）: アクションボタンを表示
  - ⏸ 停止 … `POST /api/sessions/{id}/cancel`（実行中のみ表示）
  - 🗑 削除 … `DELETE /api/sessions/{id}`（確認ダイアログあり）
- タップ: `/?session_id=<id>` へ遷移（既存のセッション切替機構を利用）
- `restoreHistory()`: URLに `session_id` があり、セッションに `project_path` が
  記録されている場合（開発モード）、プロジェクト選択状態を復元して
  ピッカーの代わりにチャット画面（クイックアクション + 入力有効）を表示

### 変更スコープ（追加分）

| ファイル | 変更種別 |
|---|---|
| `server/main.py` | `/api/sessions/{id}/log` レスポンス拡張 |
| `client/index.html` | ピッカーに過去チャット枠・スワイプ操作・セッション復帰時のプロジェクト復元 |

## ステータス

- [x] 実装中
- [x] 実装完了
- [x] 追加機能（過去チャット一覧 + スワイプ操作）実装完了

### 追加機能の実装メモ

- `GET /api/sessions/{id}/log` に `name` / `project_path` / `project_name` を追加（curlで動作確認済み）
- ワークスペース選択画面（開発モードのみ）に「💬 過去のチャット」枠を追加
  （`has_log || running` のセッションのみ表示、空セッションは除外、このタブのセッションには「（このタブ）」表示）
- スワイプは Pointer Events 実装（タッチ/マウス両対応、縦スクロールと干渉しないよう方向判定あり、同時に開く行は1つ）
- タップ時: 別の行が開いていれば閉じるだけ（誤タップ防止）。何も開いていなければ `/?session_id=` で遷移
- セッション再開時: `project_path` があればプロジェクト選択状態を復元してチャット画面を表示。
  実行中タスクがあるセッションでは入力を無効のままにし、WS再接続のバッファ配信に任せる
- 現在タブのセッションを削除した場合は WS に `reset` を送信して会話コンテキストをクリア

### 実装メモ

- `SessionMeta`（id/client/name/project_path/created_at/last_active）を追加し、`sessions: dict[str, SessionMeta]` に変更
- `TaskManager.cancel()` を追加（実行中asyncio.Taskをキャンセル→キュークリーンアップ、全モード共通で使用）
- REST API 4種（`GET/POST /api/sessions`, `POST /api/sessions/{id}/cancel`, `DELETE /api/sessions/{id}`）を実装
- フロントエンドの `SESSION_ID` を `sessionStorage` のみに変更（新タブ=新規セッション）。`?session_id=` / `?new_session=1` クエリに対応
- ヘッダーに🗂セッション管理ボタンとモーダル（一覧・中断・削除・新規セッションを新タブで開く）を追加
- セッション名は未指定時、最初のチャット送信時の `project_path` のディレクトリ名を自動設定（リネームAPIは今回のスコープ外）
