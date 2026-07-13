import asyncio
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

import shutil
import subprocess

import autodev
import gitutil
import idea_store
import proposal_store
import secrets_store
from claude_client import ClaudeClient, run_oneshot

# 生成AIの生出力キャッシュ（パース失敗時の復旧・デバッグ用、gitignore対象）
CACHE_DIR = Path(__file__).parent.parent / "cache"


def _save_cache(kind: str, stem: str, text: str) -> str:
    """AI生出力を必ずキャッシュに保存し、パスを返す（失敗しても本処理は止めない）"""
    try:
        d = CACHE_DIR / kind
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{stem}.txt"
        f.write_text(text or "", encoding="utf-8")
        return str(f)
    except Exception as e:
        print(f"[キャッシュ保存失敗] {kind}/{stem}: {e}")
        return ""

load_dotenv()

app = FastAPI()

WORKSPACES = [Path.home() / "private-dev", Path.home() / "hennyujuku"]


@app.on_event("startup")
async def _startup():
    asyncio.create_task(autodev.autodev_loop())


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


# ── 要件定義モード: アイデアDB ───────────────────────
@app.get("/api/ideas")
async def get_ideas():
    return JSONResponse(idea_store.list_ideas())


@app.post("/api/ideas/star")
async def star_idea(data: dict):
    idea = idea_store.update_meta(data["id"], starred=bool(data.get("starred")))
    if idea is None:
        return JSONResponse({"error": "アイデアが見つかりません"}, status_code=404)
    return JSONResponse(idea)


@app.delete("/api/ideas/{idea_id}")
async def delete_idea(idea_id: str):
    if not idea_store.delete_idea(idea_id):
        return JSONResponse({"error": "アイデアが見つかりません"}, status_code=404)
    return JSONResponse({"ok": True})


@app.post("/api/ideas/implement")
async def implement_idea(data: dict):
    """アイデアからアプリディレクトリを自動作成して実装を開始する"""
    result = idea_store.get_idea(data["id"])
    if result is None:
        return JSONResponse({"error": "アイデアが見つかりません"}, status_code=404)
    idea, body = result

    ws_path = Path.home() / data.get("workspace", "private-dev")
    if not ws_path.exists():
        return JSONResponse({"error": "ワークスペースが見つかりません"}, status_code=404)

    # 既に実装開始済みならそのディレクトリを返す
    if idea["app_dir"] and Path(idea["app_dir"]).exists():
        app_dir = Path(idea["app_dir"])
    else:
        dir_name = idea_store.dir_name_for(idea["id"], idea["title"])
        app_dir = ws_path / dir_name
        n = 2
        while app_dir.exists():
            app_dir = ws_path / f"{dir_name}-{n}"
            n += 1
        app_dir.mkdir(parents=True)
        subprocess.run(["git", "init"], cwd=str(app_dir), capture_output=True, timeout=15)

    req_dir = app_dir / "requirements"
    req_dir.mkdir(exist_ok=True)
    req_file = req_dir / "要件定義書.md"
    req_file.write_text(body, encoding="utf-8")

    idea_store.update_meta(idea["id"], status="実装中", app_dir=str(app_dir))
    # ステータス変更を確実に保管（best-effort）
    await gitutil.commit_and_push(
        [idea["path"]], f"idea: {idea['title']} の実装を開始（{app_dir.name}）")
    return JSONResponse({
        "name": app_dir.name, "path": str(app_dir), "plan_file": str(req_file),
    })


# ── 秘密情報ストア ───────────────────────────────────
@app.get("/api/secrets")
async def get_secrets(app_name: str):
    try:
        return JSONResponse(secrets_store.list_keys(app_name))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/api/secrets")
async def set_secret(data: dict):
    try:
        secrets_store.set_key(data["app_name"], data["key"], data["value"])
        return JSONResponse({"ok": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.delete("/api/secrets")
async def delete_secret(app_name: str, key: str):
    if not secrets_store.delete_key(app_name, key):
        return JSONResponse({"error": "キーが見つかりません"}, status_code=404)
    return JSONResponse({"ok": True})


# ── 本番接続テスト ───────────────────────────────────
@app.post("/api/test/line")
async def test_line(data: dict):
    """秘密ストアのLINEトークンでプッシュ送信テストを行う"""
    import httpx
    env = secrets_store.load_env(data["app_name"])
    token = env.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = env.get("LINE_USER_ID")
    if not token or not user_id:
        return JSONResponse({
            "error": "秘密情報に LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を登録してください"
        }, status_code=400)
    message = data.get("message") or f"✅ {data['app_name']} からの送信テストです（Voice Dev）"
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(
            "https://api.line.me/v2/bot/message/push",
            headers={"Authorization": f"Bearer {token}"},
            json={"to": user_id, "messages": [{"type": "text", "text": message}]},
        )
    if res.status_code == 200:
        return JSONResponse({"ok": True, "detail": "LINE送信に成功しました"})
    return JSONResponse({"error": f"LINE API エラー ({res.status_code}): {res.text[:300]}"},
                        status_code=502)


@app.post("/api/test/gcloud")
async def test_gcloud():
    """gcloud CLI の認証・プロジェクト設定を確認する"""
    if shutil.which("gcloud") is None:
        return JSONResponse({"error": "gcloud CLI がインストールされていません"}, status_code=400)
    try:
        auth = subprocess.run(
            ["gcloud", "auth", "list", "--format=value(account,status)"],
            capture_output=True, text=True, timeout=30)
        proj = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True, text=True, timeout=30)
        return JSONResponse({
            "ok": True,
            "accounts": auth.stdout.strip() or "(認証済みアカウントなし)",
            "project": proj.stdout.strip() or "(未設定)",
        })
    except subprocess.TimeoutExpired:
        return JSONResponse({"error": "gcloud コマンドがタイムアウトしました"}, status_code=504)


# ── ZIP送付モード ────────────────────────────────────
ZIPMAIL_DEFAULT_TO = "koki.n.shukatsu@gmail.com"
ZIPMAIL_MAX_ZIP_BYTES = 20 * 1024 * 1024  # Gmail添付上限25MBへの安全マージン


@app.get("/api/zipmail/files")
async def zipmail_files(project_path: str):
    """送付対象のファイル一覧（サイズ上限なし・sizeを含む）"""
    proj = Path(project_path)
    try:
        proj.resolve().relative_to(Path.home())
    except ValueError:
        return JSONResponse({"error": "不正なパスです"}, status_code=403)
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
        try:
            size = f.stat().st_size
        except Exception:
            continue
        files.append({
            "name": f.name,
            "path": str(f),
            "rel_path": str(rel),
            "folder": str(rel.parent) if str(rel.parent) != "." else "",
            "size": size,
        })
    return JSONResponse(files)


@app.get("/api/zipmail/config")
async def zipmail_config():
    env = secrets_store.load_env("gmail")
    return JSONResponse({
        "configured": bool(env.get("GMAIL_ADDRESS") and env.get("GMAIL_APP_PASSWORD")),
        "address": env.get("GMAIL_ADDRESS", ""),
        "default_to": ZIPMAIL_DEFAULT_TO,
    })


def _send_gmail(from_addr: str, app_password: str, to_addr: str,
                subject: str, body: str, zip_name: str, zip_bytes: bytes) -> None:
    import smtplib
    from email.message import EmailMessage
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    msg.add_attachment(zip_bytes, maintype="application", subtype="zip", filename=zip_name)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as smtp:
        smtp.login(from_addr, app_password)
        smtp.send_message(msg)


@app.post("/api/zipmail/send")
async def zipmail_send(data: dict):
    """選択ファイルをZIP化してGmailで送付する"""
    import io
    import zipfile
    from datetime import datetime

    project_path = Path(data["project_path"])
    to_addr = (data.get("to") or ZIPMAIL_DEFAULT_TO).strip()
    paths = data.get("paths") or []
    if not paths:
        return JSONResponse({"error": "ファイルが選択されていません"}, status_code=400)
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", to_addr):
        return JSONResponse({"error": "宛先メールアドレスが不正です"}, status_code=400)

    env = secrets_store.load_env("gmail")
    from_addr = env.get("GMAIL_ADDRESS")
    app_password = env.get("GMAIL_APP_PASSWORD")
    if not from_addr or not app_password:
        return JSONResponse({
            "error": "秘密情報（アプリ名: gmail）に GMAIL_ADDRESS と GMAIL_APP_PASSWORD を登録してください"
        }, status_code=400)

    home = Path.home()
    buf = io.BytesIO()
    total_raw = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            f = Path(p).resolve()
            try:
                f.relative_to(home)
            except ValueError:
                return JSONResponse({"error": f"不正なパスです: {p}"}, status_code=403)
            if not f.is_file():
                return JSONResponse({"error": f"ファイルが見つかりません: {p}"}, status_code=404)
            try:
                arcname = str(f.relative_to(project_path.resolve()))
            except ValueError:
                arcname = f.name
            total_raw += f.stat().st_size
            zf.write(f, arcname)

    zip_bytes = buf.getvalue()
    if len(zip_bytes) > ZIPMAIL_MAX_ZIP_BYTES:
        return JSONResponse({
            "error": f"ZIPサイズが上限（20MB）を超えています（{len(zip_bytes) / 1024 / 1024:.1f}MB）。選択ファイルを減らしてください"
        }, status_code=400)

    proj_name = project_path.name or "files"
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    zip_name = f"{proj_name}-{stamp}.zip"
    subject = f"[Voice Dev] {proj_name} のファイル送付（{len(paths)}件）"
    body = (f"Voice Dev からのファイル送付です。\n\n"
            f"プロジェクト: {project_path}\n"
            f"ファイル数: {len(paths)}件\n"
            f"ZIPサイズ: {len(zip_bytes) / 1024:.0f}KB\n")
    try:
        await asyncio.to_thread(_send_gmail, from_addr, app_password, to_addr,
                                subject, body, zip_name, zip_bytes)
    except Exception as e:
        return JSONResponse({"error": f"メール送信に失敗しました: {e}"}, status_code=502)
    return JSONResponse({"ok": True, "zip_name": zip_name, "count": len(paths),
                         "size_kb": round(len(zip_bytes) / 1024), "to": to_addr})


# ── 追加提案蓄積モード ───────────────────────────────
@app.get("/api/proposals")
async def get_proposals(app_path: str):
    return JSONResponse(proposal_store.load(app_path))


@app.post("/api/proposals/toggle")
async def toggle_proposal(data: dict):
    ok = proposal_store.set_checked(data["app_path"], int(data["id"]), bool(data["checked"]))
    if not ok:
        return JSONResponse({"error": "タスクが見つかりません"}, status_code=404)
    return JSONResponse({"ok": True})


@app.get("/api/autodev")
async def get_autodev():
    return JSONResponse(autodev.status())


@app.post("/api/autodev")
async def set_autodev(data: dict):
    cfg = autodev.set_config(
        enabled=data.get("enabled"),
        interval_min=data.get("interval_min"),
        model=data.get("model"),
    )
    # ONにした直後は次のtick（60秒以内）で1件目が動くよう last_run をクリア
    if data.get("enabled"):
        cfg = autodev.set_config(last_run="")
    return JSONResponse(autodev.status())


@app.get("/api/autodev/log")
async def autodev_log():
    if not autodev.LOG_FILE.exists():
        return JSONResponse({"content": ""})
    content = autodev.LOG_FILE.read_text(encoding="utf-8")
    return JSONResponse({"content": content[-8000:]})


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
    # 秘密ストアの接続情報を注入（本番接続テストをAIが実行できるように）
    extra_env = secrets_store.load_env(Path(project_path).name) if project_path else {}
    try:
        async for chunk in client.send_message(
            text, project_path, model,
            plan_file=plan_file, context_files=context_files,
            extra_env=extra_env,
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


IDEA_PROMPT = """あなたはアプリ企画の専門家です。以下のユーザーの発話（アイデア）を、構造化された要件定義書に書き起こしてください。

【出力契約（システムが機械的に読み取るため厳守）】
- ツールは一切使わないこと
- 返答は次の形式「のみ」とすること。マーカーの外には前置き・後書き・コードフェンスなど一切何も書かないこと:

<<<IDEA_START>>>
# <アプリ名>
（要件定義書Markdown本体）
<<<IDEA_END>>>

【要件定義書の構成】
- 必ず `# <アプリ名>` の見出しで始めること（アプリ名は内容から適切に命名）
- 以下のセクションを含めること:
  ## 概要 / ## ターゲットユーザー / ## 解決する課題 / ## 主要機能（表: # | 機能名 | 説明 | 優先度）/ ## 画面構成 / ## データ / ## 技術スタック案 / ## MVPスコープ / ## 元のアイデア（原文）
- 発話に含まれない部分は、アイデアの意図を汲んで具体的に補完すること
- 「元のアイデア（原文）」セクションにはユーザーの発話を引用としてそのまま記載すること

【ユーザーの発話】
{text}
"""

IDEA_RETRY_SUFFIX = """

【重要】前回の返答は出力契約に違反していました（マーカー欠落または構造不足）。
今回は必ず <<<IDEA_START>>> で始まり <<<IDEA_END>>> で終わる形式で、要件定義書のみを出力してください。
"""


async def _generate_oneshot(queue, prompt: str, model: str, *,
                            work_dir: str | None = None,
                            add_dir: str | None = None) -> tuple[str, str]:
    """ワンショット生成をUIにストリームしつつ、(本文テキスト, resultテキスト) を返す"""
    buf: list[str] = []
    result_buf: list[str] = []
    async for chunk in run_oneshot(prompt, model, work_dir=work_dir, add_dir=add_dir):
        if chunk.get("type") == "text":
            buf.append(chunk["content"])
        elif chunk.get("type") == "result_text":
            result_buf.append(chunk["content"])
            continue  # resultテキストはUIに二重表示しない
        await queue.put(chunk)
    return "".join(buf).strip(), "".join(result_buf).strip()


def _extract_idea(stream_text: str, result_text: str):
    """本文→resultの順で要件定義書の抽出を試みる"""
    for raw in (stream_text, result_text):
        if not raw:
            continue
        extracted = idea_store.extract_document(raw)
        if extracted:
            return extracted
    return None


async def _run_idea(session_id: str, text: str, model: str) -> None:
    """要件定義モード: 1送信を要件定義書MDに変換してアイデアDBに保存する。
    出力契約(sentinel) → 抽出 → 検証 → 違反時は1回だけ自動再生成。生出力は必ずキャッシュ。
    """
    queue = task_manager.get_or_create_queue(session_id)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    cache_file = ""
    try:
        idea_store.IDEAS_DIR.mkdir(parents=True, exist_ok=True)
        prompt = IDEA_PROMPT.format(text=text)

        stream_text, result_text = await _generate_oneshot(
            queue, prompt, model, work_dir=str(idea_store.IDEAS_DIR))
        cache_file = _save_cache("idea", ts, stream_text + "\n\n===RESULT===\n\n" + result_text)

        extracted = _extract_idea(stream_text, result_text)

        # 書式違反（抽出不能 or 構造不足）→ 矯正プロンプトで1回だけ再生成
        if not extracted or not idea_store.validate_document(extracted[0]):
            await queue.put({"type": "notice",
                             "content": "書式を検証中: 出力契約違反を検出したため再生成します..."})
            print(f"[要件定義] 書式違反を検出、リトライ実行 (extracted={bool(extracted)})")
            stream_text2, result_text2 = await _generate_oneshot(
                queue, prompt + IDEA_RETRY_SUFFIX, model, work_dir=str(idea_store.IDEAS_DIR))
            _save_cache("idea", f"{ts}-retry", stream_text2 + "\n\n===RESULT===\n\n" + result_text2)
            # リトライ結果を優先、ダメなら初回の抽出結果（検証は通らずとも保存を優先）
            extracted = _extract_idea(stream_text2, result_text2) or extracted

        if extracted:
            content, method = extracted
            idea = idea_store.save_idea(content, text)
            print(f"[要件定義] 保存: {idea['id']} ({method}抽出, valid={idea_store.validate_document(content)})")
            await queue.put({"type": "idea_saved", "idea": idea, "method": method})
            # 蓄積を確実に保管（best-effort git commit + push）
            await gitutil.commit_and_push(
                [idea["path"]], f"idea: {idea['title']} を蓄積")
        else:
            await queue.put({
                "type": "error",
                "content": f"要件定義書の抽出に失敗しました（リトライ済み）。生出力はキャッシュに保存済み: {cache_file}",
            })
    except Exception as e:
        print(f"[要件定義エラー] session={session_id}: {e}")
        await queue.put({"type": "error", "content": str(e)})
    finally:
        await queue.put({"type": "done"})
        await queue.put(None)


PROPOSE_PROMPT = """あなたはこのアプリ（{app_name}）の改善提案の専門家です。コードベースを読み、改善提案を10件程度生成してください。

【出力契約（システムが機械的に読み取るため厳守）】
- 分析にはツール（ファイル読み取り）を使ってよいが、ファイルの変更・作成は一切行わないこと
- 最終返答は必ず次の形式で締めくくること。マーカーの間は「1行1提案」の箇条書きのみとし、
  マーカーの外に提案行を書かないこと:

<<<PROPOSALS_START>>>
- 【カテゴリ/規模】タイトル — 説明（1文）
- 【カテゴリ/規模】タイトル — 説明（1文）
<<<PROPOSALS_END>>>

【提案のルール】
- カテゴリは 機能 / UI/UX / 性能 / セキュリティ / テスト / 運用 から選び、様々な角度をバランスよく含めること
- 規模は 小 / 中 / 大 で、1タスク30分以内で実装可能な粒度に分割すること（大きい提案は分割する）
- タイトルと説明はダッシュ（—）で区切ること
{existing_section}{user_hint}"""

PROPOSE_RETRY_SUFFIX = """

【重要】前回の返答は出力契約に違反しており、提案を1件も読み取れませんでした。
今回は必ず <<<PROPOSALS_START>>> と <<<PROPOSALS_END>>> の間に
`- 【カテゴリ/規模】タイトル — 説明` 形式の行のみを出力してください。ツールは使わず、直前の分析結果から提案リストだけを出力し直してください。
"""


def _parse_proposals(stream_text: str, result_text: str) -> tuple[list, str]:
    """本文→resultの順で、sentinel抽出→緩いパースを試みる。(tasks, 抽出方法)"""
    for raw in (stream_text, result_text):
        if not raw:
            continue
        block, method = proposal_store.extract_block(raw)
        tasks = proposal_store.parse_generated(block)
        if tasks:
            return tasks, method
    return [], "none"


async def _run_propose(session_id: str, text: str, project_path: str, model: str) -> None:
    """追加提案蓄積モード: アプリを解析して改善提案を生成・蓄積する。
    出力契約(sentinel) → 抽出 → パース → 0件なら1回だけ自動再生成。生出力は必ずキャッシュ。
    """
    queue = task_manager.get_or_create_queue(session_id)
    app_name = Path(project_path).name
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    cache_file = ""
    try:
        existing = proposal_store.load(project_path)["tasks"]
        existing_section = ""
        if existing:
            titles = "\n".join(f"- {t['title']}" for t in existing)
            existing_section = f"\n【既存の提案（重複を避けること）】\n{titles}\n"
        user_hint = f"\n【ユーザーからの観点指示】\n{text}\n" if text.strip() else ""

        prompt = PROPOSE_PROMPT.format(
            app_name=app_name, existing_section=existing_section, user_hint=user_hint)

        stream_text, result_text = await _generate_oneshot(
            queue, prompt, model, add_dir=project_path)
        cache_file = _save_cache(
            "propose", f"{app_name}-{ts}",
            stream_text + "\n\n===RESULT===\n\n" + result_text)

        tasks, method = _parse_proposals(stream_text, result_text)

        # 1件もパースできない → 矯正プロンプトで1回だけ再生成
        if not tasks:
            await queue.put({"type": "notice",
                             "content": "書式を検証中: 提案を読み取れなかったため再生成します..."})
            print(f"[提案パース] 0件のためリトライ実行 app={app_name}")
            stream_text2, result_text2 = await _generate_oneshot(
                queue, prompt + PROPOSE_RETRY_SUFFIX, model, add_dir=project_path)
            _save_cache("propose", f"{app_name}-{ts}-retry",
                        stream_text2 + "\n\n===RESULT===\n\n" + result_text2)
            tasks, method = _parse_proposals(stream_text2, result_text2)

        added = proposal_store.add_tasks(project_path, tasks) if tasks else 0
        print(f"[提案パース] app={app_name} 抽出={method} パース={len(tasks)}件 追加={added}件")

        await queue.put({
            "type": "proposals_updated",
            "parsed": len(tasks),
            "added": added,
            "app_path": project_path,
            "cache_file": cache_file if not tasks else "",
        })
        if added > 0:
            # 蓄積を確実に保管（best-effort git commit + push）
            await gitutil.commit_and_push(
                [str(proposal_store._file_for(app_name))],
                f"proposals: {app_name} に{added}件の提案を蓄積")
    except Exception as e:
        print(f"[提案生成エラー] session={session_id}: {e}")
        await queue.put({"type": "error", "content": str(e)})
    finally:
        await queue.put({"type": "done"})
        await queue.put(None)


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
                mode = message.get("mode", "dev")

                print(f"[受信] [{mode}/{model}] {text[:80]}")

                await websocket.send_text(json.dumps({"type": "thinking"}))

                # モードに応じたバックグラウンドタスクとして起動
                if mode == "idea":
                    coro = _run_idea(session_id, text, model)
                elif mode == "propose":
                    coro = _run_propose(session_id, text, project_path, model)
                else:
                    coro = _run_chat(session_id, client, text, project_path, model,
                                     plan_file, context_files)
                task_manager.create_task(session_id, coro)

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
