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

---

## 全マージ経路のデグレ防止機構（2026-11-13 着手）

### 背景: 対策A/Bの穴

対策A/Bは **autodev の task→stu-ui 自動統合**しか守っていなかった。以下は無防備だった:

- UI「統合」ボタン（`/api/autodev/merge`、task→stu-ui）に検証が無い。
- **stu-ui→main 昇格**は voice-dev 外の手動 git で行われ、完全に無防備。
- 「stu-ui が main より古い状態での stu-ui→main」は、古いベースが main の変更を静かに捨てる
  典型的デグレ経路だが、どの経路でも検知されない。

### 設計: 共通プリミティブ `safe_merge`（全経路が必ず経由）

`server/merge_guard.py` に `safe_merge(app_path, source, target, *, level, push, bring_in_if_behind)`:

1. **最新化強制（静かなドロップの構造的根絶）**:
   `target` が `source` の祖先でなければ（source が target より遅れている）、
   先に **target を source に取り込み**（`merge target→source`）、検証を通してから
   `source→target` を行う。こうすると最終マージは fast-forward 相当になり、
   target の変更が 3-way マージで静かに捨てられることが構造的に起こり得なくなる。
   - task→stu-ui は `bring_in_if_behind=False`（worktree都合）。stu-ui が進んでいたら
     `stale` として保留（＝ドロップし得るマージは実行しない）。逐次化(B)により通常は発生しない。
   - stu-ui→main は `bring_in_if_behind=True`（main を stu-ui に取り込んでから昇格）。
2. `source→target` をマージ。
3. **検証** `verify(app_path, level)`:
   - `build`（既定）= `npm run build`（= `tsc && vite build`、型+バンドル）。gh_portal は
     `tsconfig.noEmit=true` で `tsc` は出力せず型検査のみ、`dist/` は gitignore 済みのため
     作業ツリーを汚さない。
   - `tsc` = `node_modules/.bin/tsc --noEmit`。`off` = スキップ。対象構成でなければ skip。
4. **失敗時**: `gitutil.undo_merge`（`reset --hard ORIG_HEAD`）で巻き戻し、ブランチは保持、
   `push` しない。取り込み(1)の検証失敗時はその取り込みを巻き戻す（stu-ui を汚さない）。
5. **成功時のみ push**（bring_in した場合は source ブランチも push）。

検証レベルは常に `build` を既定とする（複数 task を stu-ui 経由で main にまとめる際も、
各マージで型+バンドルを通すことで「全 task の変更が壊れない」ことを担保するため。
`tsc` のみでは bundler 固有エラーを見逃す可能性があり安全を保証できない）。

### カバー範囲（全経路 + CLI）

| 経路 | 実装 |
|---|---|
| autodev task→stu-ui 自動統合 | `_integrate_branch` → `safe_merge`（bring_in=False, level=cfg） |
| UI「統合」ボタン task→stu-ui | `/api/autodev/merge` → `safe_merge`（同上） |
| **stu-ui→main 昇格（新）** | `/api/autodev/promote` + UIボタン → `safe_merge`（bring_in=True, level=build） |
| **CLI 手動マージ（voice-dev外）** | gh_portal に `pre-push` git hook を導入し `npm run build` を強制（失敗で push 拒否） |

### 設定

`server/autodev.py` の `DEFAULT_CONFIG` に `merge_verify`（既定 `"build"`、`"tsc"`/`"off"` 可）。
`POST /api/autodev` で変更可能。

### 正直な限界（「絶対」の範囲）

- 本機構がカバーするのは **voice-dev を介したマージ + CLI push（hook経由）**。
  `git push --no-verify` 等で hook を明示的に回避した場合は対象外。
- `build` が通っても検知できないデグレ（型・バンドル的に正しいが機能削除・CSS削除など）は
  テストが無い限り自動では捕捉できない。ただし **最新化強制により「他ブランチの変更を
  静かに捨てる」クラスのデグレは構造的に発生しなくなる**（これが本課題の主因）。
  残るのは「エージェント自身が意図せず機能を壊す」クラスで、これはテスト/レビューの領域。

### 実装ステータス（2026-11-13 完了）

- [x] `gitutil.is_ancestor`
- [x] `server/merge_guard.py`（verify + safe_merge）
- [x] `autodev.py`: `merge_verify` 設定（既定 build）+ `_integrate_branch` を `safe_merge` に（旧 `_post_merge_typecheck` 削除）
- [x] `main.py`: `/api/autodev/merge` を `safe_merge` に / `/api/autodev/promote` 新設 / 設定受け渡し
- [x] `client/index.html`: 「⬆ mainへ昇格」ボタン + `promoteToMain()`
- [x] gh_portal: `pre-push` hook 導入（`scripts/git-hooks/pre-push`、`.git/hooks/` に設置済み）

### 重要な実装上の発見: npm は WSL 上で使えない

`npm` は WSL の PATH 上で Windows 版（`/mnt/c/Program Files/nodejs/npm`）に解決され、
CMD.EXE を起動して WSL パス（`\\wsl.localhost\...`）を扱えず失敗する。
そのため検証は `npm run build` ではなく **`node_modules/.bin/tsc --noEmit` → `node_modules/.bin/vite build`**
をローカルバイナリとして直接実行する（Linux の node shebang で動作、`"build": "tsc && vite build"` と等価）。
merge_guard・pre-push hook の両方でこの方式を採用。

### 検証結果

- `safe_merge` のコア不変条件を一時 git repo で12項目 PASS:
  - **「mainより古い stu-ui を main へ昇格しても main の変更が落ちない／履歴消失なし」**（最新化強制の効果）
  - 検証失敗で main・source とも自動巻き戻し（verify_failed）
  - 統合先が進行中の task→stu-ui は stale で保留（ドロップし得るマージを実行しない）
  - 最新 task→stu-ui は正常統合
- gh_portal で `verify("build")`（tsc+vite build, 約5〜7秒）が実際に緑になることを確認。
- pre-push hook 設置・構文チェック済み。gh_portal の main への push で実際に発火し正常 push を阻害しないことを確認。

### 申し送り

- サーバー再起動で反映（`merge_verify` 既定 build、`/api/autodev/promote` 有効化）。
- 検証が重い/遅い場合は `POST /api/autodev` で `merge_verify="tsc"` に下げられる（昇格は安全優先で常に build）。
- `git push --no-verify` で hook を明示回避した場合、および型/バンドル的に正しい機能削除は
  自動検知対象外（テスト導入が恒久的な補完策）。
