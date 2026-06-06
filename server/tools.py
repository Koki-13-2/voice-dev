import subprocess
import os
from pathlib import Path

TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "ファイルの内容を読む",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "ファイルパス（絶対パスまたはプロジェクトルートからの相対パス）"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "ファイルを作成または上書きする",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "ファイルパス"},
                "content": {"type": "string", "description": "書き込む内容"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_directory",
        "description": "ディレクトリの内容を一覧表示する",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "ディレクトリパス。省略時はプロジェクトルート"}
            }
        }
    },
    {
        "name": "run_shell",
        "description": "シェルコマンドを実行する（git, npm, python等）",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "実行するコマンド"},
                "cwd": {"type": "string", "description": "作業ディレクトリ。省略時はプロジェクトルート"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "create_directory",
        "description": "ディレクトリを作成する",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "作成するディレクトリパス"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "save_knowledge",
        "description": "学んだことやエラー解決策・スニペットをtilリポジトリに自動保存してGitHubにpushする",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["errors", "snippets", "notes", "summary"],
                    "description": "保存カテゴリ: errors=エラー解決, snippets=コード, notes=技術メモ, summary=会話まとめ"
                },
                "title": {"type": "string", "description": "ファイル名になるタイトル（英語スネークケース推奨）"},
                "content": {"type": "string", "description": "Markdown形式の内容"}
            },
            "required": ["category", "title", "content"]
        }
    }
]


TIL_PATH = Path.home() / "til"


def execute_tool(tool_name: str, tool_input: dict, project_path: str) -> str:
    try:
        if tool_name == "read_file":
            return _read_file(tool_input["path"], project_path)
        elif tool_name == "write_file":
            return _write_file(tool_input["path"], tool_input["content"], project_path)
        elif tool_name == "list_directory":
            return _list_directory(tool_input.get("path", ""), project_path)
        elif tool_name == "run_shell":
            return _run_shell(tool_input["command"], tool_input.get("cwd"), project_path)
        elif tool_name == "create_directory":
            return _create_directory(tool_input["path"], project_path)
        elif tool_name == "save_knowledge":
            return _save_knowledge(tool_input["category"], tool_input["title"], tool_input["content"])
        else:
            return f"エラー: 不明なツール '{tool_name}'"
    except Exception as e:
        return f"エラー: {e}"


def _resolve_path(path: str, project_path: str) -> str:
    p = Path(path)
    if p.is_absolute():
        return str(p)
    return str(Path(project_path) / p)


def _read_file(path: str, project_path: str) -> str:
    full_path = _resolve_path(path, project_path)
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    lines = content.splitlines()
    # 行番号付きで返す（大きいファイルは先頭200行まで）
    if len(lines) > 200:
        numbered = "\n".join(f"{i+1}: {l}" for i, l in enumerate(lines[:200]))
        return f"{numbered}\n... (残り {len(lines)-200} 行省略)"
    return "\n".join(f"{i+1}: {l}" for i, l in enumerate(lines))


def _write_file(path: str, content: str, project_path: str) -> str:
    full_path = _resolve_path(path, project_path)
    Path(full_path).parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"書き込み完了: {full_path}"


def _list_directory(path: str, project_path: str) -> str:
    full_path = _resolve_path(path or ".", project_path)
    entries = []
    for entry in sorted(Path(full_path).iterdir()):
        if entry.name.startswith(".") and entry.name not in (".gitignore",):
            continue
        marker = "/" if entry.is_dir() else ""
        entries.append(f"{entry.name}{marker}")
    return "\n".join(entries) if entries else "(空のディレクトリ)"


def _run_shell(command: str, cwd: str | None, project_path: str) -> str:
    work_dir = _resolve_path(cwd, project_path) if cwd else project_path
    result = subprocess.run(
        command,
        shell=True,
        cwd=work_dir,
        capture_output=True,
        text=True,
        timeout=60
    )
    output = result.stdout + result.stderr
    return output.strip() if output.strip() else "(出力なし)"


def _create_directory(path: str, project_path: str) -> str:
    full_path = _resolve_path(path, project_path)
    Path(full_path).mkdir(parents=True, exist_ok=True)
    return f"ディレクトリ作成: {full_path}"


def _save_knowledge(category: str, title: str, content: str) -> str:
    from datetime import date
    today = date.today().isoformat()
    safe_title = title.replace(" ", "_").replace("/", "-")
    file_path = TIL_PATH / category / f"{today}_{safe_title}.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n> 保存日: {today}\n\n{content}\n")
    result = subprocess.run(
        f'git add . && git commit -m "til: {category}/{safe_title}" && git push',
        shell=True, cwd=str(TIL_PATH), capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return f"ファイル保存済みですがpush失敗: {result.stderr}"
    return f"保存・push完了: {file_path.name}"
