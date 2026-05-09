from __future__ import annotations

import os
from pathlib import Path

import vdf
import winreg


def find_steam_path(logger=None) -> str:
    keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
    ]
    for root, sub, name in keys:
        try:
            with winreg.OpenKey(root, sub) as k:
                val, _ = winreg.QueryValueEx(k, name)
                if logger:
                    logger.debug("SteamResolver", f"Registry {sub}/{name}={val}")
                if os.path.isdir(val):
                    if logger:
                        logger.info("Steam", f"Found SteamPath/InstallPath: {val}")
                    return val
        except OSError as exc:
            if logger:
                logger.debug("SteamResolver", f"Registry read failed: {sub}/{name}, error={exc}")
    for p in [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]:
        if os.path.isdir(p):
            if logger:
                logger.info("Steam", f"Use default Steam path: {p}")
            return p
    if logger:
        logger.warning("Steam", "Steam install path not found")
    return ""


def parse_libraries(steam_path: str, logger=None) -> list[str]:
    libs = []
    lib_vdf = Path(steam_path) / "steamapps" / "libraryfolders.vdf"
    if logger:
        logger.debug("SteamResolver", f"libraryfolders.vdf path: {lib_vdf}")
    if not lib_vdf.exists():
        if logger:
            logger.debug("SteamResolver", f"libraryfolders.vdf does not exist: {lib_vdf}")
        return libs
    data = vdf.load(open(lib_vdf, encoding="utf-8"))
    lf = data.get("libraryfolders", {})
    for k, v in lf.items():
        if isinstance(v, dict) and "path" in v:
            libs.append(v["path"])
        elif str(k).isdigit() and isinstance(v, str):
            libs.append(v)
    if steam_path not in libs:
        libs.append(steam_path)
    if logger:
        for lib in libs:
            logger.debug("SteamResolver", f"Steam Library: {lib}, exists={os.path.isdir(lib)}")
    return libs


def resolve_appid(appid: str, logger=None) -> dict:
    if logger:
        logger.info("Steam", f"Resolve AppID: {appid}")
    steam_path = find_steam_path(logger)
    libs = parse_libraries(steam_path, logger) if steam_path else []
    for lib in libs:
        mf = Path(lib) / "steamapps" / f"appmanifest_{appid}.acf"
        if logger:
            logger.debug("SteamResolver", f"Check manifest: {mf}")
        if mf.exists():
            data = vdf.load(open(mf, encoding="utf-8")).get("AppState", {})
            name = data.get("name", "")
            installdir = data.get("installdir", "")
            install_dir = str(Path(lib) / "steamapps" / "common" / installdir)
            if logger:
                logger.debug("SteamResolver", f"appmanifest fields: {data}")
                logger.info("Steam", f"Found game install dir: {install_dir}")
            return {"steam_path": steam_path, "libraries": libs, "manifest": str(mf), "name": name, "install_dir": install_dir}
    return {"steam_path": steam_path, "libraries": libs}
