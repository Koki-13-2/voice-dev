"""Supabase バックエンドの提案タスクストア。

proposals/*.md（テキストファイル）に代わり、対象アプリ各自の Supabase を
タスク台帳の「正」とする。improvement_proposals / user_feedbacks に追加した
dev_task_* 列を SECURITY DEFINER RPC 経由で読み書きする。

タスク判定:
  - proposal（improvement_proposals）: import_status='imported' または dev_source='ai'
  - opinion（user_feedbacks）: import_status='imported'

各タスクは `type`（'proposal' | 'opinion'）を持ち、更新時に対象テーブルを判別する。
branch はタスクではなくアプリ設定のため ~/.voice-dev/app_config.json に保持し、
同ファイルを autodev の横断アプリレジストリとして兼用する。
"""
import json
import urllib.request
import urllib.error
from pathlib import Path

import secrets_store

APP_CONFIG_FILE = Path.home() / ".voice-dev" / "app_config.json"
DEFAULT_SUPABASE_URL = "https://drmoefhhovpzmuzdqhax.supabase.co"


# ---------------- 認証情報 / アプリレジストリ ----------------

def _creds(app_path: str) -> tuple[str, str]:
    """(supabase_url, api_key) を返す。api_key が空なら credentials 未検出。
    解決順: voice-dev シークレット → プロジェクト .env.local/.env → 既定 URL。
    """
    app_name = Path(app_path).name if app_path else "gh_portal"
    env = secrets_store.load_env(app_name)
    url = env.get("SUPABASE_URL", "") or env.get("VITE_SUPABASE_URL", "")
    key = (env.get("SUPABASE_SERVICE_ROLE_KEY", "")
           or env.get("SUPABASE_ANON_KEY", "")
           or env.get("VITE_SUPABASE_ANON_KEY", ""))
    if not key and app_path:
        for fname in (".env.local", ".env"):
            f = Path(app_path) / fname
            if not f.exists():
                continue
            proj: dict[str, str] = {}
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                proj[k.strip()] = v.strip().strip('"').strip("'")
            url = url or proj.get("VITE_SUPABASE_URL", "") or proj.get("SUPABASE_URL", "")
            key = (proj.get("SUPABASE_SERVICE_ROLE_KEY", "")
                   or proj.get("SUPABASE_ANON_KEY", "")
                   or proj.get("VITE_SUPABASE_ANON_KEY", ""))
            if key:
                break
    return (url or DEFAULT_SUPABASE_URL), key


def _rpc(app_path: str, fn: str, payload: dict | None = None) -> list | dict | None:
    """Supabase RPC を呼ぶ。失敗時は RuntimeError。204/空応答は None。"""
    url, key = _creds(app_path)
    if not key:
        raise RuntimeError(
            "Supabase キーが見つかりません。シークレットタブから SUPABASE_ANON_KEY を"
            "登録するか、プロジェクトの .env.local に VITE_SUPABASE_ANON_KEY を設定してください。")
    req = urllib.request.Request(
        f"{url}/rest/v1/rpc/{fn}",
        method="POST",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload or {}).encode("utf-8"),
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"Supabase RPC {fn} HTTP {e.code}: {detail[:300]}")
    except Exception as e:
        raise RuntimeError(f"Supabase RPC {fn} 失敗: {e}")


def _load_app_config() -> dict:
    if not APP_CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(APP_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_app_config(cfg: dict) -> None:
    APP_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    APP_CONFIG_FILE.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def register_app(app_path: str) -> None:
    """アプリを横断レジストリに登録（autodev の next_tasks 用）。"""
    if not app_path:
        return
    app_name = Path(app_path).name
    cfg = _load_app_config()
    entry = cfg.get(app_name, {})
    if entry.get("app_path") == app_path:
        return
    entry["app_path"] = app_path
    entry.setdefault("branch", "")
    cfg[app_name] = entry
    _save_app_config(cfg)


def get_branch(app_path: str) -> str:
    return _load_app_config().get(Path(app_path).name, {}).get("branch", "")


def set_branch(app_path: str, branch: str) -> bool:
    app_name = Path(app_path).name
    cfg = _load_app_config()
    entry = cfg.get(app_name, {"app_path": app_path})
    entry["app_path"] = app_path
    entry["branch"] = branch
    cfg[app_name] = entry
    _save_app_config(cfg)
    return True


# ---------------- 読み取り ----------------

def _row_to_task(row: dict, task_type: str) -> dict:
    content = (row.get("content") or "").strip()
    first = content.split("\n")[0] if content else ""
    title = (row.get("dev_task_title") or "").strip() or (
        (first[:57] + "…") if len(first) > 57 else first)
    return {
        "id": str(row.get("id", "")),
        "type": task_type,
        "angle": (row.get("dev_task_angle") or "").strip(),
        "title": title,
        "desc": (row.get("dev_task_desc") or "").strip() or content,
        "checked": bool(row.get("dev_task_queued")),
        "done": row.get("dev_task_done_at") or "",
        "rejected": row.get("dev_task_rejected_at") or "",
        "dev_source": row.get("dev_source") or "user",
        "created_at": row.get("created_at", ""),
    }


def _fetch_tasks(app_path: str) -> list[dict]:
    """アプリの全タスク（取込済み提案 + AI生成 + 取込済みご意見）を返す。"""
    tasks: list[dict] = []
    props = _rpc(app_path, "get_improvement_proposals_admin", {}) or []
    for row in props:
        if row.get("import_status") == "imported" or row.get("dev_source") == "ai":
            tasks.append(_row_to_task(row, "proposal"))
    opinions = _rpc(app_path, "get_user_feedbacks_admin", {}) or []
    for row in opinions:
        if row.get("import_status") == "imported":
            tasks.append(_row_to_task(row, "opinion"))
    return tasks


def load(app_path: str) -> dict:
    """提案画面用: {app, app_path, branch, tasks:[...]} を返す。"""
    app_name = Path(app_path).name
    register_app(app_path)
    try:
        tasks = _fetch_tasks(app_path)
    except RuntimeError:
        tasks = []
    return {"app": app_name, "app_path": app_path,
            "branch": get_branch(app_path), "tasks": tasks}


# ---------------- 更新 ----------------

def set_checked(app_path: str, task_id: str, checked: bool,
                task_type: str = "proposal") -> bool:
    _rpc(app_path, "set_dev_task_queued",
         {"p_type": task_type, "p_id": task_id, "p_queued": checked})
    return True


def mark_done(app_path: str, task_id: str, task_type: str = "proposal") -> bool:
    _rpc(app_path, "mark_dev_task_done", {"p_type": task_type, "p_id": task_id})
    return True


def reject_task(app_path: str, task_id: str, task_type: str = "proposal") -> bool:
    _rpc(app_path, "set_dev_task_rejected",
         {"p_type": task_type, "p_id": task_id, "p_rejected": True})
    return True


def restore_task(app_path: str, task_id: str, task_type: str = "proposal") -> bool:
    _rpc(app_path, "set_dev_task_rejected",
         {"p_type": task_type, "p_id": task_id, "p_rejected": False})
    return True


# ---------------- 取り込み / 追加 ----------------

def import_feedback_as_task(app_path: str, task_type: str, source_id: str,
                            angle: str, title: str, desc: str) -> bool:
    """未処理フィードバックをタスク化する（import_status='imported' + dev_task_*）。"""
    _rpc(app_path, "import_feedback_as_task", {
        "p_type": task_type, "p_id": source_id,
        "p_angle": angle, "p_title": title, "p_desc": desc,
    })
    return True


def add_ai_tasks(app_path: str, tasks: list[dict]) -> int:
    """AI生成提案を improvement_proposals に INSERT する。追加件数を返す。
    tasks: [{"angle","title","desc"(省略可)}]。タイトル重複は既存タスクと照合してスキップ。
    """
    register_app(app_path)
    try:
        existing = {t["title"] for t in _fetch_tasks(app_path)}
    except RuntimeError:
        existing = set()
    added = 0
    for t in tasks:
        title = (t.get("title") or "").strip()
        if not title or title in existing:
            continue
        angle = (t.get("angle") or "").strip()
        desc = (t.get("desc") or "").strip()
        content = f"【{angle}】{title}" + (f" — {desc}" if desc else "")
        _rpc(app_path, "insert_ai_dev_task", {
            "p_tab": "other", "p_angle": angle, "p_title": title,
            "p_desc": desc, "p_content": content,
        })
        existing.add(title)
        added += 1
    return added


# 後方互換エイリアス（既存呼び出し箇所が add_tasks を使うため）
def add_tasks(app_path: str, new_tasks: list[dict]) -> int:
    return add_ai_tasks(app_path, new_tasks)


# ---------------- autodev 用 ----------------

def task_branch_name(app_name: str, task: dict) -> str:
    """タスク専用ブランチ名: task/<app>/<短縮id>[-<slug>]。"""
    import re
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", task.get("title", "")).strip("-").lower()[:24].rstrip("-")
    short = str(task.get("id", ""))[:8]
    base = f"task/{app_name}/{short}"
    return f"{base}-{slug}" if slug else base


def next_tasks(limit: int = 1) -> list[tuple[str, dict]]:
    """登録済み全アプリの Supabase から「キュー投入済み・未完了・未不採用」の
    タスクを最大 limit 件返す [(app_path, task), ...]（並列スケジューラ用）。"""
    results: list[tuple[str, dict]] = []
    if limit <= 0:
        return results
    for app_name, entry in sorted(_load_app_config().items()):
        app_path = entry.get("app_path", "")
        if not app_path or not Path(app_path).exists():
            continue
        try:
            tasks = _fetch_tasks(app_path)
        except RuntimeError:
            continue
        for t in tasks:
            if t["checked"] and not t["done"] and not t["rejected"]:
                results.append((app_path, t))
                if len(results) >= limit:
                    return results
    return results


def next_task() -> tuple[str, dict] | None:
    found = next_tasks(1)
    return found[0] if found else None
