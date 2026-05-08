from __future__ import annotations

import os
import re


def norm_text(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def norm_path(p: str) -> str:
    if not p:
        return ""
    p = p.strip().strip('"')
    if "," in p and p.lower().endswith(",0"):
        p = p.rsplit(",", 1)[0].strip('"')
    return os.path.normcase(os.path.normpath(p))


def extract_appid(text: str) -> str:
    m = re.search(r"rungameid/(\d+)", text or "")
    if m:
        return m.group(1)
    m = re.search(r"-applaunch\s+(\d+)", text or "", re.I)
    return m.group(1) if m else ""
