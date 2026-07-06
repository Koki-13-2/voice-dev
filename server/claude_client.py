import asyncio
import json
import os
from pathlib import Path
from typing import AsyncGenerator

DEFAULT_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """あなたはソフトウェア開発アシスタントです。

【タスク処理ルール】
- 大きなタスクは小さなステップに分割し、一度に実行する処理量を減らすこと
- 各ステップ完了後は次に進む前にユーザーに確認・選択肢を提示すること
- ユーザーに次のアクションを選ばせる際は、必ず以下のフォーマットを使うこと:

:::choices
- 選択肢1
- 選択肢2
- 選択肢3
:::

このブロックはUI上でボタンとして表示される。ユーザーがボタンを押すとその内容が送信される。
選択肢は3〜5個程度に絞り、簡潔な動詞句で書くこと（例: 「実装を開始する」「要件を確認する」「別の方法を提案する」）。"""


class ClaudeClient:
    def __init__(self):
        self.claude_session_id: str | None = None
        self._pending_tools: dict[str, str] = {}  # tool_use_id -> tool_name

    def reset(self):
        self.claude_session_id = None
        self._pending_tools = {}

    async def send_message(
        self, user_text: str, project_path: str, model: str = DEFAULT_MODEL,
        plan_file: str | None = None,
        context_files: list[str] | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> AsyncGenerator[dict, None]:
        if plan_file:
            try:
                plan_content = Path(plan_file).read_text(encoding="utf-8")
            except Exception:
                plan_content = "（ファイルの読み込みに失敗しました）"
            user_text = (
                f"【企画モード】要件定義ファイル: {plan_file}\n\n"
                f"--- 要件定義書の内容 ---\n{plan_content}\n--- ここまで ---\n\n"
                "【ルール】\n"
                "- 要件が明確になったら随時そのMDファイルを更新し git commit すること\n"
                "- ファイルはgitブランチ単位（機能・画面・APIなど）で管理する\n"
                "- 実装を開始する場合は要件を確認してから着手すること\n\n"
                f"{user_text}"
            )

        if context_files:
            sections = []
            for cf in context_files:
                try:
                    content = Path(cf).read_text(encoding="utf-8")
                except Exception:
                    content = "（ファイルの読み込みに失敗しました）"
                sections.append(f"--- {cf} ---\n{content}\n--- ここまで ---")
            prefix = "【参照ファイル】以下のファイルを参考にしてください。\n\n" + "\n\n".join(sections) + "\n\n"
            user_text = prefix + user_text

        cmd = [
            "claude", "-p", user_text,
            "--output-format", "stream-json",
            "--verbose",
            "--model", model,
            "--add-dir", project_path,
            "--dangerously-skip-permissions",
            "--append-system-prompt", SYSTEM_PROMPT,
        ]
        if self.claude_session_id:
            cmd += ["--resume", self.claude_session_id]

        # ANTHROPIC_API_KEY を除外してサブスクリプション認証を使わせる
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        if extra_env:
            # 秘密ストアの接続情報（LINEトークン等）をAIから参照可能にする
            env.update(extra_env)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=project_path,
            env=env,
            limit=8 * 1024 * 1024,  # 8MB: デフォルト64KBだと長い行でLimitOverrunErrorが出る
        )

        try:
            async for raw_line in proc.stdout:
                line = raw_line.decode().strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                etype = event.get("type")

                if etype == "assistant":
                    for block in event.get("message", {}).get("content", []):
                        btype = block.get("type")
                        if btype == "text" and block.get("text"):
                            yield {"type": "text", "content": block["text"]}
                        elif btype == "tool_use":
                            tool_id = block.get("id", "")
                            tool_name = block.get("name", "")
                            self._pending_tools[tool_id] = tool_name
                            yield {
                                "type": "tool_start",
                                "tool": tool_name,
                                "input": block.get("input", {}),
                            }

                elif etype == "user":
                    for block in event.get("message", {}).get("content", []):
                        if block.get("type") == "tool_result":
                            tool_id = block.get("tool_use_id", "")
                            tool_name = self._pending_tools.pop(tool_id, "")
                            content = block.get("content", "")
                            if isinstance(content, list):
                                content = "\n".join(
                                    b.get("text", "") for b in content
                                    if b.get("type") == "text"
                                )
                            yield {
                                "type": "tool_end",
                                "tool": tool_name,
                                "result": str(content)[:500],
                            }

                elif etype == "result":
                    sid = event.get("session_id")
                    if sid:
                        self.claude_session_id = sid
                    if event.get("subtype") != "success":
                        self.claude_session_id = None
                        yield {
                            "type": "error",
                            "content": event.get("error", "Claude CLIエラーが発生しました"),
                        }

        except Exception as e:
            print(f"[stdout読み込みエラー] {e}")
            yield {"type": "error", "content": f"ストリーム読み込みエラー: {e}"}
        finally:
            proc.kill()

        rc = await proc.wait()
        if rc != 0:
            stderr_data = await proc.stderr.read()
            err_text = stderr_data.decode().strip()
            if err_text:
                yield {"type": "error", "content": f"claude CLI エラー: {err_text}"}


async def run_oneshot(
    prompt: str, model: str = DEFAULT_MODEL,
    work_dir: str | None = None,
    add_dir: str | None = None,
    system_prompt: str | None = None,
) -> AsyncGenerator[dict, None]:
    """セッション継続なしのワンショット実行（要件定義書生成・提案生成用）。
    send_message と同じチャンク形式を yield する。
    """
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--model", model,
        "--dangerously-skip-permissions",
    ]
    if add_dir:
        cmd += ["--add-dir", add_dir]
    if system_prompt:
        cmd += ["--append-system-prompt", system_prompt]

    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    cwd = work_dir or add_dir or str(Path.home())

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env,
        limit=8 * 1024 * 1024,
    )

    pending_tools: dict[str, str] = {}
    try:
        async for raw_line in proc.stdout:
            line = raw_line.decode().strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            etype = event.get("type")
            if etype == "assistant":
                for block in event.get("message", {}).get("content", []):
                    btype = block.get("type")
                    if btype == "text" and block.get("text"):
                        yield {"type": "text", "content": block["text"]}
                    elif btype == "tool_use":
                        pending_tools[block.get("id", "")] = block.get("name", "")
                        yield {"type": "tool_start", "tool": block.get("name", ""),
                               "input": block.get("input", {})}
            elif etype == "user":
                for block in event.get("message", {}).get("content", []):
                    if block.get("type") == "tool_result":
                        tool_name = pending_tools.pop(block.get("tool_use_id", ""), "")
                        content = block.get("content", "")
                        if isinstance(content, list):
                            content = "\n".join(
                                b.get("text", "") for b in content if b.get("type") == "text"
                            )
                        yield {"type": "tool_end", "tool": tool_name,
                               "result": str(content)[:500]}
            elif etype == "result":
                if event.get("subtype") != "success":
                    yield {"type": "error",
                           "content": event.get("error", "Claude CLIエラーが発生しました")}
    except Exception as e:
        yield {"type": "error", "content": f"ストリーム読み込みエラー: {e}"}
    finally:
        proc.kill()

    rc = await proc.wait()
    if rc != 0:
        stderr_data = await proc.stderr.read()
        err_text = stderr_data.decode().strip()
        if err_text:
            yield {"type": "error", "content": f"claude CLI エラー: {err_text}"}
