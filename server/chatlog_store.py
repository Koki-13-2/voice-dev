"""チャットログストア — セッションごとの会話ログを永続化する（方針F）。

別画面・別チャットに移動してもログが失われないよう、
~/.voice-dev/chatlogs/<session_id>.jsonl に1イベント1行で追記する。
各エントリには連番 seq を付与し、WS再接続時の「ログ復元」と
「未配信バッファ再送」の二重表示をクライアント側で排除できるようにする。
"""
import json
import re
import time
from pathlib import Path

CHATLOG_DIR = Path.home() / ".voice-dev" / "chatlogs"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_-]")

# セッションごとの採番カウンタ（初回アクセス時に既存行数で初期化）
_counters: dict[str, int] = {}


def _file(session_id: str) -> Path:
    safe = _SAFE_ID_RE.sub("_", session_id)[:80]
    return CHATLOG_DIR / f"{safe}.jsonl"


def _next_seq(session_id: str) -> int:
    if session_id not in _counters:
        f = _file(session_id)
        count = 0
        if f.exists():
            try:
                with open(f, encoding="utf-8") as fp:
                    count = sum(1 for _ in fp)
            except Exception:
                count = 0
        _counters[session_id] = count
    _counters[session_id] += 1
    return _counters[session_id]


def append(session_id: str, entry: dict) -> int:
    """エントリを追記し、採番したseqを返す。失敗しても本処理は止めない（seq=0）"""
    try:
        CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        seq = _next_seq(session_id)
        record = {"seq": seq, "ts": time.time(), **entry}
        with open(_file(session_id), "a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")
        return seq
    except Exception as e:
        print(f"[チャットログ保存失敗] session={session_id}: {e}")
        return 0


def append_user(session_id: str, text: str, mode: str = "dev") -> int:
    return append(session_id, {"role": "user", "text": text, "mode": mode})


def append_chunk(session_id: str, chunk: dict) -> int:
    """WS配信チャンクをログエントリに変換して追記する。対象外タイプは0を返す"""
    ctype = chunk.get("type")
    if ctype in ("text", "result_text"):
        return append(session_id, {"role": "ai", "text": chunk.get("content", "")})
    if ctype == "tool_start":
        try:
            input_summary = json.dumps(chunk.get("input", {}), ensure_ascii=False)[:300]
        except Exception:
            input_summary = ""
        return append(session_id, {"role": "tool", "tool": chunk.get("tool", ""),
                                   "input": input_summary})
    if ctype == "tool_end":
        return append(session_id, {"role": "tool_end", "tool": chunk.get("tool", ""),
                                   "result": str(chunk.get("result", ""))[:300]})
    if ctype == "error":
        return append(session_id, {"role": "error", "text": chunk.get("content", "")})
    if ctype == "notice":
        return append(session_id, {"role": "event", "text": chunk.get("content", "")})
    if ctype == "idea_saved":
        title = (chunk.get("idea") or {}).get("title", "")
        return append(session_id, {"role": "event", "text": f"要件定義書「{title}」を保存しました"})
    if ctype == "proposals_updated":
        return append(session_id, {"role": "event",
                                   "text": f"改善提案を{chunk.get('added', 0)}件追加しました"
                                           f"（{chunk.get('parsed', 0)}件読み取り）"})
    return 0


def read(session_id: str, limit: int = 500) -> list[dict]:
    """セッションのログを古い順に最大limit件返す"""
    f = _file(session_id)
    if not f.exists():
        return []
    entries: list[dict] = []
    try:
        with open(f, encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    return entries[-limit:]


def exists(session_id: str) -> bool:
    return _file(session_id).exists()


def delete(session_id: str) -> None:
    _counters.pop(session_id, None)
    try:
        _file(session_id).unlink(missing_ok=True)
    except Exception:
        pass
