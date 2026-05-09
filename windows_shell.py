from __future__ import annotations

import ctypes
import os
import subprocess


SW_SHOWNORMAL = 1


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
        if logger:
            logger.debug("WindowsAPI", f"Fallback command args={cmd} shell=False")
        proc = subprocess.Popen(cmd, shell=False)
        if logger:
            logger.debug("WindowsAPI", f"Fallback explorer started pid={proc.pid}")
        return False
    except Exception as exc:
        if logger:
            logger.exception("WindowsAPI", f"Fallback explorer failed for path={path}", exc)
        return False
