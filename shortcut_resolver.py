from __future__ import annotations

import configparser
from pathlib import Path
import pythoncom
from win32com.shell import shell
from utils import extract_appid


def parse_url(path: str, logger=None) -> dict:
    cp = configparser.ConfigParser()
    cp.read(path, encoding="utf-8")
    url = cp.get("InternetShortcut", "URL", fallback="")
    if logger:
        try:
            logger.debug("Shortcut", f".url raw content: {Path(path).read_text(encoding='utf-8', errors='replace')}")
        except Exception as exc:
            logger.exception("Shortcut", f"Failed to read .url raw content: {path}", exc)
    return {"steam_url": url, "steam_appid": extract_appid(url)}


def parse_lnk(path: str, logger=None) -> dict:
    pythoncom.CoInitialize()
    link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    persist = link.QueryInterface(pythoncom.IID_IPersistFile)
    persist.Load(path)
    target, _ = link.GetPath(shell.SLGP_RAWPATH)
    args = link.GetArguments()
    wd = link.GetWorkingDirectory()
    icon, _ = link.GetIconLocation()
    text = f"{target} {args}"
    if logger:
        logger.debug("Shortcut", f".lnk TargetPath: {target}")
        logger.debug("Shortcut", f".lnk Arguments: {args}")
        logger.debug("Shortcut", f".lnk WorkingDirectory: {wd}")
        logger.debug("Shortcut", f".lnk IconLocation: {icon}")
    return {"target": target, "arguments": args, "working_directory": wd, "icon": icon, "steam_appid": extract_appid(text)}


def parse_input_file(path: str, logger=None) -> dict:
    ext = Path(path).suffix.lower()
    if logger:
        logger.info("Input", f"拖入文件: {path}")
        logger.debug("Input", f"Input file type: {ext or 'no extension'}")
    if ext == ".url":
        return parse_url(path, logger)
    if ext == ".lnk":
        return parse_lnk(path, logger)
    if ext == ".exe":
        return {"exe": path}
    return {}
