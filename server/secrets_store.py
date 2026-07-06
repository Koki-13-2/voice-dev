"""秘密情報ストア — ~/.voice-dev/secrets/<アプリ名>.env をパーミッション制限付きで管理する"""
import os
import re
from pathlib import Path

SECRETS_DIR = Path.home() / ".voice-dev" / "secrets"


def _safe_app_name(app_name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_\-.]", "_", app_name)
    if not name or name.startswith("."):
        raise ValueError("不正なアプリ名です")
    return name


def _env_file(app_name: str) -> Path:
    return SECRETS_DIR / f"{_safe_app_name(app_name)}.env"


def _ensure_dir() -> None:
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(SECRETS_DIR, 0o700)


def load_env(app_name: str) -> dict[str, str]:
    f = _env_file(app_name)
    if not f.exists():
        return {}
    env = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value
    return env


def _write_env(app_name: str, env: dict[str, str]) -> None:
    _ensure_dir()
    f = _env_file(app_name)
    content = "\n".join(f"{k}={v}" for k, v in env.items()) + ("\n" if env else "")
    f.write_text(content, encoding="utf-8")
    os.chmod(f, 0o600)


def list_keys(app_name: str) -> list[dict]:
    """値はマスクして返す（末尾4文字のみ表示）"""
    result = []
    for k, v in load_env(app_name).items():
        masked = ("*" * 8 + v[-4:]) if len(v) > 4 else "*" * 8
        result.append({"key": k, "preview": masked})
    return result


def set_key(app_name: str, key: str, value: str) -> None:
    key = key.strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        raise ValueError("キー名は英数字とアンダースコアのみ使用できます")
    if "\n" in value:
        raise ValueError("値に改行は使用できません")
    env = load_env(app_name)
    env[key] = value
    _write_env(app_name, env)


def delete_key(app_name: str, key: str) -> bool:
    env = load_env(app_name)
    if key not in env:
        return False
    del env[key]
    _write_env(app_name, env)
    return True
