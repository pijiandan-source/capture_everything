from __future__ import annotations

import winreg

from rapidfuzz import fuzz

from models import RegistryCandidate
from utils import norm_path
from windows_paths import clean_display_path, extract_exe_from_command

UNINSTALL_ROOTS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]
FIELDS = ["DisplayName", "DisplayVersion", "Publisher", "InstallLocation", "InstallSource", "DisplayIcon", "UninstallString", "QuietUninstallString", "EstimatedSize", "NoModify", "NoRepair", "URLInfoAbout", "HelpLink"]


def readable_key(root, sub: str) -> str:
    if root == winreg.HKEY_LOCAL_MACHINE:
        root_name = "HKEY_LOCAL_MACHINE"
    elif root == winreg.HKEY_CURRENT_USER:
        root_name = "HKEY_CURRENT_USER"
    else:
        root_name = str(root)
    return f"{root_name}\\{sub}"


def _read_values(k):
    d = {}
    for f in FIELDS:
        try:
            d[f] = winreg.QueryValueEx(k, f)[0]
        except OSError:
            d[f] = ""
    return d


def _score_candidate(vals: dict, game_name: str, install_dir: str, appid: str, exe_path: str) -> tuple[int, list[str]]:
    dn = vals.get("DisplayName", "")
    score = 0
    reasons = []
    if game_name and dn:
        s = fuzz.ratio(game_name.lower(), dn.lower())
        score += int(s / 2)
        reasons.append(f"name:{s}")
    install_value = clean_display_path(str(vals.get("InstallLocation", "")))
    if install_dir and norm_path(install_dir) == norm_path(install_value):
        score += 40
        reasons.append("install match")
    uninstall = str(vals.get("UninstallString", ""))
    uninstall_exe = extract_exe_from_command(uninstall)
    if appid and appid in uninstall:
        score += 40
        reasons.append("appid in uninstall")
    display_icon = clean_display_path(str(vals.get("DisplayIcon", "")))
    if exe_path and (norm_path(exe_path) == norm_path(display_icon) or norm_path(exe_path) == norm_path(uninstall_exe)):
        score += 30
        reasons.append("exe path match")
    return score, reasons


def scan_registry(game_name: str = "", install_dir: str = "", appid: str = "", exe_path: str = "", logger=None, log_all_candidates: bool = False):
    out = []
    skipped = 0
    for root, sub in UNINSTALL_ROOTS:
        root_name = readable_key(root, sub)
        if logger:
            logger.debug("Registry", f"Scan root: {root_name}")
        try:
            with winreg.OpenKey(root, sub) as base:
                i = 0
                read_count = 0
                while True:
                    try:
                        name = winreg.EnumKey(base, i)
                        i += 1
                    except OSError:
                        break
                    path = f"{sub}\\{name}"
                    try:
                        with winreg.OpenKey(root, path) as k:
                            vals = _read_values(k)
                        read_count += 1
                    except OSError as exc:
                        skipped += 1
                        if logger:
                            logger.debug("Registry", f"Skip registry key: {readable_key(root, path)}, reason={exc}")
                        continue
                    score, reasons = _score_candidate(vals, game_name, install_dir, appid, exe_path)
                    if score > 0:
                        out.append(RegistryCandidate(key=readable_key(root, path), values=vals, score=score, reasons=reasons))
                if logger:
                    logger.debug("Registry", f"Read registry entries: {read_count} under {root_name}")
        except OSError as exc:
            if logger:
                logger.debug("Registry", f"Skip registry root: {root_name}, reason={exc}")
            continue
    result = sorted(out, key=lambda x: x.score, reverse=True)
    if logger:
        logger.info("Registry", f"Found registry candidate count: {len(result)}")
        logger.debug("Registry", f"Skipped registry entries count: {skipped}")
        low_hidden = 0
        for idx, c in enumerate(result):
            should_log = log_all_candidates or idx < 20 or c.score >= 50
            if should_log:
                vals = c.values
                logger.debug("Registry", f"Candidate rank={idx + 1}: {c.key}, DisplayName={vals.get('DisplayName','')}, InstallLocation={vals.get('InstallLocation','')}, Publisher={vals.get('Publisher','')}, DisplayIcon={vals.get('DisplayIcon','')}, UninstallString={vals.get('UninstallString','')}, score={c.score}, reasons={c.reasons}")
            else:
                low_hidden += 1
        if low_hidden:
            logger.debug("Registry", f"Low-score registry candidates not logged: {low_hidden}; enable log-all registry candidates to print them")
        if result:
            logger.info("Registry", f"Recommended DisplayName: {result[0].values.get('DisplayName','')}")
            logger.debug("Registry", f"Final registry key: {result[0].key}, score={result[0].score}, reasons={result[0].reasons}")
    return result
