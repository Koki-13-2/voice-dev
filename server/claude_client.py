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


_AUTH_ERROR_PATTERNS = ("401", "unauthorized", "oauth", "auth", "credential", "login")

# claude CLIは ~/.claude/.credentials.json のOAuthトークン（ローテーション式・使い切り）を
# 起動のたびに参照・更新する。完全直列化は廃止し最大3並行を許容。
# 競合時の401エラーは send_message/_run_oneshot_impl の _auth_retry 機構でリカバリする。
CLI_LOCK = asyncio.Semaphore(3)


class ClaudeClient:
    def __init__(self):
        self.claude_session_id: str | None = None
        self._pending_tools: dict[str, str] = {}  # tool_use_id -> tool_name
        self._proc: asyncio.subprocess.Process | None = None

    def reset(self):
        self.claude_session_id = None
        self._pending_tools = {}

    async def cancel(self):
        """実行中のCLIプロセスを停止してセッションをリセットする"""
        if self._proc and self._proc.returncode is None:
            try:
                self._proc.kill()
                await self._proc.wait()
            except ProcessLookupError:
                pass
        self._proc = None
        self.reset()

    async def send_message(
        self, user_text: str, project_path: str, model: str = DEFAULT_MODEL,
        plan_file: str | None = None,
        context_files: list[str] | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> AsyncGenerator[dict, None]:
        async for chunk in self._send_message_impl(
            user_text, project_path, model,
            plan_file=plan_file, context_files=context_files,
            extra_env=extra_env, _retry=False,
        ):
            if chunk.get("_auth_retry"):
                print("[認証エラー] セッションをリセットして再試行します")
                self.reset()
                async for retry_chunk in self._send_message_impl(
                    user_text, project_path, model,
                    plan_file=plan_file, context_files=context_files,
                    extra_env=extra_env, _retry=True,
                ):
                    if not retry_chunk.get("_auth_retry"):
                        yield retry_chunk
                return
            yield chunk

    async def _send_message_impl(
        self, user_text: str, project_path: str, model: str = DEFAULT_MODEL,
        plan_file: str | None = None,
        context_files: list[str] | None = None,
        extra_env: dict[str, str] | None = None,
        _retry: bool = False,
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

        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        if extra_env:
            env.update(extra_env)

        async with CLI_LOCK:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_path,
                env=env,
                limit=8 * 1024 * 1024,
            )
            self._proc = proc

            got_output = False
            try:
                async for raw_line in proc.stdout:
                    line = raw_line.decode().strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    got_output = True
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
                            err_msg = event.get("error", "")
                            if not _retry and self._is_auth_error(err_msg):
                                yield {"_auth_retry": True}
                                return
                            yield {
                                "type": "error",
                                "content": err_msg or "Claude CLIエラーが発生しました",
                            }
                        usage = event.get("usage")
                        if usage:
                            yield {
                                "type": "usage",
                                "usage": usage,
                                "cost_usd": event.get("total_cost_usd"),
                            }

            except Exception as e:
                print(f"[stdout読み込みエラー] {e}")
                yield {"type": "error", "content": f"ストリーム読み込みエラー: {e}"}
            finally:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                self._proc = None

            rc = await proc.wait()
            if rc != 0:
                stderr_data = await proc.stderr.read()
                err_text = stderr_data.decode().strip()
                if err_text:
                    if not _retry and not got_output and self._is_auth_error(err_text):
                        yield {"_auth_retry": True}
                        return
                    yield {"type": "error", "content": f"claude CLI エラー: {err_text}"}

    @staticmethod
    def _is_auth_error(text: str) -> bool:
        lower = text.lower()
        return any(p in lower for p in _AUTH_ERROR_PATTERNS)


async def run_oneshot(
    prompt: str, model: str = DEFAULT_MODEL,
    work_dir: str | None = None,
    add_dir: str | None = None,
    system_prompt: str | None = None,
) -> AsyncGenerator[dict, None]:
    """セッション継続なしのワンショット実行（要件定義書生成・提案生成用）。
    send_message と同じチャンク形式を yield する。401 OAuthエラー検知時は
    send_message と同様に一度だけ再試行する。
    """
    async for chunk in _run_oneshot_impl(
        prompt, model, work_dir=work_dir, add_dir=add_dir,
        system_prompt=system_prompt, _retry=False,
    ):
        if chunk.get("_auth_retry"):
            print("[認証エラー] ワンショット実行を再試行します")
            async for retry_chunk in _run_oneshot_impl(
                prompt, model, work_dir=work_dir, add_dir=add_dir,
                system_prompt=system_prompt, _retry=True,
            ):
                if not retry_chunk.get("_auth_retry"):
                    yield retry_chunk
            return
        yield chunk


async def _run_oneshot_impl(
    prompt: str, model: str = DEFAULT_MODEL,
    work_dir: str | None = None,
    add_dir: str | None = None,
    system_prompt: str | None = None,
    _retry: bool = False,
) -> AsyncGenerator[dict, None]:
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

    async with CLI_LOCK:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
            limit=8 * 1024 * 1024,
        )

        pending_tools: dict[str, str] = {}
        got_output = False
        try:
            async for raw_line in proc.stdout:
                line = raw_line.decode().strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                got_output = True
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
                    if event.get("subtype") == "success":
                        result_text = event.get("result", "")
                        if result_text:
                            yield {"type": "result_text", "content": result_text}
                    else:
                        err_msg = event.get("error", "")
                        if not _retry and ClaudeClient._is_auth_error(err_msg):
                            yield {"_auth_retry": True}
                            return
                        yield {"type": "error",
                               "content": err_msg or "Claude CLIエラーが発生しました"}
                    usage = event.get("usage")
                    if usage:
                        yield {
                            "type": "usage",
                            "usage": usage,
                            "cost_usd": event.get("total_cost_usd"),
                        }
        except Exception as e:
            yield {"type": "error", "content": f"ストリーム読み込みエラー: {e}"}
        finally:
            try:
                proc.kill()
            except ProcessLookupError:
                pass  # 既に正常終了している場合

        rc = await proc.wait()
        if rc != 0:
            stderr_data = await proc.stderr.read()
            err_text = stderr_data.decode().strip()
            if err_text:
                if not _retry and not got_output and ClaudeClient._is_auth_error(err_text):
                    yield {"_auth_retry": True}
                    return
                yield {"type": "error", "content": f"claude CLI エラー: {err_text}"}
