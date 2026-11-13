# 提案タスク管理の Supabase 移行（2026-11-13 着手）

## 目的

提案機能のタスク管理を **テキストファイル（`proposals/*.md`）から Supabase に全面移行**する。
Supabase を唯一の正とし、アプリ（voice-dev）は Supabase を読み込み、更新を Supabase に書き戻す。

### 決定事項（ユーザー確認済み）

1. **対象範囲**: 全タスク（AI自動生成の提案 + 意見取り込み由来）を Supabase 化。`proposals/*.md` のタスク台帳は廃止。
2. **テーブル設計**: 既存テーブル（`improvement_proposals` / `user_feedbacks`）に **列追加のみ**。既存列の編集・削除はしない。
3. **Supabase 対象**: 対象アプリ各自の Supabase（gh_portal など）。
4. **AI生成提案**: `improvement_proposals` に行として INSERT し、`dev_source` 列で AI / ユーザー投稿を区別（タグ管理）。

## 現状（移行前）

- タスク台帳は `proposals/<app>.md`（`server/proposal_store.py`）。フィールド: id(連番) / angle / title / desc / checked / done / rejected、メタ: branch / app_path。
- 意見取り込み: Supabase の `improvement_proposals` / `user_feedbacks`（`import_status` 列: null/imported/rejected）から取得 →
  Claude がエンジニア向けに書き直し → MD にタスク追加。
- AI自動生成: 企画/提案モードの出力をパース → MD に蓄積。
- autodev: `next_tasks()` が `proposals/*.md` を走査し checked タスクを拾う。

## 移行後アーキテクチャ

### Supabase 列追加（gh_portal リポジトリの migration）

既存列は不変。以下を **追加のみ**（`ADD COLUMN IF NOT EXISTS`）。

`improvement_proposals`:
| 列 | 型 | 用途 |
|---|---|---|
| `dev_source` | text default 'user' | 'user'（ユーザー投稿）/ 'ai'（AI生成） |
| `dev_task_title` | text | エンジニア向けタイトル |
| `dev_task_desc` | text | エンジニア向け説明 |
| `dev_task_angle` | text | 【観点】カテゴリ |
| `dev_task_queued` | boolean default false | autodev 実行キュー投入（旧 checked） |
| `dev_task_done_at` | timestamptz | 完了日時（旧 done） |
| `dev_task_rejected_at` | timestamptz | 不採用日時（旧 rejected、import_status='rejected' とは別） |

`user_feedbacks`: 上記のうち `dev_source` を除く同じ6列（ご意見は常にユーザー由来）。

**タスク判定**:
- `improvement_proposals`: `import_status = 'imported'`（取込済み）または `dev_source = 'ai'`（AI生成）。
- `user_feedbacks`: `import_status = 'imported'`。

**状態マッピング**: checked→`dev_task_queued` / done→`dev_task_done_at` / rejected(不採用)→`dev_task_rejected_at` /
angle・title・desc→`dev_task_*`。

### RPC（全て SECURITY DEFINER・anon へ GRANT）

anon キーで RLS をバイパスして読み書きするため（既存 `set_feedback_import_status` の前例に倣う）。

- `get_improvement_proposals_admin()` / `get_user_feedbacks_admin()` — 既存を CREATE OR REPLACE し
  追加列（`dev_source`, `dev_task_*`）を返却に含める（戻り型拡張、既存フィールドは不変で後方互換）。
- `import_feedback_as_task(p_type, p_id, p_angle, p_title, p_desc)` — 取込。`import_status='imported'` +
  `dev_task_*` を設定。
- `insert_ai_dev_task(p_tab, p_angle, p_title, p_desc, p_content)` RETURNS uuid — AI生成提案を
  `improvement_proposals` に INSERT。`dev_source='ai'`, `import_status='imported'`, `user_id` は
  owner プロフィール（`is_owner`→`is_admin`→先頭）を採用（user_id NOT NULL FK のため）。
- `set_dev_task_queued(p_type, p_id, p_queued)` — 旧 set_checked。
- `mark_dev_task_done(p_type, p_id)` — `dev_task_done_at = now()`。
- `set_dev_task_rejected(p_type, p_id, p_rejected)` — 旧 reject/restore。reject 時は queued=false。

`p_type`: 'proposal'→improvement_proposals / 'opinion'→user_feedbacks。

### voice-dev サーバー

- 新規 `server/supabase_task_store.py`: Supabase バックエンドのタスクストア（`proposal_store` の役割を代替）。
  - 認証情報解決（secrets → プロジェクト .env → 既定）は共通ヘルパー化。
  - `load(app_path)` / `set_queued` / `mark_done` / `reject_task` / `restore_task` /
    `add_imported_task` / `add_ai_tasks` / `next_tasks` / `get_branch` / `set_branch` / `task_branch_name`。
  - タスク id は uuid（文字列）。各タスクに `type`（proposal/opinion）を持たせ、更新時にテーブルを判別。
- アプリレジストリ `~/.voice-dev/app_config.json`（リポジトリ外）: `{app_name: {app_path, branch}}`。
  - branch はタスクではなくアプリ設定のためここに移管（テキストファイルのタスク管理廃止と両立）。
  - autodev の横断列挙（どのアプリの Supabase を見るか）もこのレジストリを使う。
- `server/main.py`: 提案系エンドポイントを `supabase_task_store` に差し替え。
  - toggle/reject/restore は payload に `type` を追加で受け取る。
  - import 系は `dev_task_*` を Supabase に書き込む（MD 追加を廃止）。
  - `_run_propose` は AI タスクを `add_ai_tasks` で Supabase に INSERT。
- `server/autodev.py`: `next_tasks` / `mark_done` / `set_checked` / `get_branch` を store 経由に。
  MD の commit/push（`_file_for`）を廃止（autodev-log は履歴として存続可）。

### クライアント（client/index.html）

- タスク id が uuid 文字列になるため onclick 等を引用符付きに（`toggleProposal('${t.id}', ...)`）。
- toggle/reject/restore/run に `type` を同送。

## 廃止・存続

- 廃止: `proposals/*.md`（タスク台帳）, `.imported_ids.json`, `~/.voice-dev/imported_user_proposals.json`
  （取込済み判定は Supabase の `import_status` に一本化）。
- 存続: `proposals/autodev-log.md`（実行履歴ログ。タスク台帳ではない）。
- `server/proposal_store.py`: パース関数（`extract_block` / `parse_generated`）は純粋関数なので存続・再利用。
  ファイル I/O のタスク管理関数は未使用化。

## 適用手順（重要）

1. gh_portal の migration を Supabase に適用（`supabase db push` 等）。**適用しないと voice-dev 側は動作しない。**
2. voice-dev を再起動。

## 実装ステータス（2026-11-13 実装）

- [x] gh_portal migration（列追加 + RPC）: `supabase/migrations/20261113000001_dev_task_columns.sql`
      → **Supabase に適用済み（2026-11-13, `supabase db push`）**。本番で読取検証済み
      （dev_* 列7種を確認、`load()` で既存の取込済み提案 34件がタスクとして取得できることを確認）。
- [x] gh_portal の開発ブランチ `stu-ui` を `~/.voice-dev/app_config.json` に移行（旧MD frontmatterから）。
- [x] server/supabase_task_store.py（Supabase バックエンドのタスクストア）
- [x] server/main.py 差し替え（proposals 系 API + import + propose を Supabase 化）
- [x] server/autodev.py 差し替え（next_tasks / mark_done / set_checked / get_branch / run_now）
- [x] client/index.html（id 文字列化 + type 同送 + 短縮id表示 + 🤖/👤 タグ表示）

### 検証

- `supabase_task_store` のネットワーク非依存ロジックを `_rpc` モックで単体検証（15項目 PASS）:
  行→タスク変換 / タスク判定フィルタ / ブランチ名 / app_config roundtrip /
  各書き込みRPCペイロード / add_ai_tasks の重複スキップ / next_tasks の queued&!done&!rejected 抽出。
- サーバー3ファイル py_compile OK。

### 未対応・申し送り

- **migration 適用が前提**（上記）。適用後に提案画面で動作確認が必要。
- 既存 `proposals/*.md` の過去タスクは Supabase へ自動移行しない（履歴として残置）。
  取込済み判定は今後 Supabase の `import_status` に一本化。
- 音声の「#3 を並列実行」指定（`parse_parallel_request`）は id が uuid になったため実質無効化。
  必要なら別途 UI 側の短縮id指定に対応する。
