from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path


APP_DIR_NAME = "SteamGameInfoCollector"

DEFAULT_SETTINGS = {
    "basic_visibility": {
        "steam": True,
        "shortcut": True,
        "game_paths": True,
        "main_exe": True,
        "exe_metadata": True,
        "signature": True,
        "registry": True,
    },
    "basic_field_visibility": {
        "game_name": True,
        "steam_appid": True,
        "steam_url": True,
        "shortcut_name": True,
        "shortcut_type": True,
        "shortcut_path": True,
        "shortcut_icon_path": True,
        "shortcut_icon_index": True,
        "install_dir": True,
        "main_exe_path": True,
        "process_name": True,
        "exe_company": True,
        "exe_product": True,
        "exe_desc": True,
        "exe_file_version": True,
        "exe_product_version": True,
        "exe_original": True,
        "exe_internal": True,
        "exe_copyright": True,
        "exe_sig_status": True,
        "exe_sig_subject": True,
        "exe_sig_issuer": True,
        "exe_sig_subject_simple": True,
        "exe_sig_issuer_simple": True,
        "exe_sig_subject_raw": True,
        "exe_sig_issuer_raw": True,
        "exe_sig_raw_status": True,
        "exe_sig_message": True,
        "reg_name": True,
        "reg_install": True,
        "reg_pub": True,
        "reg_icon": True,
        "reg_uninstall": True,
        "reg_key": True,
    },
}


def settings_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / APP_DIR_NAME / "settings.json"


def load_settings(logger=None) -> dict:
    path = settings_path()
    settings = deepcopy(DEFAULT_SETTINGS)
    if not path.exists():
        return settings
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for section, defaults in DEFAULT_SETTINGS.items():
                if isinstance(defaults, dict):
                    current = data.get(section, {})
                    if isinstance(current, dict):
                        settings[section].update(current)
                elif section in data:
                    settings[section] = data[section]
    except Exception as exc:
        if logger:
            logger.warning("Settings", f"Failed to load settings.json, use defaults: {path}, error={exc}")
    return settings


def save_settings(settings: dict, logger=None) -> Path:
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        if logger:
            logger.exception("Settings", f"Failed to save settings.json: {path}", exc)
    return path


def reset_settings(logger=None) -> dict:
    settings = deepcopy(DEFAULT_SETTINGS)
    save_settings(settings, logger)
    return settings
