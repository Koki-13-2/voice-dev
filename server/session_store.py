"""セッションメタの永続化 — ~/.voice-dev/sessions.json（方針F）。

サーバー再起動後もセッション一覧・プロジェクト・Claude CLIの会話ID
（--resume 用の claude_session_id）を復元し、別画面から戻っても会話を継続できるようにする。
"""
import json
from pathlib import Path

SESSIONS_FILE = Path.home() / ".voice-dev" / "sessions.json"


def load_all() -> dict[str, dict]:
    if not SESSIONS_FILE.exists():
        return {}
    try:
        data = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_all(metas: dict[str, dict]) -> None:
    """失敗しても本処理は止めない（永続化は最善努力）"""
    try:
        SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSIONS_FILE.write_text(
            json.dumps(metas, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[セッション永続化失敗] {e}")
