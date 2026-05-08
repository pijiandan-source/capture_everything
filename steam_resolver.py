from __future__ import annotations

import os
from pathlib import Path
import winreg
import vdf


def find_steam_path() -> str:
    keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
    ]
    for root, sub, name in keys:
        try:
            with winreg.OpenKey(root, sub) as k:
                val, _ = winreg.QueryValueEx(k, name)
                if os.path.isdir(val):
                    return val
        except OSError:
            pass
    for p in [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]:
        if os.path.isdir(p):
            return p
    return ""


def parse_libraries(steam_path: str) -> list[str]:
    libs = []
    lib_vdf = Path(steam_path) / "steamapps" / "libraryfolders.vdf"
    if not lib_vdf.exists():
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
    return libs


def resolve_appid(appid: str) -> dict:
    steam_path = find_steam_path()
    libs = parse_libraries(steam_path) if steam_path else []
    for lib in libs:
        mf = Path(lib) / "steamapps" / f"appmanifest_{appid}.acf"
        if mf.exists():
            data = vdf.load(open(mf, encoding="utf-8")).get("AppState", {})
            name = data.get("name", "")
            installdir = data.get("installdir", "")
            install_dir = str(Path(lib) / "steamapps" / "common" / installdir)
            return {"steam_path": steam_path, "libraries": libs, "manifest": str(mf), "name": name, "install_dir": install_dir}
    return {"steam_path": steam_path, "libraries": libs}
