from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass

from process_utils import popen_hidden, run_command_hidden
from windows_paths import normalize_registry_path


SW_SHOWNORMAL = 1
REGEDIT_LAST_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Applets\Regedit"


@dataclass
class RegistryOpenResult:
    ok: bool
    message: str = ""
    normalized_path: str = ""
    needs_elevation: bool = False


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


def open_registry_path(path: str, logger=None) -> RegistryOpenResult:
    if logger:
        logger.debug("RegistryShell", "Open registry requested")
        logger.debug("RegistryShell", f"raw_path={path}")
    normalized = normalize_registry_path(path, logger)
    if logger:
        logger.debug("RegistryShell", f"normalized_path={normalized}")
    if not normalized:
        return RegistryOpenResult(False, "No registry path to open.", normalized)

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
            message = (cp.stderr or cp.stdout or "Failed to write Regedit LastKey.").strip()
            if logger:
                logger.error("RegistryShell", f"reg add failed: {message}")
            return RegistryOpenResult(False, message, normalized)
    except Exception as exc:
        if logger:
            logger.exception("RegistryShell", "reg add exception", exc)
        return RegistryOpenResult(False, str(exc), normalized)

    try:
        if logger:
            logger.debug("RegistryShell", "start regedit args=['regedit.exe'] shell=False hidden=True")
        popen_hidden(["regedit.exe"], logger=logger, module="RegistryShell")
        return RegistryOpenResult(True, "", normalized)
    except Exception as exc:
        winerror = getattr(exc, "winerror", None)
        if logger:
            logger.exception("RegistryShell", "start regedit exception", exc)
            logger.error("RegistryShell", f"start regedit failed: winerror={winerror}, need elevation={winerror == 740}")
        if winerror == 740:
            return RegistryOpenResult(False, "Opening regedit requires administrator privileges.", normalized, True)
        return RegistryOpenResult(False, str(exc), normalized)


def open_regedit_as_admin(logger=None) -> tuple[bool, str]:
    try:
        ctypes.set_last_error(0)
        if logger:
            logger.info("RegistryShell", "Prompt user to run regedit as admin")
            logger.debug("RegistryShell", "ShellExecuteW verb=runas file=regedit.exe")
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "regedit.exe", None, None, SW_SHOWNORMAL)
        last_error = ctypes.get_last_error()
        if logger:
            logger.debug("RegistryShell", f"ShellExecuteW ret={ret} GetLastError={last_error}")
        if ret > 32:
            return True, ""
        return False, str(ctypes.WinError(last_error))
    except Exception as exc:
        if logger:
            logger.exception("RegistryShell", "runas regedit exception", exc)
        return False, str(exc)
