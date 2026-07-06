"""改善提案ストア — proposals/<アプリ名>.md のチェックリストを管理する"""
import re
from datetime import datetime
from pathlib import Path

PROPOSALS_DIR = Path(__file__).parent.parent / "proposals"

# 例: - [x] 【機能/中】CSVエクスポート — 分析結果を保存 <!-- id:2 done:2026-07-06T16:00 -->
_TASK_RE = re.compile(
    r"^- \[(?P<check>[ x])\] 【(?P<angle>[^】]+)】(?P<title>[^—–\-ー\n]+?)"
    r"(?:\s*[—–\-ー]\s*(?P<desc>.*?))?\s*<!-- id:(?P<id>\d+)(?: done:(?P<done>[^ >]+))? -->\s*$"
)

_DASH_RE = r"[—–\-ー:：]"

# AI生成行: 番号付き・箇条書き・インデント付きすべて許容
# 例: - 【機能/中】タイトル — 説明
#      1. 【機能/中】タイトル — 説明
#      • 【機能/中】タイトル: 説明
_GEN_RE = re.compile(
    r"^(?:\d+[.)]\s*|[-*•·▸►]\s*|\s*)"
    r"【(?P<angle>[^】]+)】\s*"
    r"(?P<title>.+?)(?:\s*" + _DASH_RE + r"\s+(?P<desc>.+))?$"
)


def _file_for(app_name: str) -> Path:
    return PROPOSALS_DIR / f"{app_name}.md"


def _parse_file(f: Path) -> tuple[dict, list[dict], list[str]]:
    """(meta, tasks, 全行) を返す"""
    meta: dict = {}
    tasks: list[dict] = []
    lines = f.read_text(encoding="utf-8").splitlines()
    in_fm = False
    for i, line in enumerate(lines):
        if i == 0 and line == "---":
            in_fm = True
            continue
        if in_fm:
            if line == "---":
                in_fm = False
                continue
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
            continue
        m = _TASK_RE.match(line)
        if m:
            tasks.append({
                "id": int(m.group("id")),
                "angle": m.group("angle"),
                "title": m.group("title").strip(),
                "desc": (m.group("desc") or "").strip(),
                "checked": m.group("check") == "x",
                "done": m.group("done") or "",
                "line_no": i,
            })
    return meta, tasks, lines


def _task_line(task: dict) -> str:
    check = "x" if task["checked"] else " "
    done = f" done:{task['done']}" if task["done"] else ""
    desc = f" — {task['desc']}" if task["desc"] else ""
    return f"- [{check}] 【{task['angle']}】{task['title']}{desc} <!-- id:{task['id']}{done} -->"


def load(app_path: str) -> dict:
    app_name = Path(app_path).name
    f = _file_for(app_name)
    if not f.exists():
        return {"app": app_name, "app_path": app_path, "tasks": []}
    meta, tasks, _ = _parse_file(f)
    for t in tasks:
        t.pop("line_no", None)
    return {"app": app_name, "app_path": meta.get("app_path", app_path), "tasks": tasks}


_FALLBACK_RE = re.compile(r"【(?P<angle>[^】]+)】\s*(?P<rest>.+)")


def parse_generated(text: str) -> list[dict]:
    """AI出力から提案行を抽出する。正規表現マッチ → フォールバックの2段階。"""
    tasks = []
    unmatched_lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _TASK_RE.match(line)
        if m:
            tasks.append({"angle": m.group("angle"), "title": m.group("title").strip(),
                          "desc": (m.group("desc") or "").strip()})
            continue
        m = _GEN_RE.match(line)
        if m:
            tasks.append({"angle": m.group("angle"), "title": m.group("title").strip(),
                          "desc": (m.group("desc") or "").strip()})
            continue
        if "【" in line and "】" in line:
            unmatched_lines.append(line)

    if tasks:
        return tasks

    for line in unmatched_lines:
        m = _FALLBACK_RE.search(line)
        if m:
            rest = m.group("rest").strip()
            parts = re.split(r"\s*[—–\-ー:：]\s+", rest, maxsplit=1)
            title = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""
            if title:
                tasks.append({"angle": m.group("angle"), "title": title, "desc": desc})
    return tasks


def add_tasks(app_path: str, new_tasks: list[dict]) -> int:
    """新規提案を追記する（タイトル重複はスキップ）。追加件数を返す"""
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    app_name = Path(app_path).name
    f = _file_for(app_name)

    if not f.exists():
        f.write_text(
            f"---\napp: {app_name}\napp_path: {app_path}\n---\n\n"
            f"# {app_name} 改善提案\n\n",
            encoding="utf-8",
        )

    _, existing, lines = _parse_file(f)
    existing_titles = {t["title"] for t in existing}
    next_id = max([t["id"] for t in existing], default=0) + 1

    added = 0
    for t in new_tasks:
        if t["title"] in existing_titles:
            continue
        lines.append(_task_line({
            "id": next_id, "angle": t["angle"], "title": t["title"],
            "desc": t.get("desc", ""), "checked": False, "done": "",
        }))
        existing_titles.add(t["title"])
        next_id += 1
        added += 1

    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return added


def _update_task(app_name: str, task_id: int, **kwargs) -> bool:
    f = _file_for(app_name)
    if not f.exists():
        return False
    _, tasks, lines = _parse_file(f)
    for t in tasks:
        if t["id"] == task_id:
            line_no = t.pop("line_no")
            t.update(kwargs)
            lines[line_no] = _task_line(t)
            f.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return True
    return False


def set_checked(app_path: str, task_id: int, checked: bool) -> bool:
    return _update_task(Path(app_path).name, task_id, checked=checked)


def mark_done(app_name: str, task_id: int) -> bool:
    return _update_task(app_name, task_id, done=datetime.now().strftime("%Y-%m-%dT%H:%M"))


def next_task() -> tuple[str, dict] | None:
    """全提案ファイルから「チェック済み・未完了」の先頭タスクを返す (app_path, task)"""
    if not PROPOSALS_DIR.exists():
        return None
    for f in sorted(PROPOSALS_DIR.glob("*.md")):
        if f.name == "autodev-log.md":
            continue
        meta, tasks, _ = _parse_file(f)
        app_path = meta.get("app_path", "")
        if not app_path or not Path(app_path).exists():
            continue
        for t in tasks:
            if t["checked"] and not t["done"]:
                t.pop("line_no", None)
                return app_path, t
    return None
