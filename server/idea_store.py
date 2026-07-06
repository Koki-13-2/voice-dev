"""アイデアDB — ideas/ 配下のMDファイルをフロントマター付きで管理する"""
import re
from datetime import datetime
from pathlib import Path

IDEAS_DIR = Path(__file__).parent.parent / "ideas"

# 出力契約マーカー（プロンプトで義務付け、抽出はこれを最優先）
IDEA_START = "<<<IDEA_START>>>"
IDEA_END = "<<<IDEA_END>>>"

_OUTER_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*\n(.*)\n```\s*$", re.S)


def _strip_outer_fence(text: str) -> str:
    """出力全体がコードフェンスで包まれている場合に剥がす"""
    m = _OUTER_FENCE_RE.match(text.strip())
    return m.group(1).strip() if m else text.strip()


def extract_document(raw: str) -> tuple[str, str] | None:
    """AI生出力から要件定義書本体を抽出する。
    戻り値: (本文, 抽出方法) / 抽出不能なら None

    1. sentinel マーカー区間（最優先・確実）
    2. フェンス除去後、最初の `# ` 見出し以降（フォールバック）
    """
    text = (raw or "").strip()
    if not text:
        return None

    if IDEA_START in text and IDEA_END in text:
        seg = text.split(IDEA_START, 1)[1].split(IDEA_END, 1)[0]
        seg = _strip_outer_fence(seg)
        if seg.strip():
            return seg.strip(), "sentinel"

    text = _strip_outer_fence(text)
    m = re.search(r"^#\s+\S.*$", text, re.MULTILINE)
    if m:
        return text[m.start():].strip(), "heading"
    return None


def validate_document(content: str) -> bool:
    """要件定義書として最低限の構造を持つか（タイトル + セクション3つ以上）"""
    has_title = bool(re.match(r"^#\s+\S", content))
    section_count = len(re.findall(r"^##\s+\S", content, re.MULTILINE))
    return has_title and section_count >= 3


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """フロントマターと本文に分離する"""
    meta: dict = {}
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            for line in text[4:end].splitlines():
                if ":" not in line:
                    continue
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
            body = text[end + 5:]
    return meta, body


def _serialize(meta: dict, body: str) -> str:
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.lstrip("\n")


def _idea_file(idea_id: str) -> Path:
    return IDEAS_DIR / f"{idea_id}.md"


def _to_dict(idea_id: str, meta: dict) -> dict:
    return {
        "id": idea_id,
        "title": meta.get("title", "(無題)"),
        "status": meta.get("status", "未着手"),
        "starred": meta.get("starred", "false") == "true",
        "created": meta.get("created", ""),
        "app_dir": meta.get("app_dir", ""),
        "path": str(_idea_file(idea_id)),
    }


def list_ideas() -> list[dict]:
    if not IDEAS_DIR.exists():
        return []
    ideas = []
    for md in IDEAS_DIR.glob("*.md"):
        meta, _ = _parse_frontmatter(md.read_text(encoding="utf-8"))
        ideas.append(_to_dict(md.stem, meta))
    # 新しい順
    ideas.sort(key=lambda x: x["id"], reverse=True)
    return ideas


def save_idea(content: str, raw_request: str) -> dict:
    """AI生成した要件定義書を保存する。タイトルは先頭の # 見出しから抽出"""
    IDEAS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    idea_id = now.strftime("%Y%m%d-%H%M%S")

    m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = m.group(1).strip() if m else raw_request[:30]

    if "元のアイデア" not in content:
        content = content.rstrip() + f"\n\n## 元のアイデア（原文）\n\n> {raw_request}\n"

    meta = {
        "id": idea_id,
        "title": title,
        "status": "未着手",
        "starred": "false",
        "created": now.strftime("%Y-%m-%d %H:%M"),
        "app_dir": "",
    }
    _idea_file(idea_id).write_text(_serialize(meta, content), encoding="utf-8")
    return _to_dict(idea_id, meta)


def get_idea(idea_id: str) -> tuple[dict, str] | None:
    f = _idea_file(idea_id)
    if not f.exists():
        return None
    meta, body = _parse_frontmatter(f.read_text(encoding="utf-8"))
    return _to_dict(idea_id, meta), body


def update_meta(idea_id: str, **kwargs) -> dict | None:
    f = _idea_file(idea_id)
    if not f.exists():
        return None
    meta, body = _parse_frontmatter(f.read_text(encoding="utf-8"))
    for k, v in kwargs.items():
        if isinstance(v, bool):
            v = "true" if v else "false"
        meta[k] = str(v)
    f.write_text(_serialize(meta, body), encoding="utf-8")
    return _to_dict(idea_id, meta)


def delete_idea(idea_id: str) -> bool:
    f = _idea_file(idea_id)
    if not f.exists():
        return False
    f.unlink()
    return True


def dir_name_for(idea_id: str, title: str) -> str:
    """アプリディレクトリ名を生成（ASCII安全な名前に）"""
    ascii_part = re.sub(r"[^a-zA-Z0-9\- ]", "", title).strip().replace(" ", "-").lower()
    ascii_part = re.sub(r"-+", "-", ascii_part).strip("-")
    if len(ascii_part) >= 3:
        return ascii_part
    return f"app-{idea_id}"
