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
    }
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
            for section, values in data.items():
                if isinstance(values, dict) and isinstance(settings.get(section), dict):
                    settings[section].update(values)
                else:
                    settings[section] = values
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
