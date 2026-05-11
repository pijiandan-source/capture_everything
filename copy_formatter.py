from __future__ import annotations

import json

from models import GameInfo
from windows_paths import normalize_registry_path


def basic_text(g: GameInfo) -> str:
    return (
        f"Game Name: {g.game_name}\n"
        f"Steam AppID: {g.steam_appid}\n"
        f"Steam URL: {g.steam_url}\n"
        f"Shortcut Type: {g.shortcut_type}\n"
        f"Shortcut Path: {g.shortcut_path}\n"
        f"Shortcut Icon Path: {g.shortcut_icon_path}\n"
        f"Shortcut Icon Index: {g.shortcut_icon_index}\n"
        f"Install Dir: {g.install_dir}\n"
        f"Main EXE: {g.main_exe_path}\n"
        f"Process Name: {g.process_name}"
    )


def exe_text(g: GameInfo) -> str:
    e = g.exe_info
    return (
        f"Main EXE: {g.main_exe_path}\n"
        f"Process Name: {g.process_name}\n"
        f"CompanyName: {e.company_name}\n"
        f"ProductName: {e.product_name}\n"
        f"FileDescription: {e.file_description}\n"
        f"FileVersion: {e.file_version}\n"
        f"ProductVersion: {e.product_version}\n"
        f"OriginalFilename: {e.original_filename}\n"
        f"Digital Signature Status: {e.digital_signature_status}\n"
        f"Digital Signature Subject: {e.digital_signature_subject}\n"
        f"Digital Signature Issuer: {e.digital_signature_issuer}\n"
        f"Digital Signature Subject Simple: {e.digital_signature_subject_simple}\n"
        f"Digital Signature Issuer Simple: {e.digital_signature_issuer_simple}\n"
        f"Digital Signature Subject Raw: {e.digital_signature_subject_raw}\n"
        f"Digital Signature Issuer Raw: {e.digital_signature_issuer_raw}\n"
        f"Digital Signature Raw Status: {e.digital_signature_raw_status}\n"
        f"Digital Signature Status Message: {e.digital_signature_status_message}\n"
        f"Digital Signature Error: {e.digital_signature_error}"
    )


def reg_text(g: GameInfo) -> str:
    r = g.registry
    return (
        f"DisplayName: {r['display_name']}\n"
        f"InstallLocation: {r['install_location']}\n"
        f"Publisher: {r['publisher']}\n"
        f"DisplayIcon: {r['display_icon']}\n"
        f"UninstallString: {r['uninstall_string']}\n"
        f"RegistryKey: {normalize_registry_path(r['key'])}"
    )


def full_text(g: GameInfo) -> str:
    return basic_text(g) + "\n\n" + exe_text(g) + "\n\n" + reg_text(g)


def as_json(g: GameInfo) -> str:
    return json.dumps(g.to_dict(), ensure_ascii=False, indent=2)
