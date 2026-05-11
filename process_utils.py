from __future__ import annotations

import os
import subprocess


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
    cp = subprocess.run(args, **kwargs)
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
