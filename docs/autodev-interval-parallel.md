# 自動開発: 間隔設定UI + 並行稼働対応

## 概要

自動開発の実行間隔を画面上で設定可能にする。間隔を短くしても前タスクの完了を待たず並行実行できるよう、直列制約を除去する。

## 変更スコープ

### server/autodev.py

- `current_task` (単一 dict) → `running_tasks` (dict の dict, キー=タスクID) に変更
- `autodev_loop()` の `current_task is not None` ガードを削除。間隔タイマーのみでタスク発火を制御
- `_run_task()` を `asyncio.create_task()` で非同期起動し、ループをブロックしない
- `claim` 機構はプロセス跨ぎ多重ループ防止用なので維持。ただし「1件実行中」ではなく「ループ所有権」として使う
- `TASK_TIMEOUT_SEC` は引き続きタスク単体のタイムアウトとして機能
- `status()` で `running_tasks` の全件を返す

### client/index.html

- `autodevBarHtml()` に間隔変更UIを追加（数値入力 or セレクト）
- `setAutodevInterval()` 関数追加: `POST /api/autodev` に `interval_min` を送信
- `running` 表示を複数タスク対応に変更

### server/main.py

- 変更なし（`POST /api/autodev` は既に `interval_min` を受け付ける）

## 実装方針

- 各タスクは `claude -p` のワンショット起動で独立プロセスのため、並行実行しても互いに干渉しない
- `running_tasks` は asyncio 単一スレッドで操作されるためロック不要

## ステータス

- [x] 実装済み（2026-07-07）
