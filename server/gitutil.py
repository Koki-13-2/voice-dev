"""git 永続化ユーティリティ — 生成MDのbest-effortコミット + ブランチ操作。
失敗しても呼び出し元の処理は止めない（保管は最善努力、本処理優先）。
"""
import asyncio
import subprocess
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent


def is_git_repo(repo_path: str) -> bool:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=repo_path, capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def get_current_branch(repo_path: str) -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def list_branches(repo_path: str) -> dict:
    current = get_current_branch(repo_path)
    branches: list[str] = []
    try:
        r = subprocess.run(
            ["git", "branch", "--format=%(refname:short)"],
            cwd=repo_path, capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            branches = [b.strip() for b in r.stdout.splitlines() if b.strip()]
    except Exception:
        pass
    return {"current": current, "branches": branches}


def checkout_or_create(repo_path: str, branch: str) -> str:
    current = get_current_branch(repo_path)
    if current == branch:
        return "already-on-branch"
    try:
        r = subprocess.run(
            ["git", "checkout", branch],
            cwd=repo_path, capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            return "checked-out"
        r = subprocess.run(
            ["git", "checkout", "-b", branch],
            cwd=repo_path, capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            return "created"
        return f"error: {r.stderr.strip()[:200]}"
    except Exception as e:
        return f"error: {e}"


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
