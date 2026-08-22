"""Claude Codeアカウント管理ストア — 複数アカウントのログイン情報保存・切替・利用量集計。

~/.claude/.credentials.json（claude CLIが読むログイン情報ファイル）をアカウントごとに
~/.voice-dev/accounts/<name>/ にスナップショット保存し、切替時に書き戻す。

「残トークン」はAnthropic側が公開APIを提供していないため取得できない。ここでは
アプリ経由でclaude CLIを呼び出した際の使用量（result イベントのusage）を自己集計した
目安カウンターとして扱う。
"""
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

ACCOUNTS_DIR = Path.home() / ".voice-dev" / "accounts"
ACTIVE_MARKER = ACCOUNTS_DIR / "active.json"
CLAUDE_CREDENTIALS_FILE = Path.home() / ".claude" / ".credentials.json"

_USAGE_KEYS = (
    "input_tokens", "output_tokens",
    "cache_creation_input_tokens", "cache_read_input_tokens",
)


def _safe_name(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_\-.]", "_", (name or "").strip())
    if not name or name.startswith("."):
        raise ValueError("不正なアカウント名です")
    return name


def _account_dir(name: str) -> Path:
    return ACCOUNTS_DIR / _safe_name(name)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dir(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    d.chmod(0o700)


def _read_json(f: Path, default: dict) -> dict:
    if not f.exists():
        return dict(default)
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(default)


def _write_json(f: Path, data: dict) -> None:
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    f.chmod(0o600)


def _empty_usage() -> dict:
    return {
        "since": _now(), "calls": 0,
        "input_tokens": 0, "output_tokens": 0,
        "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
        "total_cost_usd": 0.0, "last_used_at": None,
    }


def _claude_auth_status() -> dict | None:
    """`claude auth status` の結果をパースして返す。失敗時はNone。"""
    try:
        proc = subprocess.run(
            ["claude", "auth", "status"],
            capture_output=True, text=True, timeout=20,
        )
        return json.loads(proc.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return None


def whoami() -> dict:
    status = _claude_auth_status()
    if status is None:
        return {"loggedIn": False}
    return status


def get_active_name() -> str | None:
    marker = _read_json(ACTIVE_MARKER, {})
    return marker.get("name")


def _set_active_name(name: str | None) -> None:
    _ensure_dir(ACCOUNTS_DIR)
    if name is None:
        _write_json(ACTIVE_MARKER, {})
    else:
        _write_json(ACTIVE_MARKER, {"name": name})


def _is_live_credentials_equal_to(name: str) -> bool:
    saved = _account_dir(name) / "credentials.json"
    if not saved.exists() or not CLAUDE_CREDENTIALS_FILE.exists():
        return False
    try:
        return saved.read_bytes() == CLAUDE_CREDENTIALS_FILE.read_bytes()
    except OSError:
        return False


def list_accounts() -> list[dict]:
    if not ACCOUNTS_DIR.exists():
        return []
    active_name = get_active_name()
    result = []
    for d in sorted(ACCOUNTS_DIR.iterdir()):
        if not d.is_dir():
            continue
        name = d.name
        meta = _read_json(d / "meta.json", {})
        usage = _read_json(d / "usage.json", _empty_usage())
        is_active = (name == active_name) and _is_live_credentials_equal_to(name)
        result.append({"name": name, "active": is_active, **meta, "usage": usage})
    return result


def save_current_as(name: str, label: str | None = None) -> dict:
    if not CLAUDE_CREDENTIALS_FILE.exists():
        raise ValueError("現在ログインしていません。ターミナルで `claude auth login` を実行してください")

    safe = _safe_name(name)
    d = ACCOUNTS_DIR / safe
    _ensure_dir(d)

    creds = CLAUDE_CREDENTIALS_FILE.read_bytes()
    (d / "credentials.json").write_bytes(creds)
    (d / "credentials.json").chmod(0o600)

    status = whoami()
    meta = {
        "label": (label or safe).strip() or safe,
        "email": status.get("email"),
        "org_name": status.get("orgName"),
        "subscription_type": status.get("subscriptionType"),
        "auth_method": status.get("authMethod"),
        "saved_at": _now(),
        "last_switched_at": _now(),
    }
    _write_json(d / "meta.json", meta)

    usage_file = d / "usage.json"
    if not usage_file.exists():
        _write_json(usage_file, _empty_usage())

    _set_active_name(safe)
    return {"name": safe, "active": True, **meta, "usage": _read_json(usage_file, _empty_usage())}


def switch_to(name: str) -> dict:
    safe = _safe_name(name)
    d = ACCOUNTS_DIR / safe
    creds_file = d / "credentials.json"
    if not creds_file.exists():
        raise ValueError(f"アカウント '{safe}' は保存されていません")

    # 切替前に、現在アクティブな既知アカウントのトークンが更新されている可能性があるので書き戻す
    current_active = get_active_name()
    if current_active and current_active != safe and CLAUDE_CREDENTIALS_FILE.exists():
        prev_dir = ACCOUNTS_DIR / current_active
        if prev_dir.exists():
            (prev_dir / "credentials.json").write_bytes(CLAUDE_CREDENTIALS_FILE.read_bytes())
            (prev_dir / "credentials.json").chmod(0o600)

    CLAUDE_CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_CREDENTIALS_FILE.write_bytes(creds_file.read_bytes())
    CLAUDE_CREDENTIALS_FILE.chmod(0o600)

    meta = _read_json(d / "meta.json", {})
    meta["last_switched_at"] = _now()
    _write_json(d / "meta.json", meta)
    _set_active_name(safe)

    status = whoami()
    usage = _read_json(d / "usage.json", _empty_usage())
    return {"name": safe, "active": True, **meta, "status": status, "usage": usage}


def delete_account(name: str) -> bool:
    safe = _safe_name(name)
    d = ACCOUNTS_DIR / safe
    if not d.exists():
        return False
    for f in d.iterdir():
        f.unlink()
    d.rmdir()
    if get_active_name() == safe:
        _set_active_name(None)
    return True


def record_usage(name: str | None, usage: dict, cost_usd: float | None = None) -> None:
    """claude CLI呼び出し1回分のusageを、指定アカウントの累計に加算する。"""
    if not name:
        return
    d = ACCOUNTS_DIR / _safe_name(name)
    if not d.exists():
        return
    usage_file = d / "usage.json"
    current = _read_json(usage_file, _empty_usage())
    for k in _USAGE_KEYS:
        current[k] = current.get(k, 0) + int(usage.get(k) or 0)
    if cost_usd:
        current["total_cost_usd"] = current.get("total_cost_usd", 0.0) + float(cost_usd)
    current["calls"] = current.get("calls", 0) + 1
    current["last_used_at"] = _now()
    _write_json(usage_file, current)


def reset_usage(name: str) -> dict:
    safe = _safe_name(name)
    d = ACCOUNTS_DIR / safe
    if not d.exists():
        raise ValueError(f"アカウント '{safe}' は保存されていません")
    fresh = _empty_usage()
    _write_json(d / "usage.json", fresh)
    return fresh
