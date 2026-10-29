"""gh_portal ユーザー投稿の改善提案を Supabase から取得・管理する。

認証情報は ~/.voice-dev/secrets/gh_portal.env に以下の形式で保存する:
  SUPABASE_URL=https://xxx.supabase.co
  SUPABASE_ANON_KEY=eyJ...
"""
import json
import urllib.request
import urllib.error
from pathlib import Path

SECRETS_DIR = Path.home() / ".voice-dev" / "secrets"
IMPORTED_FILE = Path.home() / ".voice-dev" / "imported_user_proposals.json"

TAB_LABEL: dict[str, str] = {
    "dashboard": "ダッシュボード",
    "chat": "チャット",
    "timeline": "タイムライン",
    "contents": "コンテンツ",
    "practice": "プラクティス",
    "other": "その他",
}


def _load_credentials() -> tuple[str, str]:
    f = SECRETS_DIR / "gh_portal.env"
    if not f.exists():
        return "", ""
    env: dict[str, str] = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env.get("SUPABASE_URL", ""), env.get("SUPABASE_ANON_KEY", "")


def _load_imported() -> set[str]:
    if not IMPORTED_FILE.exists():
        return set()
    try:
        return set(json.loads(IMPORTED_FILE.read_text(encoding="utf-8")))
    except Exception:
        return set()


def _save_imported(ids: set[str]) -> None:
    IMPORTED_FILE.parent.mkdir(parents=True, exist_ok=True)
    IMPORTED_FILE.write_text(
        json.dumps(sorted(ids), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_new_proposals() -> list[dict]:
    """Supabase から未取り込みのユーザー改善提案を返す。
    認証情報未設定なら空リストを返す（エラーにしない）。
    """
    url, key = _load_credentials()
    if not url or not key:
        return []

    try:
        rpc_url = f"{url}/rest/v1/rpc/get_improvement_proposals_admin"
        req = urllib.request.Request(
            rpc_url,
            method="POST",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            data=b"{}",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            rows: list[dict] = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Supabase HTTP {e.code}: {body}")
    except Exception as e:
        raise RuntimeError(str(e))

    imported = _load_imported()
    result: list[dict] = []
    for r in rows:
        rid = str(r.get("id", ""))
        if not rid or rid in imported:
            continue
        tab = r.get("tab", "other")
        result.append({
            "id": rid,
            "tab": tab,
            "tab_label": TAB_LABEL.get(tab, tab),
            "content": r.get("content", ""),
            "image_url": r.get("image_url") or "",
            "created_at": r.get("created_at", ""),
        })
    return result


def mark_imported(proposal_ids: list[str]) -> int:
    """指定 ID を取り込み済みとしてマークする。追加件数を返す。"""
    imported = _load_imported()
    before = len(imported)
    imported.update(proposal_ids)
    _save_imported(imported)
    return len(imported) - before
