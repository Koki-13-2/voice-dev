# 提案 不採用機能

## 概要

提案に「不採用」ボタンを追加し、不採用とした提案を通常の一覧から非表示にする。
不採用提案は別セクション「不採用提案集」に表示され、復元・実装が可能。

## 要件

- 未実装の各提案に「不採用」ボタンを表示する
- 不採用にした提案はメインリストから非表示にする
- 「不採用提案集」セクションを設け、不採用提案を一覧表示する
- 不採用提案集から「復元」操作で通常リストに戻せる
- 実装済み・未実装・不採用すべての提案が後から見返せる状態を維持する

## 設計

### データ構造

MDファイルのHTMLコメントに `rejected:` フィールドを追加:
```
- [ ] 【機能/中】タイトル — 説明 <!-- id:2 rejected:2026-07-14T10:00 -->
```

### 状態遷移

- 未採用(pending): checked=false, done="", rejected=""
- 実装予約(queued): checked=true, done="", rejected=""
- 実装済み(done): done に値あり
- 不採用(rejected): rejected に値あり

### バックエンド変更

- `proposal_store.py`:
  - `_TASK_RE` に `rejected:` キャプチャを追加
  - `_task_line()` に rejected 出力を追加
  - `reject_task()` / `restore_task()` 関数を追加
  - `next_task()` は既に checked && !done のみ見るため影響なし

- `main.py`:
  - `POST /api/proposals/reject` エンドポイント追加
  - `POST /api/proposals/restore` エンドポイント追加

### フロントエンド変更

- 各 pending 行に「不採用」ボタンを追加
- rejected 提案をメインリストから除外
- 折りたたみ式「不採用提案集」セクションを追加（復元ボタン付き）

## ステータス

- [x] 実装方針策定
- [x] 実装済み
