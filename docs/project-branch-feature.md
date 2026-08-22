# プロジェクトごとのGitブランチ管理機能

## 概要

各ターゲットプロジェクトにGitブランチを関連付け、自動開発（autodev）やdevモードでの実装をそのブランチ上で行えるようにする。

## 変更スコープ

### 1. gitutil.py — ブランチ操作ユーティリティ追加

ターゲットプロジェクトの git リポジトリに対するブランチ操作関数を追加:

- `list_branches(repo_path)` — ブランチ一覧（現在のブランチも返す）
- `checkout_or_create(repo_path, branch)` — ブランチを切替（なければ作成）
- `get_current_branch(repo_path)` — 現在のブランチ名を取得

### 2. proposal_store.py — フロントマターに `branch` フィールド追加

```yaml
---
app: my-app
app_path: /home/user/private-dev/my-app
branch: feature/improvement
---
```

- `load()` の戻り値に `branch` を含める
- `set_branch(app_path, branch)` 関数を追加

### 3. autodev.py — タスク実行前にブランチ切替

`_run_task()` 内で:
1. proposal のフロントマターから `branch` を取得
2. ブランチが指定されていれば `checkout_or_create()` で切替
3. タスク実行（claude CLI）
4. コミット・プッシュはそのブランチ上で行われる

### 4. main.py — API追加

- `GET /api/branches?project_path=...` — プロジェクトのブランチ一覧
- `POST /api/proposals/branch` — プロジェクトの開発ブランチを設定

### 5. client/index.html — 提案画面にブランチセレクタ追加

提案画面ヘッダーに:
- 現在のブランチ表示
- ブランチ選択ドロップダウン
- 新規ブランチ作成ボタン

## 実装方針

- ブランチ未設定時はデフォルトブランチ（main/master）で動作（既存動作と同じ）
- ブランチ操作はターゲットプロジェクトの git リポジトリに対して行う（voice-dev のリポジトリではない）
- git リポジトリでないプロジェクトではブランチ機能を非表示にする

## ステータス

- [x] gitutil.py ブランチ操作
- [x] proposal_store.py branch フィールド
- [x] autodev.py ブランチ切替
- [x] main.py API
- [x] client/index.html UI
