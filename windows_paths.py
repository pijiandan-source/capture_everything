from __future__ import annotations

import os
import re


REGISTRY_PREFIX_REPLACEMENTS = {
    "HKLM\\": "HKEY_LOCAL_MACHINE\\",
    "HKCU\\": "HKEY_CURRENT_USER\\",
    "18446744071562067970\\": "HKEY_LOCAL_MACHINE\\",
    "18446744071562067969\\": "HKEY_CURRENT_USER\\",
}

KNOWN_REGISTRY_ROOTS = [
    "HKEY_LOCAL_MACHINE\\",
    "HKEY_CURRENT_USER\\",
    "HKEY_CLASSES_ROOT\\",
    "HKEY_USERS\\",
    "HKEY_CURRENT_CONFIG\\",
]


def strip_icon_index(value: str) -> str:
    p = (value or "").strip()
    if not p:
        return ""
    if p.startswith('"'):
        end = p.find('"', 1)
        if end != -1:
            return p[1:end]
    if "," in p and re.search(r",\s*-?\d+\s*$", p):
        p = p.rsplit(",", 1)[0].strip()
    return p.strip('"')


def extract_exe_from_command(value: str) -> str:
    p = (value or "").strip()
    if not p:
        return ""
    if p.startswith('"'):
        end = p.find('"', 1)
        if end != -1:
            return p[1:end]
    m = re.search(r"(?i)^(.+?\.exe)\b", p)
    if m:
        return m.group(1).strip().strip('"')
    return strip_icon_index(p)


def clean_display_path(value: str) -> str:
    p = strip_icon_index(value)
    if not p:
        return ""
    if ".exe" in p.lower():
        p = extract_exe_from_command(p)
    return os.path.expandvars(p.strip().strip('"'))


def normalize_registry_path(path: str, logger=None) -> str:
    if not path:
        return ""

    original = path
    p = path.strip().strip('"').strip("'")
    if p.lower().startswith("computer\\"):
        p = p[len("computer\\"):]

    lower_p = p.lower()
    for prefix, replacement in REGISTRY_PREFIX_REPLACEMENTS.items():
        if lower_p.startswith(prefix.lower()):
            normalized = replacement + p[len(prefix):]
            if logger:
                logger.debug("RegistryPath", f"normalized registry path: raw={original}, normalized={normalized}")
            return normalized

    for root in KNOWN_REGISTRY_ROOTS:
        if lower_p.startswith(root.lower()):
            return p

    if logger:
        logger.debug("RegistryPath", f"unknown registry path format; using original path: {original}")
    return p
