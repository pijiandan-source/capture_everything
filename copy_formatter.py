from __future__ import annotations
import json
from models import GameInfo

def basic_text(g: GameInfo) -> str:
    return f"游戏名称: {g.game_name}\nSteam AppID: {g.steam_appid}\nSteam URL: {g.steam_url}\n安装目录: {g.install_dir}\n主 exe: {g.main_exe_path}\n进程名: {g.process_name}"

def exe_text(g: GameInfo) -> str:
    e = g.exe_info
    return f"主 exe: {g.main_exe_path}\n进程名: {g.process_name}\nCompanyName: {e.company_name}\nProductName: {e.product_name}\nFileDescription: {e.file_description}\nFileVersion: {e.file_version}\nProductVersion: {e.product_version}\nOriginalFilename: {e.original_filename}"

def reg_text(g: GameInfo) -> str:
    r=g.registry
    return f"DisplayName: {r['display_name']}\nInstallLocation: {r['install_location']}\nPublisher: {r['publisher']}\nDisplayIcon: {r['display_icon']}\nUninstallString: {r['uninstall_string']}\nRegistryKey: {r['key']}"

def full_text(g: GameInfo) -> str:
    return basic_text(g)+"\n\n"+exe_text(g)+"\n\n"+reg_text(g)

def as_json(g: GameInfo) -> str:
    return json.dumps(g.to_dict(), ensure_ascii=False, indent=2)
