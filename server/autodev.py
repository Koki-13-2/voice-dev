"""自動開発スケジューラ — チェック済み提案を interval_min おきに実行する（並行稼働対応）"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import gitutil
import proposal_store
import secrets_store

CONFIG_FILE = Path.home() / ".voice-dev" / "autodev.json"
LOG_FILE = proposal_store.PROPOSALS_DIR / "autodev-log.md"

DEFAULT_CONFIG = {
    "enabled": False,
    "interval_min": 30,
    "model": "claude-sonnet-4-6",
    "last_run": "",
    "claim": None,  # 実行中タスクのクレーム {app, id, at} — プロセス跨ぎの多重実行防止
}

TASK_TIMEOUT_SEC = 25 * 60  # 1タスクの最大実行時間
CLAIM_TTL_SEC = 30 * 60     # クレームの有効期間（プロセス死亡時の自動解放）

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
    for k in ("enabled", "interval_min", "model", "last_run"):
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
    running_tasks[task_key] = {"app": app_name, "id": task["id"], "title": task["title"],
                               "started": datetime.now().strftime("%H:%M")}

    # アイデア由来の要件定義書があれば、実装のインプットとして参照させる
    req_dir = Path(app_path) / "requirements"
    req_hint = ""
    if req_dir.exists() and any(req_dir.rglob("*.md")):
        req_hint = (
            "- 着手前に requirements/ 配下の要件定義書を読み、"
            "アプリの目的・要件と整合する実装にすること\n"
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
        "- git remote が設定されていれば git push も行うこと\n"
    )

    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env.update(secrets_store.load_env(app_name))

    proc = await asyncio.create_subprocess_exec(
        "claude", "-p", prompt,
        "--output-format", "text",
        "--model", model,
        "--add-dir", app_path,
        "--dangerously-skip-permissions",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=app_path,
        env=env,
        limit=8 * 1024 * 1024,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=TASK_TIMEOUT_SEC)
        output = stdout.decode(errors="replace")
        if proc.returncode == 0:
            proposal_store.mark_done(app_name, task["id"])
            _log(app_name, task, "✅ 成功", output)
        else:
            _log(app_name, task, f"⚠ 失敗 (exit={proc.returncode})", output)
    except asyncio.TimeoutError:
        proc.kill()
        _log(app_name, task, "⏱ タイムアウト（25分）")
    except Exception as e:
        _log(app_name, task, f"⚠ エラー: {e}")
    finally:
        running_tasks.pop(task_key, None)
        # 提案の完了状態と実行ログを確実に保管（best-effort）
        await gitutil.commit_and_push(
            [str(proposal_store._file_for(app_name)), str(LOG_FILE)],
            f"autodev: {app_name} #{task['id']} {task['title'][:40]} の実行記録",
        )


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
            nxt = proposal_store.next_task()
            if nxt is None:
                continue
            # 同じタスクが既に実行中ならスキップ
            app_path, task = nxt
            task_key = f"{Path(app_path).name}#{task['id']}"
            if task_key in running_tasks:
                continue
            now = datetime.now().isoformat(timespec="seconds")
            set_config(last_run=now)
            print(f"[autodev] タスク実行: {Path(app_path).name} #{task['id']} {task['title']}")
            asyncio.create_task(_run_task(app_path, task, cfg["model"]))
        except Exception as e:
            print(f"[autodev] ループエラー: {e}")


def status() -> dict:
    cfg = get_config()
    nxt = proposal_store.next_task()
    tasks_list = list(running_tasks.values())
    return {
        **cfg,
        "running": tasks_list[0] if len(tasks_list) == 1 else None,
        "running_tasks": tasks_list,
        "next_task": {"app": Path(nxt[0]).name, **nxt[1]} if nxt else None,
        "log_path": str(LOG_FILE) if LOG_FILE.exists() else "",
    }
