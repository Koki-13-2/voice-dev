"""マージ時デグレを構造的に防ぐ共通プリミティブ `safe_merge`。

voice-dev を介す全てのマージ（autodev自動統合 / UI統合 / main昇格）がこれを経由する。

手順:
  1. 最新化強制: target が source の祖先でなければ（source が target より遅れている）、
     先に target を source へ取り込み検証する。こうすると source→target は
     fast-forward 相当になり、3-way マージで target の変更が静かに捨てられる
     （= 本課題の主因デグレ）が構造的に起こり得なくなる。
  2. source→target をマージ。
  3. 検証（build / tsc）。
  4. 失敗時は reset --hard ORIG_HEAD で巻き戻し、ブランチは保持（push しない）。
  5. 成功時のみ push（最新化で source にも新コミットが出来た場合は source も push）。
"""
import asyncio
from pathlib import Path

import gitutil

TSC_TIMEOUT_SEC = 5 * 60
BUILD_TIMEOUT_SEC = 12 * 60


async def _run(cmd: list[str], cwd: str, timeout: int) -> tuple[int, str]:
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=cwd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode, out.decode(errors="replace")
    except asyncio.TimeoutError:
        if proc:
            proc.kill()
        return 1, f"タイムアウト（{timeout}s）: {' '.join(cmd)}"
    except Exception as e:
        return 1, f"実行エラー: {e}"


async def verify(app_path: str, level: str) -> tuple[bool, str]:
    """マージ結果（カレントの作業ツリー）を検証する。
    level: 'off' | 'tsc' | 'build'。戻り値 (ok, detail)。対象構成でなければ ok=True（スキップ）。

    注意: `npm` は WSL 上で Windows 版（/mnt/c/.../npm）に解決され CMD.EXE 起動で
    WSL パスを扱えず失敗する。そのため build は npm ではなく node_modules/.bin の
    ローカルバイナリ（Linux の node shebang で動く）を直接実行する。
    build = `tsc --noEmit` → `vite build`（package.json の "tsc && vite build" と等価）。
    """
    app = Path(app_path)
    if level == "off":
        return True, ""
    tsc = app / "node_modules" / ".bin" / "tsc"
    vite = app / "node_modules" / ".bin" / "vite"

    if level == "tsc":
        if not tsc.exists():
            return True, ""
        rc, out = await _run([str(tsc), "--noEmit"], app_path, TSC_TIMEOUT_SEC)
        return rc == 0, out

    # build
    if not tsc.exists() and not vite.exists():
        return True, ""  # 非対象構成 → スキップ
    if tsc.exists():
        rc, out = await _run([str(tsc), "--noEmit"], app_path, TSC_TIMEOUT_SEC)
        if rc != 0:
            return False, out
    if vite.exists():
        rc, out = await _run([str(vite), "build"], app_path, BUILD_TIMEOUT_SEC)
        return rc == 0, out
    return True, ""


async def safe_merge(app_path: str, source: str, target: str, *,
                     level: str = "build", push: bool = True,
                     bring_in_if_behind: bool = True) -> dict:
    """source を target へ安全にマージする。結果 dict を返す。
    status: 'merged' | 'stale' | 'conflict' | 'verify_failed' | 'error'。
    """
    result = {"ok": False, "status": "error", "detail": "",
              "verified": False, "pushed": "", "brought_in": False}
    orig = await asyncio.to_thread(gitutil.get_current_branch, app_path)

    async def _restore():
        if orig:
            await asyncio.to_thread(gitutil.checkout_or_create, app_path, orig)

    # 1. 最新化強制
    up_to_date = await asyncio.to_thread(gitutil.is_ancestor, app_path, target, source)
    source_verified = False
    if not up_to_date:
        if not bring_in_if_behind:
            result.update(status="stale",
                          detail=f"{source} は {target} より遅れています（{target} 未取込）。"
                                 "再ベース／タスク再実行が必要です（デグレ防止のため中止）")
            await _restore()
            return result
        # target を source に取り込む（checkout source, merge target）
        r = await asyncio.to_thread(gitutil.merge_branch, app_path, target, source)
        if r == "conflict":
            result.update(status="conflict",
                          detail=f"{target} を {source} に取り込む際にコンフリクト。手動解決が必要です")
            await _restore()
            return result
        if r != "merged":
            result.update(status="error", detail=f"{target}→{source} 取込失敗: {r}")
            await _restore()
            return result
        ok, detail = await verify(app_path, level)
        if not ok:
            await asyncio.to_thread(gitutil.undo_merge, app_path)
            result.update(status="verify_failed",
                          detail=f"{target} 取込後の検証({level})に失敗。取込を巻き戻しました:\n{detail[-1500:]}")
            await _restore()
            return result
        source_verified = True   # source は target を含み検証済み
        result["brought_in"] = True

    # 2. source → target
    r = await asyncio.to_thread(gitutil.merge_branch, app_path, source, target)
    if r == "conflict":
        result.update(status="conflict", detail=f"{source}→{target} コンフリクト。手動解決が必要です")
        await _restore()
        return result
    if r != "merged":
        result.update(status="error", detail=f"{source}→{target} マージ失敗: {r}")
        await _restore()
        return result

    # 3. 検証（最新化で source 検証済みなら最終木は同一のためスキップ）
    if not source_verified:
        ok, detail = await verify(app_path, level)
        if not ok:
            await asyncio.to_thread(gitutil.undo_merge, app_path)
            result.update(status="verify_failed",
                          detail=f"{source}→{target} 後の検証({level})に失敗。マージを巻き戻しました:\n{detail[-1500:]}")
            await _restore()
            return result
    result["verified"] = level != "off"

    # 4. push（target → 必要なら source）
    if push:
        result["pushed"] = await asyncio.to_thread(gitutil.push, app_path)
        if result["brought_in"]:
            await asyncio.to_thread(gitutil.checkout_or_create, app_path, source)
            result["pushed_source"] = await asyncio.to_thread(gitutil.push, app_path)

    await _restore()
    result.update(ok=True, status="merged")
    return result
