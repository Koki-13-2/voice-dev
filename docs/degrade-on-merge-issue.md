# autodev マージ時デグレ問題（2026-11-13 発覚）

## 症状

voice-dev の autodev または手動で task/ ブランチを切って開発し、stu-ui / main へマージすると
**既存機能が消える（デグレ）** が繰り返し発生している。

確認済みのデグレ事例（gh_portal）:
- `Header.tsx` の `AnnouncementSheet`（ベルアイコン）が消えた
- `Header.tsx` の `Icon` import が消えた
- マージ後に `ee929ed` で「修正」と称してさらに削除が進んだ

---

## 根本原因

### 1. 共有ファイルへの並列変更 → マージ競合の誤解決

`max_parallel_agents=3` で複数タスクが同時に動き、それぞれが `Header.tsx` / `App.tsx` などの
**共有ファイルを独立して編集してマージ**すると、後からマージするタスクが先行マージの変更を上書きする。

具体的に発生した流れ（`11cc015` マージコミット）:

```
common ancestor の Header.tsx
    ↓ main 側で追加
    AnnouncementSheet, Icon import を追加
    ↓ stu-ui 側（task/#254 worktree）で追加
    MeetingNotificationIcon import を追加
    ↓ stu-ui → main マージ時に三方向マージが競合を解決
    MeetingNotificationIcon のみ残り、AnnouncementSheet + Icon が消えた ← デグレ
```

git diff (--cc) の証拠:
```
- import { Icon } from './Icon'
- import { AnnouncementSheet } from './AnnouncementSheet'
+ import { MeetingNotificationIcon } from './MeetingNotificationIcon'
```

### 2. `_integrate_branch` がマージ後の正当性を検証しない

`autodev.py` の `_integrate_branch` は `git merge` の終了ステータスが
`"merged"` か `"conflict"` かだけを確認する。

**コンフリクトなしで不正な状態**（片方の変更が静かに消えた）を検出できない。

```python
# 現状：コンフリクトなしでマージ成功 = 正常とみなして push
result = await asyncio.to_thread(gitutil.merge_branch, app_path, branch, integration)
if result == "merged":
    push_result = await asyncio.to_thread(gitutil.push, app_path)
    _log(..., f"🔀 統合完了")  # ← デグレしていても成功ログが出る
```

### 3. タスクブランチが古いベースから切られる

タスクが並列実行される場合、後から起動したタスクの worktree が
「先行タスクのマージ前」の状態から分岐する。
その結果、先行タスクの追加コードを知らない状態でファイルを編集・マージする。

---

## 影響を受けやすいファイル

以下のファイルは複数タスクが同時に触れるリスクが高く、デグレの温床になる：

| ファイル | 理由 |
|---|---|
| `src/components/Header.tsx` | 新機能追加のたびにアイコンを追加する |
| `src/App.tsx` | ルート追加のたびに変更される |
| `src/styles/globals.css` | UI改修のたびにクラスが追加される |
| `supabase/migrations/` | DB変更のたびにファイルが追加される（競合は起きにくいが注意） |

---

## 対策（推奨）

### A. `_integrate_branch` に TypeScript 型チェックを追加（最優先）

マージ直後に `tsc --noEmit` を実行し、エラーがあれば自動マージを取り消して「要確認」ログに残す。
import が消えると必ず型エラーが発生するため、高い検出率が期待できる。

```python
# _integrate_branch 内 "merged" ブランチに追加
proc = await asyncio.create_subprocess_exec(
    "./node_modules/.bin/tsc", "--noEmit",
    cwd=app_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
)
stdout, _ = await proc.communicate()
if proc.returncode != 0:
    # マージを取り消して人間に判断を委ねる
    await asyncio.to_thread(gitutil.run_git, app_path, ["reset", "--merge"])
    _log(app_name, task,
         f"⚠ マージ後 tsc エラー（マージ取消し・手動確認が必要）: {branch} → {integration}",
         stdout.decode(errors="replace")[-1000:])
    return
```

### B. 共有ファイルへの並列変更ガード

`_launch_up_to_limit` でタスク起動前に「実行中タスクと同じファイルを変更しないか」をチェックする。
特に Header.tsx / App.tsx を触るタスクは逐次実行に限定する。

### C. Header.tsx のプラグイン化（恒久策）

`Header.tsx` が直接各コンポーネントを import している限り競合が起き続ける。
各機能が `headerExtensions.ts` に登録し、`Header.tsx` 本体は変更しない設計にする。

```ts
// src/components/headerExtensions.ts
export const HEADER_ICONS: HeaderIconDef[] = [
  { key: 'meeting-notif', component: MeetingNotificationIcon, roles: ['teacher'] },
  { key: 'announcements', component: AnnouncementBell, roles: ['all'] },
]
```

---

## 優先度

| 優先 | 対策 | 効果 | 工数 |
|---|---|---|---|
| ★★★ | A. tsc 後検証を `_integrate_branch` に追加 | デグレを自動検知してマージ中止 | 小（autodev.py 数行） |
| ★★☆ | B. 共有ファイルの並列実行ガード | 並列マージ競合を予防 | 小 |
| ★☆☆ | C. Header プラグイン化 | 構造的に競合しなくなる | 中 |

---

## 実装方針（2026-11-13 着手）

### 変更スコープ

本 voice-dev リポジトリに閉じる **対策A・B** を実装する。対策C は別リポジトリ
（gh_portal アプリ）の `Header.tsx` 構造変更のため、本リポジトリの範囲外とし別タスクに回す。

- `server/gitutil.py`
  - `undo_merge(repo_path)` を追加。`--no-ff` マージ直後に `git reset --hard ORIG_HEAD`
    で統合先をマージ前へ戻す（A のマージ取消し用）。
- `server/autodev.py`
  - **対策A**: `_post_merge_typecheck(app_path)` を追加し、`_integrate_branch` の
    `"merged"` 分岐でマージ直後に `node_modules/.bin/tsc --noEmit` を実行。
    エラーがあれば `gitutil.undo_merge` でマージを取り消し、worktree・ブランチは
    保持したまま「要確認」ログに記録して push しない。
    `node_modules/.bin/tsc` が無い（非TS構成）場合はスキップ。
  - **対策B**: 同一アプリのタスクを並列実行しないガードを `_launch_up_to_limit` と
    `run_now` に追加。共有ファイル（Header.tsx / App.tsx 等）はアプリ内でしか
    競合しないため、アプリ単位で逐次化すれば並列マージ競合を根本的に防げる。
    アプリをまたいだ並列は従来どおり維持。`serialize_per_app`（既定 true）で切替可能。

## 実装済み（2026-11-13 完了）

### 対策A: マージ後 tsc 検証 ✅

- `server/gitutil.py` に `undo_merge(repo_path)` を追加
  （`git reset --hard ORIG_HEAD` で `--no-ff` マージ直後の状態をマージ前へ戻す）。
- `server/autodev.py` に `_post_merge_typecheck(app_path)` を追加。
  `node_modules/.bin/tsc --noEmit`（最大5分 `TYPECHECK_TIMEOUT_SEC`）を実行し、
  型エラー出力を返す。`tsc` が無い非TS構成は `None`（スキップ）。
- `_integrate_branch` の `"merged"` 分岐でマージ直後に検証し、エラー時は
  `gitutil.undo_merge` でマージを取り消し、worktree・ブランチを保持したまま
  「⚠ マージ後 tsc エラー（マージ取消し・手動確認が必要）」としてログに記録。
  push はしない。
- 検証: 一時リポジトリで (1) マージ→undo でマージ前HEAD/作業ツリーへ復元、
  (2) 失敗する擬似 tsc でエラー出力を検知、(3) tsc 不在時は None スキップ、を確認。

### 対策B: 同一アプリ逐次化ガード ✅

- `server/autodev.py` の `DEFAULT_CONFIG` に `serialize_per_app: True` を追加。
  `_launch_up_to_limit` / `run_now` で実行中・起動予定のアプリ集合（`busy_apps`）を
  追跡し、同一アプリの2件目以降は先行タスクの完了（マージまで含む）まで起動しない。
  `run_now` では skip 理由「同一アプリ実行中（逐次化）」を返す。
- `server/main.py` の `POST /api/autodev` で `serialize_per_app` を受け取れるようにした。
- 先行タスクは `_integrate_branch`（マージ）完了まで `running_tasks` に残るため、
  次タスクのworktreeはマージ後の統合先から分岐し、根本原因#3（古いベースからの分岐）も緩和。

### 対策C: Header プラグイン化 — 未実装（別リポジトリ）

gh_portal アプリ側の `Header.tsx` 構造変更であり、本 voice-dev リポジトリの範囲外。
A のマージ後検証でデグレは自動検知できるようになったため、Cは恒久策として別タスクに委ねる。
