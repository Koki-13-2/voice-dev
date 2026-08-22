# 提案生成UIの改善：AIログ非表示化

## 概要

提案生成時のAIストリーミングログ（テキスト・ツール使用）を非表示にし、
ボタン上のインラインインジケーター＋完了トーストのみで進捗を表示する。

## 要件

- 提案生成中のAIログ（text, tool_start, tool_end, thinking）を画面に表示しない
- 「提案を生成」ボタンがスピナー＋経過時間インジケーターに変わる
- 生成完了時にトースト通知を表示（既存の proposals_updated を活用）
- 音声入力による提案生成は従来通りAIログを表示する（ボタン経由のみ非表示）

## 設計

### フラグ管理

- `proposalGenerating` フラグで生成中かどうかを判定
- `generateProposals()` でフラグON、`proposals_updated` / `done` / `error` でフラグOFF

### 変更箇所

- `generateProposals()`: `send()` を使わず直接 WS 送信。ボタンをインジケーターに差し替え
- `handleServerMessage()`: `proposalGenerating` 中は text/tool_start/tool_end/thinking をスキップ

## ステータス

- [x] 実装方針策定
- [x] 実装済み
