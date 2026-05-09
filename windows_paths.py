from __future__ import annotations

import os
import re


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
