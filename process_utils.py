from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def resolve_powershell_exe(logger=None) -> str:
    candidates: list[str] = []
    for name in ("powershell.exe", "powershell"):
        found = shutil.which(name)
        if found:
            candidates.append(found)

    for env_name in ("SystemRoot", "WINDIR"):
        root = os.environ.get(env_name)
        if root:
            candidates.append(str(Path(root) / "Sysnative" / "WindowsPowerShell" / "v1.0" / "powershell.exe"))
            candidates.append(str(Path(root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"))
            candidates.append(str(Path(root) / "SysWOW64" / "WindowsPowerShell" / "v1.0" / "powershell.exe"))
    candidates.append(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")

    for name in ("pwsh.exe", "pwsh"):
        found = shutil.which(name)
        if found:
            candidates.append(found)

    if logger:
        logger.debug("Process", f"PowerShell candidates={candidates}")

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        key = os.path.normcase(os.path.abspath(candidate))
        if key in seen:
            continue
        seen.add(key)
        try:
            exists = Path(candidate).exists()
            if logger:
                logger.debug("Process", f"Check PowerShell candidate={candidate} exists={exists}")
            if exists:
                if logger:
                    logger.debug("Process", f"Resolved PowerShell executable: {candidate}")
                return candidate
        except Exception as exc:
            if logger:
                logger.exception("Process", f"Failed to check PowerShell candidate: {candidate}", exc)

    if logger:
        logger.error("Process", f"PowerShell executable not found. candidates={candidates} PATH={os.environ.get('PATH', '')}")
    return ""


def _hidden_startup_kwargs() -> dict:
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return {
        "startupinfo": startupinfo,
        "creationflags": subprocess.CREATE_NO_WINDOW,
    }


def run_command_hidden(
    args: list[str],
    *,
    capture_output: bool = True,
    text: bool = True,
    timeout: int | None = None,
    encoding: str = "utf-8",
    errors: str = "replace",
    logger=None,
    module: str = "Process",
) -> subprocess.CompletedProcess:
    kwargs = {
        "shell": False,
        "capture_output": capture_output,
        "text": text,
        "timeout": timeout,
        "encoding": encoding,
        "errors": errors,
    }
    kwargs.update(_hidden_startup_kwargs())
    if logger:
        logger.debug(module, f"External command args={args} shell=False hidden={os.name == 'nt'}")
    try:
        cp = subprocess.run(args, **kwargs)
    except FileNotFoundError as exc:
        if logger:
            logger.error(module, "External command not found")
            logger.error(module, f"command_not_found={args[0] if args else ''}")
            logger.error(module, f"cwd={os.getcwd()}")
            logger.error(module, f"PATH={os.environ.get('PATH', '')}")
            logger.exception(module, "External command FileNotFoundError", exc)
        raise
    if logger:
        logger.debug(module, f"External command returncode={cp.returncode}")
        logger.debug(module, f"External command stdout={(cp.stdout or '').strip() if hasattr(cp, 'stdout') else ''}")
        logger.debug(module, f"External command stderr={(cp.stderr or '').strip() if hasattr(cp, 'stderr') else ''}")
    return cp


def popen_hidden(args: list[str], *, logger=None, module: str = "Process") -> subprocess.Popen:
    kwargs = {"shell": False}
    kwargs.update(_hidden_startup_kwargs())
    if logger:
        logger.debug(module, f"Popen args={args} shell=False hidden={os.name == 'nt'}")
    proc = subprocess.Popen(args, **kwargs)
    if logger:
        logger.debug(module, f"Popen started pid={proc.pid}")
    return proc
