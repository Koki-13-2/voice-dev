import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from claude_client import ClaudeClient

load_dotenv()

app = FastAPI()

WORKSPACES = [Path.home() / "private-dev", Path.home() / "hennyujuku"]


# ── ワークスペースアイコン ────────────────────────────
@app.get("/api/workspace-icon/{name}")
async def workspace_icon(name: str):
    icon = Path.home() / name / "icon.jpg"
    if icon.exists():
        return FileResponse(icon, media_type="image/jpeg")
    return Response(status_code=404)


# ── プロジェクト一覧 ─────────────────────────────────
@app.get("/api/projects")
async def get_projects():
    result = []
    for ws in WORKSPACES:
        if not ws.exists():
            continue
        dirs = sorted(
            [d for d in ws.iterdir() if d.is_dir() and not d.name.startswith(".")],
            key=lambda d: d.name,
        )
        result.append({
            "workspace": ws.name,
            "path": str(ws),
            "projects": [{"name": d.name, "path": str(d)} for d in dirs],
        })
    return JSONResponse(result)


# ── プロジェクトフォルダ新規作成 ────────────────────
@app.post("/api/projects/create")
async def create_project(data: dict):
    workspace = data["workspace"]   # e.g. "private-dev"
    name = data["name"].strip().replace(" ", "-")
    ws_path = Path.home() / workspace
    if not ws_path.exists():
        return JSONResponse({"error": "ワークスペースが見つかりません"}, status_code=404)
    proj_path = ws_path / name
    proj_path.mkdir(parents=True, exist_ok=True)
    return JSONResponse({"name": name, "path": str(proj_path)})


# ── 企画モード: 要件MDファイル一覧 ──────────────────
@app.get("/api/plan/files")
async def plan_files(project_path: str):
    req_dir = Path(project_path) / "requirements"
    if not req_dir.exists():
        return JSONResponse([])
    files = []
    for md in sorted(req_dir.rglob("*.md")):
        rel = md.relative_to(req_dir)
        files.append({
            "name": md.stem,
            "path": str(md),
            "rel_path": str(rel),
            "folder": str(rel.parent) if str(rel.parent) != "." else "",
        })
    return JSONResponse(files)


# ── 企画モード: 要件フォルダ一覧 ────────────────────
@app.get("/api/plan/folders")
async def plan_folders(project_path: str):
    req_dir = Path(project_path) / "requirements"
    if not req_dir.exists():
        return JSONResponse([])
    folders = []
    for d in sorted(req_dir.rglob("*")):
        if d.is_dir():
            rel = str(d.relative_to(req_dir))
            folders.append(rel)
    return JSONResponse(folders)


# ── 企画モード: 要件MDファイル新規作成 ──────────────
@app.post("/api/plan/create-file")
async def plan_create_file(data: dict):
    project_path = data["project_path"]
    folder = data.get("folder", "")
    filename = data["filename"].strip().replace(" ", "-")
    if not filename.endswith(".md"):
        filename += ".md"

    req_dir = Path(project_path) / "requirements"
    target_dir = req_dir / folder if folder else req_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / filename
    if not file_path.exists():
        title = Path(filename).stem.replace("-", " ").replace("_", " ").title()
        # template_category takes priority over folder for template selection
        category = data.get("template_category") or folder or "overview"
        templates = {
            "features": f"""# {title}

## 概要

この機能の目的・背景を記述してください。

## 機能要件

| # | 機能名 | 説明 | 優先度 | ステータス |
|---|--------|------|--------|-----------|
| 1 |  |  | 高 | 未着手 |
| 2 |  |  | 中 | 未着手 |

## 非機能要件

| 項目 | 要件 | 備考 |
|------|------|------|
| パフォーマンス |  |  |
| セキュリティ |  |  |
| 対応環境 |  |  |

## ユーザーストーリー

- **ユーザーとして**、〜できる。

## 受け入れ条件

- [ ] 条件1
- [ ] 条件2

## 備考
""",
            "screens": f"""# {title}

## 概要

この画面の目的・遷移元を記述してください。

## 画面要素

| コンポーネント | 説明 | 必須 | 備考 |
|---------------|------|------|------|
| ヘッダー |  | ○ |  |
| メインコンテンツ |  | ○ |  |
| フッター |  |  |  |

## 画面遷移

| トリガー | 遷移先 | 条件 |
|---------|--------|------|
|  |  |  |

## バリデーション

| フィールド | ルール | エラーメッセージ |
|-----------|--------|----------------|
|  |  |  |

## 備考
""",
            "api": f"""# {title}

## 概要

このAPIの目的・使用箇所を記述してください。

## エンドポイント一覧

| メソッド | パス | 説明 | 認証 |
|---------|------|------|------|
| GET |  |  | 要 |
| POST |  |  | 要 |

## リクエスト／レスポンス仕様

### `POST /example`

**リクエスト**

```json
{{
  "field": "value"
}}
```

**レスポンス**

```json
{{
  "id": 1,
  "field": "value"
}}
```

## エラーコード

| コード | 意味 | 対処 |
|--------|------|------|
| 400 | バリデーションエラー |  |
| 401 | 認証エラー |  |
| 500 | サーバーエラー |  |

## 備考
""",
            "data": f"""# {title}

## 概要

このデータモデルの目的・関連エンティティを記述してください。

## テーブル定義

### `table_name`

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---------|----|------|-----------|------|
| id | INTEGER | ✗ | AUTO | 主キー |
| created_at | DATETIME | ✗ | NOW | 作成日時 |
| updated_at | DATETIME | ✗ | NOW | 更新日時 |

## ER図（テキスト）

```
[Entity A] 1 ---< N [Entity B]
```

## インデックス

| テーブル | カラム | 種別 | 目的 |
|---------|-------|------|------|
|  |  | INDEX |  |

## 備考
""",
            "flows": f"""# {title}

## 概要

このフローの目的・登場人物を記述してください。

## フロー図

```
[開始] → [ステップ1] → [ステップ2] → [終了]
                           ↓ (エラー)
                       [エラー処理]
```

## ステップ詳細

| # | ステップ | アクター | 説明 | 条件 |
|---|---------|---------|------|------|
| 1 |  | ユーザー |  |  |
| 2 |  | システム |  |  |

## 分岐条件

| 条件 | 真の場合 | 偽の場合 |
|------|---------|---------|
|  |  |  |

## 備考
""",
        }
        template = templates.get(category, f"# {title}\n\n## 概要\n\n## 要件\n\n## 備考\n")
        file_path.write_text(template, encoding="utf-8")

    return JSONResponse({"path": str(file_path), "name": Path(filename).stem})


# ── プロジェクトファイル一覧 ────────────────────────
_IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', '.next', 'dist', 'build',
    '.venv', 'venv', '.cache', 'coverage', '.pytest_cache', '.mypy_cache',
    'target', '.gradle', '.idea', '.vscode', '.tox',
}
_IGNORE_EXTS = {
    '.pyc', '.pyo', '.class', '.o', '.so', '.dll', '.exe', '.bin',
    '.jpg', '.jpeg', '.png', '.gif', '.ico', '.webp', '.mp4', '.mp3',
    '.wav', '.zip', '.tar', '.gz', '.whl',
}

@app.get("/api/project/files")
async def project_files(project_path: str):
    proj = Path(project_path)
    if not proj.exists():
        return JSONResponse([])
    files = []
    for f in sorted(proj.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(proj)
        parts = rel.parts
        if any(p in _IGNORE_DIRS or p.startswith('.') for p in parts[:-1]):
            continue
        if parts[-1].startswith('.'):
            continue
        if f.suffix.lower() in _IGNORE_EXTS:
            continue
        try:
            if f.stat().st_size > 150_000:
                continue
        except Exception:
            continue
        files.append({
            "name": f.name,
            "path": str(f),
            "rel_path": str(rel),
            "folder": str(rel.parent) if str(rel.parent) != "." else "",
        })
    return JSONResponse(files)


# ── 企画モード: 要件MDファイル削除 ──────────────────
@app.delete("/api/plan/file")
async def plan_delete_file(path: str):
    file_path = Path(path)
    if not file_path.exists():
        return JSONResponse({"error": "ファイルが見つかりません"}, status_code=404)
    if file_path.suffix != ".md":
        return JSONResponse({"error": "MDファイルのみ削除できます"}, status_code=400)
    try:
        file_path.resolve().relative_to(Path.home())
    except ValueError:
        return JSONResponse({"error": "不正なパスです"}, status_code=403)
    file_path.unlink()
    # 空になったサブフォルダは削除（requirementsルートは保持）
    parent = file_path.parent
    if parent.name != "requirements" and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()
    return JSONResponse({"ok": True})


# ── 企画モード: MDファイル閲覧（新タブ）─────────────
@app.get("/md-view")
async def md_view(path: str):
    md_path = Path(path)
    if not md_path.exists() or md_path.suffix != ".md":
        return HTMLResponse("<p>ファイルが見つかりません</p>", status_code=404)
    content = md_path.read_text(encoding="utf-8")
    import json as _json
    escaped = _json.dumps(content)
    filename = md_path.name
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{filename}</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<style>
  body {{ background:#0d1117; color:#e6edf3; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
         max-width:860px; margin:0 auto; padding:32px 24px; line-height:1.7; }}
  h1,h2,h3 {{ color:#e6edf3; border-bottom:1px solid #30363d; padding-bottom:6px; margin-top:28px; }}
  h1 {{ font-size:1.8rem; }} h2 {{ font-size:1.4rem; }} h3 {{ font-size:1.1rem; }}
  code {{ background:#161b22; border-radius:4px; padding:2px 6px; font-size:0.9em; }}
  pre {{ background:#161b22; border-radius:8px; padding:16px; overflow-x:auto; }}
  pre code {{ background:none; padding:0; }}
  a {{ color:#58a6ff; }}
  .file-path {{ font-size:12px; color:#8b949e; margin-bottom:24px; }}
  table {{ border-collapse:collapse; width:100%; margin:16px 0; font-size:0.9em; }}
  th {{ background:#161b22; color:#e6edf3; font-weight:600; padding:10px 14px; text-align:left; border:1px solid #30363d; }}
  td {{ padding:9px 14px; border:1px solid #30363d; color:#c9d1d9; vertical-align:top; }}
  tr:nth-child(even) td {{ background:#0d1117; }}
  tr:hover td {{ background:#1c2128; }}
  input[type="checkbox"] {{ accent-color:#58a6ff; }}
  .mermaid-wrap {{ position:relative; margin:16px 0; }}
  .mermaid {{ background:#161b22; border-radius:8px; padding:16px; text-align:center; overflow-x:auto; }}
  .mermaid svg {{ max-width:100%; height:auto; }}
  .mermaid-save {{ position:absolute; top:8px; right:8px; background:#21262d; color:#c9d1d9;
    border:1px solid #30363d; border-radius:6px; padding:4px 10px; font-size:12px;
    cursor:pointer; }}
</style>
</head>
<body>
<div class="file-path">📄 {md_path}</div>
<div id="content"></div>
<script>
mermaid.initialize({{
  startOnLoad: false,
  theme: 'dark',
  flowchart: {{ curve: 'stepBefore' }},
  sequence: {{ actorFontFamily: 'monospace' }},
  themeVariables: {{
    background: '#161b22',
    primaryColor: '#1f6feb',
    primaryTextColor: '#e6edf3',
    primaryBorderColor: '#30363d',
    lineColor: '#8b949e',
    secondaryColor: '#21262d',
    tertiaryColor: '#0d1117'
  }}
}});

const renderer = new marked.Renderer();
renderer.code = function(token) {{
  const code = typeof token === 'object' ? (token.text || '') : token;
  const lang = typeof token === 'object' ? (token.lang || '') : arguments[1] || '';
  if (lang === 'mermaid') {{
    return '<div class="mermaid-wrap"><div class="mermaid">' + code + '</div></div>';
  }}
  return '<pre><code>' + code + '</code></pre>';
}};

marked.setOptions({{ renderer }});
document.getElementById('content').innerHTML = marked.parse({escaped});
mermaid.run({{ nodes: document.querySelectorAll('.mermaid') }}).then(() => {{
  document.querySelectorAll('.mermaid-wrap').forEach((wrap, i) => {{
    const svg = wrap.querySelector('svg');
    if (!svg) return;
    const btn = document.createElement('button');
    btn.className = 'mermaid-save';
    btn.textContent = '💾 PNG保存';
    btn.onclick = () => {{
      const svgEl = svg.cloneNode(true);
      const bbox = svg.getBoundingClientRect();
      const scale = 16;
      const w = bbox.width * scale;
      const h = bbox.height * scale;
      svgEl.setAttribute('width', w);
      svgEl.setAttribute('height', h);
      svgEl.setAttribute('viewBox', '0 0 ' + bbox.width + ' ' + bbox.height);
      const svgData = new XMLSerializer().serializeToString(svgEl);
      const img = new Image();
      img.onload = () => {{
        const canvas = document.createElement('canvas');
        canvas.width = w; canvas.height = h;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#161b22';
        ctx.fillRect(0, 0, w, h);
        ctx.drawImage(img, 0, 0);
        const a = document.createElement('a');
        a.href = canvas.toDataURL('image/png');
        a.download = 'diagram-' + (i + 1) + '.png';
        a.click();
      }};
      img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgData);
    }};
    wrap.appendChild(btn);
  }});
}});
</script>
</body>
</html>""")


# ── セッションストア ─────────────────────────────────
sessions: dict[str, ClaudeClient] = {}


# ── バックグラウンドタスク管理 ────────────────────────
class TaskManager:
    """セッションごとのasyncio.Queue / asyncio.Taskを管理する。
    切断後もClaude処理を継続し、再接続時にバッファを配信できる。
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        # 切断時に send_text が失敗して取り出し済みになったチャンクを保持
        self._pending: dict[str, object] = {}

    def get_or_create_queue(self, session_id: str) -> asyncio.Queue:
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue(maxsize=1000)
        return self._queues[session_id]

    def create_task(self, session_id: str, coro) -> asyncio.Task:
        self._queues[session_id] = asyncio.Queue(maxsize=1000)
        task = asyncio.create_task(coro)
        self._tasks[session_id] = task
        return task

    def is_running(self, session_id: str) -> bool:
        return session_id in self._queues

    def cleanup(self, session_id: str) -> None:
        self._queues.pop(session_id, None)
        self._tasks.pop(session_id, None)
        self._pending.pop(session_id, None)

    def save_pending(self, session_id: str, chunk: object) -> None:
        """送信失敗したチャンクを次回再接続まで保持する"""
        self._pending[session_id] = chunk

    def pop_pending(self, session_id: str) -> object | None:
        return self._pending.pop(session_id, None)


task_manager = TaskManager()


async def _run_chat(
    session_id: str,
    client: ClaudeClient,
    text: str,
    project_path: str,
    model: str,
    plan_file: str | None,
    context_files: list,
) -> None:
    """Claude処理をバックグラウンドで実行し、結果をQueueに積む"""
    queue = task_manager.get_or_create_queue(session_id)
    try:
        async for chunk in client.send_message(
            text, project_path, model,
            plan_file=plan_file, context_files=context_files,
        ):
            if chunk.get("_break"):
                continue
            await queue.put(chunk)
    except Exception as e:
        print(f"[バックグラウンドエラー] session={session_id}: {e}")
        await queue.put({"type": "error", "content": str(e)})
    finally:
        await queue.put({"type": "done"})
        await queue.put(None)  # 終了sentinel


async def _drain_queue(session_id: str, websocket: WebSocket) -> None:
    """QueueのチャンクをWebSocketへ送り続ける（None sentinel受信で終了）。
    送信失敗チャンクは TaskManager に保存し、次回再接続時に再送する。
    """
    queue = task_manager.get_or_create_queue(session_id)
    chunk = None
    try:
        # 前回切断時に送信できなかったチャンクを先に処理
        pending = task_manager.pop_pending(session_id)
        if pending is not None:
            await websocket.send_text(json.dumps(pending))

        while True:
            chunk = await queue.get()
            if chunk is None:
                task_manager.cleanup(session_id)
                break
            await websocket.send_text(json.dumps(chunk))
            chunk = None  # 送信成功したのでリセット
    except Exception:
        # 取り出し済みで未送信のチャンクを保存（再接続時に再送）
        if chunk is not None:
            task_manager.save_pending(session_id, chunk)
        raise


@app.get("/")
async def root():
    client_path = Path(__file__).parent.parent / "client" / "index.html"
    return FileResponse(client_path)


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    print(f"[接続] session={session_id}")

    if session_id not in sessions:
        sessions[session_id] = ClaudeClient()

    client = sessions[session_id]

    try:
        # 再接続時: 進行中タスクのバッファを即座に配信
        if task_manager.is_running(session_id):
            print(f"[再接続] バッファをドレイン session={session_id}")
            await websocket.send_text(json.dumps({"type": "thinking"}))
            await _drain_queue(session_id, websocket)

        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)

            msg_type = message.get("type")

            if msg_type == "chat":
                text = message["text"]
                project_path = message.get("project_path", os.path.expanduser("~"))
                model = message.get("model", "claude-sonnet-4-6")
                plan_file = message.get("plan_file")
                context_files = message.get("context_files", [])

                print(f"[受信] [{model}] {text[:80]}")

                await websocket.send_text(json.dumps({"type": "thinking"}))

                # バックグラウンドタスクとして起動
                task_manager.create_task(
                    session_id,
                    _run_chat(session_id, client, text, project_path, model, plan_file, context_files),
                )

                # タスク完了または切断まで配信
                await _drain_queue(session_id, websocket)

            elif msg_type == "reset":
                client.reset()
                await websocket.send_text(json.dumps({
                    "type": "text",
                    "content": "会話をリセットしました。"
                }))

    except WebSocketDisconnect:
        print(f"[切断] session={session_id} (バックグラウンドタスクは継続中)")
    except Exception as e:
        print(f"[エラー] {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    cert = Path(__file__).parent / "cert.pem"
    key = Path(__file__).parent / "key.pem"
    if cert.exists() and key.exists():
        uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True,
                    ssl_certfile=str(cert), ssl_keyfile=str(key))
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
