from __future__ import annotations
import winreg
from rapidfuzz import fuzz
from models import RegistryCandidate
from utils import norm_path

UNINSTALL_ROOTS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]
FIELDS = ["DisplayName","DisplayVersion","Publisher","InstallLocation","InstallSource","DisplayIcon","UninstallString","QuietUninstallString","EstimatedSize","NoModify","NoRepair","URLInfoAbout","HelpLink"]

def _read_values(k):
    d={}
    for f in FIELDS:
        try:d[f]=winreg.QueryValueEx(k,f)[0]
        except OSError:d[f]=""
    return d

def scan_registry(game_name:str="", install_dir:str="", appid:str="", exe_path:str=""):
    out=[]
    for root,sub in UNINSTALL_ROOTS:
        try:
            with winreg.OpenKey(root, sub) as base:
                i=0
                while True:
                    try:name=winreg.EnumKey(base,i); i+=1
                    except OSError: break
                    path=f"{sub}\\{name}"
                    with winreg.OpenKey(root,path) as k:
                        vals=_read_values(k)
                    dn=vals.get("DisplayName","")
                    score=0; reasons=[]
                    if game_name and dn:
                        s=fuzz.ratio(game_name.lower(), dn.lower())
                        score += int(s/2); reasons.append(f"name:{s}")
                    if install_dir and norm_path(install_dir)==norm_path(vals.get("InstallLocation","")):
                        score += 40; reasons.append("install match")
                    if appid and appid in str(vals.get("UninstallString","")):
                        score += 40; reasons.append("appid in uninstall")
                    if exe_path and norm_path(exe_path) in norm_path(str(vals.get("DisplayIcon",""))):
                        score += 30; reasons.append("icon match")
                    if score>0:
                        rk=f"{root}\\{path}"
                        out.append(RegistryCandidate(key=rk, values=vals, score=score, reasons=reasons))
        except OSError:
            continue
    return sorted(out, key=lambda x:x.score, reverse=True)
