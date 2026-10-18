"""git 永続化ユーティリティ — 生成MDのbest-effortコミット + ブランチ操作。
失敗しても呼び出し元の処理は止めない（保管は最善努力、本処理優先）。
"""
import asyncio
import subprocess
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent

# タスク単位worktreeの置き場所（リポジトリ内に置くと未追跡ファイルとして
# AIエージェントのgit操作を汚染するため、リポジトリ外に置く）
WORKTREES_DIR = Path.home() / ".voice-dev" / "worktrees"


def _run_git(args: list[str], cwd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=cwd,
                          capture_output=True, text=True, timeout=timeout)


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


def worktree_path(repo_path: str, task_id: str) -> Path:
    return WORKTREES_DIR / Path(repo_path).name / task_id


def create_worktree(repo_path: str, branch: str, task_id: str, base: str = "") -> tuple[str, str]:
    """タスク専用のgit worktreeを作成する。戻り値: (worktreeパス, ステータス)。
    失敗時はパスが空文字列。既存worktreeがあればそのまま再利用する。
    """
    wt = worktree_path(repo_path, task_id)
    if wt.exists():
        return str(wt), "exists"
    try:
        wt.parent.mkdir(parents=True, exist_ok=True)
        # 前回異常終了の残骸（worktree登録だけ残っている場合）を掃除
        _run_git(["worktree", "prune"], repo_path)
        exists = _run_git(["rev-parse", "--verify", "--quiet", branch], repo_path)
        if exists.returncode == 0:
            r = _run_git(["worktree", "add", str(wt), branch], repo_path, timeout=60)
        else:
            args = ["worktree", "add", "-b", branch, str(wt)]
            if base:
                args.append(base)
            r = _run_git(args, repo_path, timeout=60)
        if r.returncode != 0:
            return "", f"error: {r.stderr.strip()[:200]}"
        return str(wt), "created"
    except Exception as e:
        return "", f"error: {e}"


def remove_worktree(repo_path: str, task_id: str) -> str:
    wt = worktree_path(repo_path, task_id)
    try:
        r = _run_git(["worktree", "remove", "--force", str(wt)], repo_path, timeout=60)
        _run_git(["worktree", "prune"], repo_path)
        if r.returncode != 0:
            return f"error: {r.stderr.strip()[:200]}"
        return "removed"
    except Exception as e:
        return f"error: {e}"


def list_worktrees(repo_path: str) -> list[dict]:
    """voice-devが作成したタスクworktree一覧（統合待ちブランチ）を返す"""
    result: list[dict] = []
    try:
        r = _run_git(["worktree", "list", "--porcelain"], repo_path)
        if r.returncode != 0:
            return []
        entry: dict = {}
        for line in r.stdout.splitlines() + [""]:
            if not line.strip():
                if entry:
                    path = entry.get("path", "")
                    # voice-dev管理のworktreeのみ（メインworktree等は除外）
                    if path.startswith(str(WORKTREES_DIR)):
                        result.append({
                            "path": path,
                            "task_id": Path(path).name,
                            "branch": entry.get("branch", "").replace("refs/heads/", ""),
                            "head": entry.get("HEAD", "")[:8],
                        })
                    entry = {}
                continue
            key, _, value = line.partition(" ")
            if key == "worktree":
                entry["path"] = value
            else:
                entry[key] = value
    except Exception:
        pass
    return result


def merge_branch(repo_path: str, branch: str, into: str = "") -> str:
    """タスクブランチを統合先ブランチへマージする。
    戻り値: "merged" / "conflict" / "error: ..."。コンフリクト時は自動abortし作業ツリーを汚さない。
    """
    try:
        into = into or get_current_branch(repo_path)
        if not into:
            return "error: 統合先ブランチを特定できません"
        current = get_current_branch(repo_path)
        if current != into:
            r = checkout_or_create(repo_path, into)
            if r.startswith("error"):
                return r
        r = _run_git(["merge", "--no-ff", "--no-edit", branch], repo_path, timeout=60)
        if r.returncode == 0:
            return "merged"
        _run_git(["merge", "--abort"], repo_path)
        return "conflict"
    except Exception as e:
        return f"error: {e}"


def push(repo_path: str) -> str:
    """best-effortのgit push（リモート未設定・失敗でも本処理は止めない）"""
    try:
        r = _run_git(["push"], repo_path, timeout=60)
        return "pushed" if r.returncode == 0 else f"push-failed: {r.stderr.strip()[:120]}"
    except Exception as e:
        return f"push-failed: {e}"


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
