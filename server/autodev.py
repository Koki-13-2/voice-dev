"""自動開発スケジューラ — チェック済み提案を interval_min おきに1タスクずつ実行する"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import proposal_store
import secrets_store

CONFIG_FILE = Path.home() / ".voice-dev" / "autodev.json"
LOG_FILE = proposal_store.PROPOSALS_DIR / "autodev-log.md"

DEFAULT_CONFIG = {
    "enabled": False,
    "interval_min": 30,
    "model": "claude-sonnet-4-6",
    "last_run": "",
}

TASK_TIMEOUT_SEC = 25 * 60  # 30分間隔に収まるよう1タスク最大25分

# 実行中タスク情報（UI表示用）
current_task: dict | None = None


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
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg


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
    global current_task
    app_name = Path(app_path).name
    current_task = {"app": app_name, "id": task["id"], "title": task["title"],
                    "started": datetime.now().strftime("%H:%M")}

    prompt = (
        f"あなたはこのアプリ（{app_name}）の自動開発エージェントです。以下の改善タスクを1件だけ実装してください。\n\n"
        f"【タスク】【{task['angle']}】{task['title']}\n"
        f"【説明】{task.get('desc', '')}\n\n"
        "【ルール】\n"
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
        current_task = None


async def autodev_loop() -> None:
    """FastAPI startup から起動されるバックグラウンドループ"""
    print("[autodev] スケジューラ起動")
    while True:
        await asyncio.sleep(60)
        try:
            cfg = get_config()
            if not cfg["enabled"] or current_task is not None:
                continue
            last_run = cfg.get("last_run") or ""
            if last_run:
                elapsed = (datetime.now() - datetime.fromisoformat(last_run)).total_seconds()
                if elapsed < cfg["interval_min"] * 60:
                    continue
            nxt = proposal_store.next_task()
            if nxt is None:
                continue
            app_path, task = nxt
            set_config(last_run=datetime.now().isoformat(timespec="seconds"))
            print(f"[autodev] タスク実行: {Path(app_path).name} #{task['id']} {task['title']}")
            await _run_task(app_path, task, cfg["model"])
        except Exception as e:
            print(f"[autodev] ループエラー: {e}")


def status() -> dict:
    cfg = get_config()
    nxt = proposal_store.next_task()
    return {
        **cfg,
        "running": current_task,
        "next_task": {"app": Path(nxt[0]).name, **nxt[1]} if nxt else None,
        "log_path": str(LOG_FILE) if LOG_FILE.exists() else "",
    }
