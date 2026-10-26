# 統合待ちブランチのマージエラー報告改善

## 背景（報告された問題）

提案画面の「統合待ちブランチ」でマージボタンを押すとエラーになる。

### 調査結果（2026-10-26, gh_portal の12本の統合待ちブランチで確認）

マージ失敗には2系統の原因があった:

1. **本物のコンフリクト（6本）** — task/gh_portal/118, 135, 148, 166, 194, 195。
   統合先 `stu-ui` と同一ファイル（Chat.tsx, Dashboard.tsx, dist/ 等）を変更しており
   `git merge` がコンフリクトする。
2. **統合先ワークツリーの未コミット変更によるブロック（6本）** — task/gh_portal/105, 154, 155, 159, 161, 184。
   内容的にはクリーンにマージ可能（`git merge-tree` で確認済み）だが、gh_portal 本体の
   作業ツリーに未コミット変更（AuthContext.tsx, database.types.ts, Register.tsx, dist/ 削除等）があり、
   マージ対象ファイルと重なるため git が
   `Please commit your changes or stash them before you merge.` で拒否する。

### コード上の欠陥

`gitutil.merge_branch()` は `git merge` の非ゼロ終了を**すべて "conflict" として返す**ため、
原因2のケースでも UI には「コンフリクトのため自動マージできません」と表示され、
本当の原因（未コミット変更）がユーザーに伝わらない。git の stderr も破棄される。

## 実装方針

### 変更スコープ

- `server/gitutil.py` — `merge_branch()` の失敗分類を3値化
  - `"merged"` / `"conflict"` / `"dirty: <git メッセージ>"` / `"error: <git メッセージ>"`
  - 判定: マージ失敗後に `MERGE_HEAD` が存在すれば本物のコンフリクト（abort して "conflict"）。
    存在しなければマージ自体が開始されておらず、stderr に
    `commit your changes or stash` / `would be overwritten` を含めば "dirty"、それ以外は "error"。
- `server/main.py` — `/api/autodev/merge` が分類に応じた日本語エラーメッセージを返す
  - conflict → 409「コンフリクトのため自動マージできません」
  - dirty → 409「統合先の作業ツリーに未コミット変更があるためマージできません」+ git メッセージ（detail）
  - その他 → 400 で git のエラーをそのまま返す
- `client/index.html` — `mergeWorktree()` がサーバーの error / detail をトーストに表示する

### スコープ外（環境側の問題、コードでは解決しない）

- gh_portal 本体の未コミット変更の整理（コミット/stash はユーザー判断）
- 6本の本物のコンフリクトの手動解決
- dist/（ビルド成果物）がコミットされているためタスクブランチ間で恒常的に
  コンフリクトする問題 → 別提案として扱う（.gitignore 化の検討）

## 実装状態

- [x] gitutil.merge_branch の失敗分類
- [x] main.py のエラーメッセージ分岐
- [x] client の表示改善
