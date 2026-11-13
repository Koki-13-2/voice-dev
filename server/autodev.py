"""自動開発スケジューラ — チェック済み提案をworktree分離で並列実行する"""
import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path

import gitutil
import proposal_store  # autodev-log（PROPOSALS_DIR）用。タスク台帳は supabase_task_store が正
import secrets_store
import supabase_task_store as task_store

CONFIG_FILE = Path.home() / ".voice-dev" / "autodev.json"
LOG_FILE = proposal_store.PROPOSALS_DIR / "autodev-log.md"

DEFAULT_CONFIG = {
    "enabled": False,
    "interval_min": 30,
    "model": "claude-sonnet-4-6",
    "max_parallel_agents": 3,  # 同時に動かすAIエージェント数の上限
    "serialize_per_app": True,  # 同一アプリのタスクは逐次実行（共有ファイルの並列マージ競合を防ぐ・対策B）
    "last_run": "",
    "claim": None,  # 実行中タスクのクレーム {app, id, at} — プロセス跨ぎの多重実行防止
}

TASK_TIMEOUT_SEC = 25 * 60       # 1タスクの最大実行時間
CLAIM_TTL_SEC = 30 * 60          # クレームの有効期間（プロセス死亡時の自動解放）
TYPECHECK_TIMEOUT_SEC = 5 * 60   # マージ後 tsc --noEmit の最大実行時間（対策A）

# 実行中タスク情報（UI表示用）— 複数タスクの並行実行に対応
running_tasks: dict[str, dict] = {}  # key = "app#id"


def get_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cfg


def set_config(**kwargs) -> dict:
    cfg = get_config()
    for k in ("enabled", "interval_min", "model", "max_parallel_agents",
              "serialize_per_app", "last_run"):
        if k in kwargs and kwargs[k] is not None:
            cfg[k] = kwargs[k]
    if "claim" in kwargs:  # None を渡すとクレーム解除
        cfg["claim"] = kwargs["claim"]
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg


def _claim_active(cfg: dict) -> bool:
    """有効なクレーム（=他プロセスが実行中/直近実行）が存在するか"""
    claim = cfg.get("claim")
    if not claim:
        return False
    try:
        at = datetime.fromisoformat(claim["at"])
    except (KeyError, ValueError, TypeError):
        return False
    return (datetime.now() - at).total_seconds() < CLAIM_TTL_SEC


def _log(app_name: str, task: dict, status: str, detail: str = "") -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        LOG_FILE.write_text("# 自動開発 実行ログ\n\n", encoding="utf-8")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"## {now} — {app_name} #{task['id']} {task['title']}\n\n- 結果: {status}\n"
    if detail:
        detail = detail[-1500:]
        entry += f"\n```\n{detail}\n```\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


async def _run_task(app_path: str, task: dict, model: str) -> None:
    app_name = Path(app_path).name
    task_key = f"{app_name}#{task['id']}"
    branch = task_store.task_branch_name(app_name, task)
    running_tasks[task_key] = {"app": app_name, "id": task["id"], "title": task["title"],
                               "branch": branch,
                               "started": datetime.now().strftime("%H:%M")}

    # アプリ単位の branch: frontmatter は「統合先ブランチ」として扱う（方針B）
    integration = ""
    work_dir = app_path
    wt_id = f"task-{task['id']}"
    use_worktree = False
    if gitutil.is_git_repo(app_path):
        integration = task_store.get_branch(app_path) or gitutil.get_current_branch(app_path)
        wt_path, wt_status = await asyncio.to_thread(
            gitutil.create_worktree, app_path, branch, wt_id, integration)
        if wt_path:
            work_dir = wt_path
            use_worktree = True
            print(f"[autodev] worktree {wt_status}: {branch} -> {wt_path}")
        else:
            _log(app_name, task, f"⚠ worktree作成失敗（app直下で実行継続）: {wt_status}")

    # アイデア由来の要件定義書があれば、実装のインプットとして参照させる
    req_dir = Path(work_dir) / "requirements"
    req_hint = ""
    if req_dir.exists() and any(req_dir.rglob("*.md")):
        req_hint = (
            "- 着手前に requirements/ 配下の要件定義書を読み、"
            "アプリの目的・要件と整合する実装にすること\n"
        )
    branch_hint = (
        f"- 現在の作業ディレクトリは専用worktree（ブランチ: {branch}）である。"
        "git checkout / git switch でブランチを切り替えないこと\n"
        f"- git remote が設定されていれば `git push -u origin {branch}` も行うこと\n"
        if use_worktree else
        "- git remote が設定されていれば git push も行うこと\n"
    )

    prompt = (
        f"あなたはこのアプリ（{app_name}）の自動開発エージェントです。以下の改善タスクを1件だけ実装してください。\n\n"
        f"【タスク】【{task['angle']}】{task['title']}\n"
        f"【説明】{task.get('desc', '')}\n\n"
        "【ルール】\n"
        f"{req_hint}"
        "- このタスクのみに集中し、スコープを広げないこと\n"
        "- 既存機能を壊さないこと。可能ならテスト・動作確認を行うこと\n"
        "- 完了したら git add -A && git commit すること（コミットメッセージにタスク内容を含める）\n"
        f"{branch_hint}"
    )

    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env.update(secrets_store.load_env(app_name))

    proc = await asyncio.create_subprocess_exec(
        "claude", "-p", prompt,
        "--output-format", "text",
        "--model", model,
        "--add-dir", work_dir,
        "--dangerously-skip-permissions",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=work_dir,
        env=env,
        limit=8 * 1024 * 1024,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=TASK_TIMEOUT_SEC)
        output = stdout.decode(errors="replace")
        if proc.returncode == 0:
            try:
                task_store.mark_done(app_path, task["id"], task.get("type", "proposal"))
            except Exception as e:
                print(f"[autodev] mark_done 失敗（続行）: {e}")
            _log(app_name, task, "✅ 成功", output)
            if use_worktree:
                await _integrate_branch(app_path, task, branch, wt_id, integration)
        else:
            _log(app_name, task, f"⚠ 失敗 (exit={proc.returncode})", output)
    except asyncio.TimeoutError:
        proc.kill()
        _log(app_name, task, "⏱ タイムアウト（25分）")
    except Exception as e:
        _log(app_name, task, f"⚠ エラー: {e}")
    finally:
        running_tasks.pop(task_key, None)
        # タスク状態は Supabase が正。ここでは実行ログのみ保管（best-effort）
        await gitutil.commit_and_push(
            [str(LOG_FILE)],
            f"autodev: {app_name} #{task['id']} {task['title'][:40]} の実行記録",
        )


async def _post_merge_typecheck(app_path: str) -> str | None:
    """マージ後の統合先ワークツリーで tsc --noEmit を実行する（対策A）。
    import消失などのデグレは必ず型エラーになるため、コンフリクトなしで静かに壊れた
    マージを検出できる。戻り値: None=問題なし（またはTS構成でないためスキップ）、
    文字列=型エラー出力。
    """
    tsc = Path(app_path) / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        return None  # 非TypeScript構成 / 未インストール → チェック対象外
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            str(tsc), "--noEmit",
            cwd=app_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(
            proc.communicate(), timeout=TYPECHECK_TIMEOUT_SEC)
        if proc.returncode == 0:
            return None
        return stdout.decode(errors="replace")
    except asyncio.TimeoutError:
        if proc:
            proc.kill()
        return "tsc タイムアウト（5分）"
    except Exception as e:
        return f"tsc 実行エラー: {e}"


async def _integrate_branch(app_path: str, task: dict, branch: str,
                            wt_id: str, integration: str) -> None:
    """完了したタスクブランチを統合先へマージする（方針D）。
    コンフリクト時はworktree・ブランチを保持したまま「要確認」として記録する。
    マージ後は tsc で正当性を検証し、型エラーがあればマージを取り消す（対策A）。
    """
    app_name = Path(app_path).name
    result = await asyncio.to_thread(gitutil.merge_branch, app_path, branch, integration)
    if result == "merged":
        # マージ後の型チェック。import消失等のデグレをコンフリクトなしでも検知する
        tsc_err = await _post_merge_typecheck(app_path)
        if tsc_err is not None:
            # マージを取り消し、worktree・ブランチは保持して人間の判断に委ねる
            undo = await asyncio.to_thread(gitutil.undo_merge, app_path)
            _log(app_name, task,
                 f"⚠ マージ後 tsc エラー（マージ取消し={undo}・手動確認が必要）: "
                 f"{branch} → {integration}。worktreeとブランチは保持",
                 tsc_err[-1200:])
            return
        await asyncio.to_thread(gitutil.remove_worktree, app_path, wt_id)
        push_result = await asyncio.to_thread(gitutil.push, app_path)
        _log(app_name, task, f"🔀 統合完了: {branch} → {integration}（{push_result}）")
    elif result == "conflict":
        _log(app_name, task,
             f"⚠ コンフリクト（要確認）: {branch} → {integration}。"
             "worktreeとブランチは保持。提案画面の「統合待ちブランチ」から解決後にマージしてください")
    else:
        _log(app_name, task, f"⚠ マージ失敗: {branch} → {integration}: {result}")


async def autodev_loop() -> None:
    """FastAPI startup から起動されるバックグラウンドループ"""
    print("[autodev] スケジューラ起動")
    while True:
        await asyncio.sleep(60)
        try:
            cfg = get_config()
            if not cfg["enabled"]:
                continue
            # プロセス跨ぎの多重ループ防止（uvicorn reload等でループが複数走った場合）
            if _claim_active(cfg):
                continue
            last_run = cfg.get("last_run") or ""
            if last_run:
                elapsed = (datetime.now() - datetime.fromisoformat(last_run)).total_seconds()
                if elapsed < cfg["interval_min"] * 60:
                    continue
            launched = _launch_up_to_limit(cfg)
            if launched:
                set_config(last_run=datetime.now().isoformat(timespec="seconds"))
        except Exception as e:
            print(f"[autodev] ループエラー: {e}")


def _launch_up_to_limit(cfg: dict) -> int:
    """空きスロット分だけ実行可能タスクをworktree並列で起動する。起動件数を返す"""
    max_parallel = int(cfg.get("max_parallel_agents") or 1)
    free = max_parallel - len(running_tasks)
    if free <= 0:
        return 0
    serialize_per_app = cfg.get("serialize_per_app", True)
    # 対策B: 同一アプリのタスクは共有ファイル（Header.tsx等）で並列マージ競合を
    # 起こすため逐次化する。実行中・本ループで起動予定のアプリ集合で判定する。
    busy_apps = {t["app"] for t in running_tasks.values()}
    candidates = task_store.next_tasks(limit=max_parallel + len(running_tasks))
    launched = 0
    for app_path, task in candidates:
        app_name = Path(app_path).name
        task_key = f"{app_name}#{task['id']}"
        if task_key in running_tasks:
            continue
        if serialize_per_app and app_name in busy_apps:
            continue  # 同一アプリの先行タスク完了（マージ）まで待つ
        if launched >= free:
            break
        print(f"[autodev] タスク実行: {app_name} #{task['id']} {task['title']}")
        asyncio.create_task(_run_task(app_path, task, cfg["model"]))
        busy_apps.add(app_name)
        launched += 1
    return launched


def run_now(app_path: str, task_ids: list[str], model: str | None = None) -> dict:
    """指定タスクを即時並列起動する（方針E: チャット/UIからの並列タスク指示）"""
    cfg = get_config()
    model = model or cfg["model"]
    max_parallel = int(cfg.get("max_parallel_agents") or 1)
    serialize_per_app = cfg.get("serialize_per_app", True)
    app_name = Path(app_path).name
    tasks = {str(t["id"]): t for t in task_store.load(app_path)["tasks"]}

    launched: list[dict] = []
    skipped: list[dict] = []
    slots_used = len(running_tasks)
    # 対策B: 同一アプリは逐次化。実行中 + 本呼び出しで起動したアプリを追跡する
    busy_apps = {t["app"] for t in running_tasks.values()}
    for tid in task_ids:
        tid = str(tid)
        t = tasks.get(tid)
        if t is None:
            skipped.append({"id": tid, "reason": "見つかりません"})
            continue
        if t["done"]:
            skipped.append({"id": tid, "reason": "実装済み"})
            continue
        if t["rejected"]:
            skipped.append({"id": tid, "reason": "不採用"})
            continue
        if f"{app_name}#{tid}" in running_tasks:
            skipped.append({"id": tid, "reason": "実行中"})
            continue
        if serialize_per_app and app_name in busy_apps:
            skipped.append({"id": tid, "reason": "同一アプリ実行中（逐次化）"})
            continue
        if slots_used >= max_parallel:
            skipped.append({"id": tid, "reason": f"並列上限({max_parallel})超過"})
            continue
        try:
            task_store.set_checked(app_path, tid, True, t.get("type", "proposal"))
        except Exception as e:
            skipped.append({"id": tid, "reason": f"キュー投入失敗: {e}"})
            continue
        asyncio.create_task(_run_task(app_path, t, model))
        launched.append({"id": tid, "title": t["title"]})
        busy_apps.add(app_name)
        slots_used += 1
    return {"launched": launched, "skipped": skipped}


_PARALLEL_KEYWORD_RE = re.compile(r"並列|同時|まとめて実行|parallel", re.IGNORECASE)
_TASK_ID_RE = re.compile(r"#(\d+)|(\d+)\s*番")


def parse_parallel_request(text: str) -> list[int]:
    """「#3 と #5 を並列実行」のような発話からタスクIDを抽出する。
    並列指示でなければ空リストを返す。
    """
    if not _PARALLEL_KEYWORD_RE.search(text or ""):
        return []
    ids: list[int] = []
    for m in _TASK_ID_RE.finditer(text):
        tid = int(m.group(1) or m.group(2))
        if tid not in ids:
            ids.append(tid)
    return ids


def status() -> dict:
    cfg = get_config()
    nxt = task_store.next_tasks(limit=3)
    tasks_list = list(running_tasks.values())
    return {
        **cfg,
        "running": tasks_list[0] if len(tasks_list) == 1 else None,
        "running_tasks": tasks_list,
        "next_task": {"app": Path(nxt[0][0]).name, **nxt[0][1]} if nxt else None,
        "next_tasks": [{"app": Path(p).name, **t} for p, t in nxt],
        "log_path": str(LOG_FILE) if LOG_FILE.exists() else "",
    }
