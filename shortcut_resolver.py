from __future__ import annotations

import configparser
from pathlib import Path
import pythoncom
from win32com.shell import shell
from utils import extract_appid


def parse_url(path: str) -> dict:
    cp = configparser.ConfigParser()
    cp.read(path, encoding="utf-8")
    url = cp.get("InternetShortcut", "URL", fallback="")
    return {"steam_url": url, "steam_appid": extract_appid(url)}


def parse_lnk(path: str) -> dict:
    pythoncom.CoInitialize()
    link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    persist = link.QueryInterface(pythoncom.IID_IPersistFile)
    persist.Load(path)
    target, _ = link.GetPath(shell.SLGP_RAWPATH)
    args = link.GetArguments()
    wd = link.GetWorkingDirectory()
    icon, _ = link.GetIconLocation()
    text = f"{target} {args}"
    return {"target": target, "arguments": args, "working_directory": wd, "icon": icon, "steam_appid": extract_appid(text)}


def parse_input_file(path: str) -> dict:
    ext = Path(path).suffix.lower()
    if ext == ".url":
        return parse_url(path)
    if ext == ".lnk":
        return parse_lnk(path)
    if ext == ".exe":
        return {"exe": path}
    return {}
