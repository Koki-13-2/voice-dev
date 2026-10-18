# 提案出力数セレクター

## 概要

提案モードで生成する提案の個数をユーザーが指定できるようにする。

## 変更スコープ

### client/index.html
- 「提案を生成」ボタンの左にプルダウン（select）を追加
- 選択肢: 1 / 3 / 5 / 10 / 15 / 20（デフォルト: 10）
  - 2026-10-18: 少数生成のニーズに応え 1件・3件 を追加（5件未満も選択可能に）
- WebSocket送信時に `proposal_count` を含める

### server/main.py
- WebSocketメッセージから `proposal_count` を取得し `_run_propose` に渡す
- `PROPOSE_PROMPT` の「10件程度」を `{count}件程度` に変更
- `_run_propose` に `count` 引数を追加

## 個別要件入力

既存の🎤/テキスト入力 → `user_hint` の仕組みをそのまま使用。追加実装なし。

## ステータス

- [x] 実装済み
