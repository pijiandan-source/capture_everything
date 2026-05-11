from __future__ import annotations

import configparser
import os
from pathlib import Path
import pythoncom
from win32com.shell import shell
from utils import extract_appid
from windows_paths import strip_icon_index


def split_icon_location(icon: str, index: int | str = "") -> tuple[str, str]:
    raw = (icon or "").strip()
    idx = "" if index is None else str(index)
    if raw.startswith('"'):
        end = raw.find('"', 1)
        if end != -1:
            path = raw[1:end]
            rest = raw[end + 1:].strip()
            if rest.startswith(",") and not idx:
                idx = rest[1:].strip()
            return path, idx
    if "," in raw:
        path_part, maybe_index = raw.rsplit(",", 1)
        if maybe_index.strip().lstrip("-").isdigit():
            return strip_icon_index(raw), idx or maybe_index.strip()
    return strip_icon_index(raw), idx


def parse_url(path: str, logger=None) -> dict:
    cp = configparser.ConfigParser()
    cp.read(path, encoding="utf-8")
    url = cp.get("InternetShortcut", "URL", fallback="")
    icon_file = cp.get("InternetShortcut", "IconFile", fallback="")
    icon_index = cp.get("InternetShortcut", "IconIndex", fallback="")
    icon_path, icon_index = split_icon_location(icon_file, icon_index)
    if logger:
        logger.debug("Shortcut", f"shortcut_path={path}")
        logger.debug("Shortcut", "shortcut_type=.url")
        logger.debug("Shortcut", f"URL={url}")
        logger.debug("Shortcut", f"IconFile={icon_file}")
        logger.debug("Shortcut", f"IconIndex={icon_index}")
        logger.debug("Shortcut", f"icon_exists={os.path.exists(icon_path) if icon_path else False}")
        try:
            logger.debug("Shortcut", f".url raw content: {Path(path).read_text(encoding='utf-8', errors='replace')}")
        except Exception as exc:
            logger.exception("Shortcut", f"Failed to read .url raw content: {path}", exc)
    return {
        "shortcut_type": ".url",
        "shortcut_path": path,
        "steam_url": url,
        "steam_appid": extract_appid(url),
        "shortcut_icon_path": icon_path,
        "shortcut_icon_index": icon_index,
    }


def parse_lnk(path: str, logger=None) -> dict:
    pythoncom.CoInitialize()
    link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    persist = link.QueryInterface(pythoncom.IID_IPersistFile)
    persist.Load(path)
    target, _ = link.GetPath(shell.SLGP_RAWPATH)
    args = link.GetArguments()
    wd = link.GetWorkingDirectory()
    icon, icon_index = link.GetIconLocation()
    icon_path, icon_index = split_icon_location(icon, icon_index)
    text = f"{target} {args}"
    if logger:
        logger.debug("Shortcut", f"shortcut_path={path}")
        logger.debug("Shortcut", "shortcut_type=.lnk")
        logger.debug("Shortcut", f".lnk TargetPath: {target}")
        logger.debug("Shortcut", f".lnk Arguments: {args}")
        logger.debug("Shortcut", f".lnk WorkingDirectory: {wd}")
        logger.debug("Shortcut", f".lnk IconLocation: {icon}")
        logger.debug("Shortcut", f"shortcut_icon_path={icon_path}")
        logger.debug("Shortcut", f"shortcut_icon_index={icon_index}")
        logger.debug("Shortcut", f"icon_exists={os.path.exists(icon_path) if icon_path else False}")
    return {
        "shortcut_type": ".lnk",
        "shortcut_path": path,
        "target": target,
        "arguments": args,
        "working_directory": wd,
        "shortcut_icon_path": icon_path,
        "shortcut_icon_index": str(icon_index),
        "steam_appid": extract_appid(text),
    }


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
