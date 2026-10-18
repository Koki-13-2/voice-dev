# voice-dev アップデート方針書 — 複数AIによる並列開発で開発スピードを向上させる

## 目的

voice-dev（音声入力でAIと会話しながらアプリ開発できる環境）を、
**複数のブランチで複数のAIエージェントを同時並行で動かし、互いに干渉せず
開発スピードを上げられるアプリ**にアップデートする。

安全性・事故防止は主眼にしない（別途検討）。ここでは
「同時に進められるタスクを増やす」機能拡充にフォーカスする。

実装前の設計合意用ドキュメント。実装時はこのファイルに沿って進め、
完了したらこのファイルに「実装済み」を追記する（CLAUDE.mdの運用ルールに従う）。

---

## 1. 現状のボトルネック（コードに基づく）

実は現在のvoice-devは、**構造的に並列実行ができない**つくりになっている。

### 1-1. タスクがアプリ全体で常に「1件だけ」しか取り出せない

`proposal_store.next_task()` は、全アプリの提案MDを順に走査して
「チェック済み・未完了」の**最初の1件だけ**を返す仕様（グローバルに1件）。

```python
def next_task() -> tuple[str, dict] | None:
    for f in sorted(PROPOSALS_DIR.glob("*.md")):
        for t in tasks:
            if t["checked"] and not t["done"]:
                return app_path, t   # ← 最初の1件で即return
```

`autodev_loop()` は60秒ごとにこの関数を呼ぶが、実行中のタスクがまだ
`done`になっていない間は、**毎回同じタスクが返ってきて `running_tasks` に
あるためスキップされる**。つまり他のアプリ・他のタスクが控えていても、
1つのタスクが終わるまで次に進めない。「並列実行用の `running_tasks` 辞書」
は存在するが、実際には常に最大1件しか入らない。

### 1-2. ブランチが「アプリ単位で1本」しか持てない

`proposal_store.set_branch` / `get_branch` は、ブランチ名を
**アプリのproposals MDのfrontmatter（`branch:`）に1つだけ**保存する。
タスク単位でブランチを分ける仕組みがない。

### 1-3. 全タスクが同じ作業ディレクトリ（同じgit index）を共有する

`autodev._run_task` は `app_path`（例：`gh_portal/`）を**そのまま**
作業ディレクトリとしてClaude CLIサブプロセスを起動する。

```python
proc = await asyncio.create_subprocess_exec(
    "claude", "-p", prompt, ..., cwd=app_path, ...
)
```

同じフォルダ・同じgit indexを複数プロセスが同時に触れば、
ファイル競合・コミット競合が即発生する。**これが並列化を阻む最大の壁。**
→ 解決には「タスクごとに独立した作業コピー」が必要（= git worktree）。

---

## 2. 実現したい姿

```
voice-dev
 ├─ タスクA ── worktree-A（branch: task/A）── AIエージェント1 ─┐
 ├─ タスクB ── worktree-B（branch: task/B）── AIエージェント2 ─┼─→ 統合（merge）
 └─ タスクC ── worktree-C（branch: task/C）── AIエージェント3 ─┘
```

- タスクごとに**専用の作業ディレクトリ（git worktree）**と**専用ブランチ**を割り当てる
- 複数のClaude CLIサブプロセスが**同時に**起動し、互いのファイル・git操作に干渉しない
- 完了したブランチは統合フローでまとめて取り込む
- 同時実行数は設定可能（API負荷・マシンリソースに応じて調整）

---

## 3. 機能拡充の方針

### 方針A：git worktreeによるタスク単位の作業ディレクトリ分離

- タスク実行時、`app_path` 直下ではなく `~/.voice-dev/worktrees/<app名>/<task_id>/` の
  専用ディレクトリに `git worktree add` でブランチを切り出す
  （リポジトリ内に置くと未追跡ファイルとしてAIエージェントのgit操作を汚染するため、リポジトリ外に置く）
- `gitutil.py` に `create_worktree(repo_path, branch, task_id)` /
  `remove_worktree(repo_path, task_id)` を追加
- Claude CLIサブプロセスの `cwd` をこのworktreeパスに向ける
  → 同じリポジトリでも物理的に別フォルダ・別git indexになるため、
    複数タスクが**本当に同時に**ファイル変更・コミットできる

### 方針B：タスク単位のブランチ命名・1タスク1ブランチ化

- `proposal_store` にタスクごとのブランチ名を持たせる
  （例：`task/{app_name}/{id}-{titleスラッグ}`）
- アプリ単位の `branch:` frontmatterは「統合先ブランチ（例：develop）」の意味に変更し、
  個別タスクはそこから分岐・そこへ合流する形にする

### 方針C：並列実行スケジューラへの変更

- `next_task()` を「1件返す」から「**実行可能なタスクを同時実行数の上限まで複数返す**」
  方式に変更する（`next_tasks(limit=N)`）
- 設定に `max_parallel_agents`（同時に動かすAIエージェント数の上限）を追加し、
  `autodev.py` の設定（`interval_min`, `model` と同じ場所）で管理する
- `running_tasks` 辞書は現状のまま活用でき、複数エントリが同時に入るようになる

### 方針D：完了ブランチの統合（マージ）フロー

- 各worktreeでタスクが完了・commit・push済みになったら、統合先ブランチへの
  マージを試みる処理を追加する
  - コンフリクトなし → 自動マージしてworktreeを削除
  - コンフリクトあり → マージせずログに「要確認」として記録し、
    ブランチ・worktreeは保持したまま次のタスクを進める（他タスクをブロックしない）
- UI（client）に「統合待ちブランチ一覧」を表示できるようにする

### 方針E：音声/チャットからの並列タスク指示

- 現在のチャットUIは1対話＝1タスクの直列実行が前提
- 「このタスクとこのタスクを同時に進めて」と話しかけると、
  複数タスクをそれぞれworktree化して並列起動できるようにする
  （内部的には方針A〜Cのスケジューラに乗せる）
- 実装形:
  - 提案画面の各行に「▶ 実行」ボタン、フィルタバーに「▶ チェック済みを並列実行」ボタンを追加
  - API `POST /api/autodev/run-now`（app_path + タスクID配列）で即時並列起動
  - 提案モードのチャット/音声入力で「#3 と #5 を並列実行」のように
    `並列` / `同時` キーワード + `#id` を含む発話を検出し、同APIに流す

### 方針F：マルチチャット並行開発（バックグラウンド継続 + チャットログ永続化）

別の機能開発の指示チャット（別画面・別タブ・別セッション）に移動しても、
元のチャットの作業が裏で継続し、会話ログが記録され、戻ると完全に復元される仕組み。

- **チャットログの永続記録（サーバー側）**
  - `server/chatlog_store.py`（新規）: セッションごとに
    `~/.voice-dev/chatlogs/<session_id>.jsonl` へ1イベント1行で追記
  - 記録対象: ユーザー発話 / AI本文 / ツール実行 / エラー / 保存イベント
    （要件定義書保存・提案追加）
  - 各エントリに連番 `seq` を付与し、WS配信チャンクにも `log_seq` を載せる
    → 再接続時の「ログ復元」と「未配信バッファ再送」の二重表示を seq 比較で排除
- **セッションメタの永続化（サーバー再起動に耐える）**
  - `server/session_store.py`（新規`）: `~/.voice-dev/sessions.json` に
    id / name / project_path / created_at / last_active / claude_session_id を保存
  - 起動時に復元するため、サーバー再起動後も Claude CLI の `--resume` で会話継続できる
- **フロントエンド**
  - ページロード時に `GET /api/sessions/{id}/log` でログを取得し、WS接続**前に**履歴を復元描画
  - セッション管理モーダルに「📂 開く」ボタンを追加（同タブでそのセッションへ切替）
  - 既存のTaskManager（切断後もタスク継続・バッファ配信）はそのまま活用

---

## 4. 段階的実装案（フェーズ分け）

| フェーズ | 内容 | 狙い |
|---|---|---|
| Phase 1 | `gitutil.py` にworktree作成/削除関数を追加 (方針A) | 並列化の土台 |
| Phase 2 | タスク単位ブランチ命名への変更 (方針B) | タスクとブランチの1:1対応 |
| Phase 3 | `next_tasks(limit=N)` + 同時実行数設定 (方針C) | 実際に複数タスクを同時起動 |
| Phase 4 | 完了ブランチの自動マージ/要確認ログ (方針D) | 統合の自動化 |
| Phase 5 | チャット/音声からの並列タスク指示 (方針E) | UX面での並列活用 |
| Phase 6 | チャットログ永続化 + セッション復元 (方針F) | 別画面に移っても並行開発できるUX |

Phase 1〜3で「複数AIが同時に動いて干渉しない」が実現する。
Phase 4〜6は、それを使いやすくする仕上げ。

## 5. やらないこと（スコープ外）

- 危険なgit操作のガード・権限制御（別の方針として扱う。今回は速度優先）
- 完全なCI/CD統合（ビルド・テストの自動実行基盤までは作らない。
  必要になった時点で別途検討）

---

## 実装状況

- [x] Phase 1: worktree作成/削除関数 — **実装済み（2026-10-18）**
- [x] Phase 2: タスク単位ブランチ命名 — **実装済み（2026-10-18）**
- [x] Phase 3: 並列スケジューラ（`next_tasks` + 同時実行数設定） — **実装済み（2026-10-18）**
- [x] Phase 4: 完了ブランチの統合フロー — **実装済み（2026-10-18）**
- [x] Phase 5: チャット/音声からの並列タスク指示 — **実装済み（2026-10-18）**
- [x] Phase 6: チャットログ永続化 + セッション復元（方針F） — **実装済み（2026-10-18）**

### 実装メモ（2026-10-18）

**Phase 1（gitutil.py）**
- `create_worktree(repo_path, branch, task_id, base)` / `remove_worktree` / `list_worktrees` /
  `merge_branch(repo_path, branch, into)` / `push` を追加
- worktreeは `~/.voice-dev/worktrees/<app名>/<task_id>/` に作成（リポジトリ外）
- `merge_branch` はコンフリクト時に自動 `merge --abort` して `"conflict"` を返す

**Phase 2（proposal_store.py）**
- `task_branch_name(app_name, task)` → `task/<app>/<id>[-<英数slug>]`（日本語タイトルはid のみ）
- アプリ単位の `branch:` frontmatter は「統合先ブランチ」の意味に変更
  （UI表示も「🌿 統合先ブランチ」に変更）

**Phase 3（proposal_store.py / autodev.py）**
- `next_tasks(limit=N)` を追加（`next_task()` は互換APIとして維持）
- 設定に `max_parallel_agents`（既定3、UIで1〜5選択）を追加
- `autodev_loop` は interval ごとに空きスロット分（`_launch_up_to_limit`）を一括起動
- `_run_task` は worktree + タスクブランチで実行（非gitアプリはapp直下にフォールバック）

**Phase 4（autodev.py / main.py / client）**
- タスク成功後 `_integrate_branch` が統合先へ自動マージ → 成功時worktree削除+push
- コンフリクト時はworktree・ブランチ保持のままログに「要確認」記録（他タスクをブロックしない）
- `GET /api/autodev/worktrees` / `POST /api/autodev/merge` を追加し、
  提案画面に「🔀 統合待ちブランチ」一覧+マージボタンを表示

**Phase 5（autodev.py / main.py / client）**
- `POST /api/autodev/run-now`（即時並列起動）、`autodev.run_now()` を追加
- 提案画面: 各行「▶」ボタン + ヘッダー「▶ 並列実行」（チェック済み一括）
- 提案モードのチャット/音声で「#3 と #5 を並列実行」「3番と7番を同時に」を
  `parse_parallel_request` が検出して即時起動

**Phase 6（chatlog_store.py / session_store.py / main.py / client）**
- `chatlog_store`: `~/.voice-dev/chatlogs/<session_id>.jsonl` に全会話イベントを連番seq付きで永続記録
- `session_store`: `~/.voice-dev/sessions.json` にセッションメタ+`claude_session_id` を保存し、
  サーバー再起動後も `--resume` で会話継続可能
- `GET /api/sessions/{id}/log` でログ取得。クライアントはロード時に履歴復元→WS接続の順で初期化し、
  チャンクの `log_seq` と復元済み最大seqの比較で二重表示を排除
- セッション管理モーダルに「📂 開く」（同タブでセッション切替・ログ復元）を追加
- 切断中のタスク継続・バッファ配信は既存TaskManagerをそのまま活用

**検証**: 全モジュールのコンパイル・ユニットテスト（chatlog/branch命名/並列指示パース/
worktree作成→コミット→マージ→削除）・FastAPI TestClientによるAPIスモークテストを実施し全合格。
