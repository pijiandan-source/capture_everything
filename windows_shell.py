from __future__ import annotations

import ctypes
import os

from process_utils import popen_hidden, run_command_hidden
from windows_paths import normalize_registry_path


SW_SHOWNORMAL = 1
REGEDIT_LAST_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Applets\Regedit"


def open_properties(path: str, logger=None) -> bool:
    exists = os.path.exists(path)
    if logger:
        logger.debug("WindowsAPI", f"Button=Properties path={path} empty={not bool(path)} exists={exists}")
    if not path:
        return False

    try:
        from win32com.shell import shell, shellcon

        args = {
            "fMask": shellcon.SEE_MASK_INVOKEIDLIST,
            "lpVerb": "properties",
            "lpFile": path,
            "nShow": SW_SHOWNORMAL,
        }
        if logger:
            logger.debug("WindowsAPI", f"API=ShellExecuteEx args={args} path_exists={exists}")
        ret = shell.ShellExecuteEx(**args)
        if logger:
            logger.debug("WindowsAPI", f"API=ShellExecuteEx ret={ret}")
        return True
    except Exception as exc:
        if logger:
            logger.exception("WindowsAPI", f"ShellExecuteEx properties failed for path={path}; fallback to ShellExecuteW", exc)

    try:
        ctypes.set_last_error(0)
        ret = ctypes.windll.shell32.ShellExecuteW(None, "properties", path, None, None, SW_SHOWNORMAL)
        last_error = ctypes.get_last_error()
        if logger:
            logger.debug("WindowsAPI", f"API=ShellExecuteW verb=properties path={path} ret={ret} GetLastError={last_error}")
        if ret > 32:
            return True
        try:
            win_error = ctypes.WinError(last_error)
        except Exception as exc:
            win_error = exc
        if logger:
            logger.error("WindowsAPI", f"ShellExecuteW properties failed: ret={ret}, GetLastError={last_error}, WinError={win_error}")
    except Exception as exc:
        if logger:
            logger.exception("WindowsAPI", f"ShellExecuteW exception for path={path}", exc)

    cmd = ["explorer.exe", f"/select,{path}"]
    try:
        popen_hidden(cmd, logger=logger, module="WindowsAPI")
        return False
    except Exception as exc:
        if logger:
            logger.exception("WindowsAPI", f"Fallback explorer failed for path={path}", exc)
        return False


def open_registry_path(path: str, logger=None) -> tuple[bool, str]:
    if logger:
        logger.debug("RegistryShell", "Open registry requested")
        logger.debug("RegistryShell", f"raw_path={path}")
    normalized = normalize_registry_path(path, logger)
    if logger:
        logger.debug("RegistryShell", f"normalized_path={normalized}")
    if not normalized:
        return False, "当前没有可打开的注册表路径"

    args = [
        "reg", "add",
        REGEDIT_LAST_KEY,
        "/v", "LastKey",
        "/d", normalized,
        "/f",
    ]
    try:
        if logger:
            logger.debug("RegistryShell", f"LastKey={normalized}")
            logger.debug("RegistryShell", f"reg add args={args}")
        cp = run_command_hidden(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, logger=logger, module="RegistryShell")
        if cp.returncode != 0:
            message = (cp.stderr or cp.stdout or "注册表路径格式无法识别或无法打开").strip()
            if logger:
                logger.error("RegistryShell", f"reg add failed: {message}")
            return False, message
    except Exception as exc:
        if logger:
            logger.exception("RegistryShell", "reg add exception", exc)
        return False, str(exc)

    try:
        popen_hidden(["regedit.exe"], logger=logger, module="RegistryShell")
        return True, ""
    except Exception as exc:
        if logger:
            logger.exception("RegistryShell", "start regedit exception", exc)
        return False, str(exc)
