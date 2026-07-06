"""git 永続化ユーティリティ — 生成MDのbest-effortコミット。
失敗しても呼び出し元の処理は止めない（保管は最善努力、本処理優先）。
"""
import asyncio
import subprocess
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent


def _commit_and_push_sync(paths: list[str], message: str) -> str:
    try:
        rel_paths = [str(p) for p in paths]
        subprocess.run(["git", "add", "--"] + rel_paths,
                       cwd=REPO_DIR, capture_output=True, timeout=15)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"],
                              cwd=REPO_DIR, capture_output=True, timeout=15)
        if diff.returncode == 0:
            return "no-change"
        commit = subprocess.run(["git", "commit", "-m", message],
                                cwd=REPO_DIR, capture_output=True, text=True, timeout=20)
        if commit.returncode != 0:
            return f"commit-failed: {commit.stderr.strip()[:200]}"
        push = subprocess.run(["git", "push"],
                              cwd=REPO_DIR, capture_output=True, text=True, timeout=30)
        if push.returncode != 0:
            return f"committed (push-failed: {push.stderr.strip()[:120]})"
        return "committed+pushed"
    except Exception as e:
        return f"error: {e}"


async def commit_and_push(paths: list[str], message: str) -> str:
    """非同期・ノンブロッキングでコミット+プッシュ。結果文字列を返す（ログ用）"""
    result = await asyncio.to_thread(_commit_and_push_sync, paths, message)
    print(f"[git保管] {message} -> {result}")
    return result
