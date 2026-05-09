from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from utils import norm_path


UUID_RE = re.compile(r"^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$")
STEAM64_RE = re.compile(r"^7656119\d{10}$")
NUM_RE = re.compile(r"^\d+$")
USER_HINTS = {"savegames", "savegame", "saves", "profiles", "profile", "userdata", "users", "remote"}


@dataclass
class PathConvertContext:
    steam_install: str = ""
    game_install: str = ""
    platform_install: str = ""
    steam_appid: str = ""


@dataclass
class PathConvertResult:
    source: str
    output: str
    reasons: list[str] = field(default_factory=list)
    error: str = ""


def normalize_input_path(path: str) -> str:
    p = os.path.expandvars((path or "").strip().strip('"').strip("'"))
    p = p.replace("\\", "/")
    while "//" in p and not re.match(r"^[a-zA-Z]+://", p):
        p = p.replace("//", "/")
    if len(p) > 1:
        p = p.rstrip("/")
    return p


def _join(base: str, rest: str) -> str:
    rest = rest.replace("\\", "/").strip("/")
    return base if not rest else f"{base}/{rest}"


def _rel_if_under(path: str, base: str) -> str | None:
    if not base:
        return None
    pn = norm_path(path)
    bn = norm_path(base)
    if pn == bn:
        return ""
    prefix = bn + os.sep
    if pn.startswith(prefix):
        return os.path.relpath(path, base).replace("\\", "/")
    return None


def _replace_user_segments(parts: list[str], steam_appid: str, reasons: list[str]) -> list[str]:
    out = []
    for i, part in enumerate(parts):
        prev = parts[i - 1].lower() if i else ""
        if STEAM64_RE.match(part):
            out.append("{64BitSteamID}")
            reasons.append(f"segment {part} -> {{64BitSteamID}}")
        elif UUID_RE.match(part):
            out.append("regexuser_^[a-zA-Z0-9_-]{36}$_regexuser")
            reasons.append(f"segment {part} -> UUID regexuser")
        elif NUM_RE.match(part) and part != steam_appid and (prev in USER_HINTS or "save" in prev or "profile" in prev):
            out.append("{Steam3AccountID}")
            reasons.append(f"segment {part} -> {{Steam3AccountID}} by context {prev}")
        else:
            out.append(part)
    return out


def _post_process(output: str, ctx: PathConvertContext, reasons: list[str]) -> str:
    parts = output.split("/")
    if len(parts) >= 3 and parts[0] in {"[Steam Install]", "[Platform Install]"} and parts[1].lower() == "userdata":
        if NUM_RE.match(parts[2]) and parts[2] != ctx.steam_appid:
            reasons.append(f"Steam userdata account {parts[2]} -> {{Steam3AccountID}}")
            parts[2] = "{Steam3AccountID}"
    parts = _replace_user_segments(parts, ctx.steam_appid, reasons)
    return "/".join(parts)


def convert_path(path: str, ctx: PathConvertContext, logger=None) -> PathConvertResult:
    source = path
    normalized = normalize_input_path(path)
    reasons = [f"normalized={normalized}"]
    if logger:
        logger.debug("PathWildcard", f"Input path: {source}")
        logger.debug("PathWildcard", f"Normalized path: {normalized}")

    if not normalized:
        return PathConvertResult(source=source, output="", reasons=reasons, error="empty path")

    candidates = [
        ("[Game Install]", ctx.game_install, "game install"),
        ("[Steam Install]", ctx.steam_install, "steam install"),
        ("[Platform Install]", ctx.platform_install or ctx.steam_install, "platform install"),
        ("%APPDATA%", os.environ.get("APPDATA", ""), "APPDATA"),
        ("%LOCALAPPDATA%", os.environ.get("LOCALAPPDATA", ""), "LOCALAPPDATA"),
        ("%USERPROFILE%", os.environ.get("USERPROFILE", ""), "USERPROFILE"),
    ]
    for token, base, label in candidates:
        rel = _rel_if_under(normalized, normalize_input_path(base)) if base else None
        if rel is not None:
            reasons.append(f"matched {label}: {base}")
            output = _post_process(_join(token, rel), ctx, reasons)
            if logger:
                logger.debug("PathWildcard", f"Output path: {output}; reasons={reasons}")
            return PathConvertResult(source=source, output=output, reasons=reasons)

    parts = normalized.split("/")
    output = "/".join(_replace_user_segments(parts, ctx.steam_appid, reasons))
    if output == normalized:
        reasons.append("no base wildcard matched")
    if logger:
        logger.debug("PathWildcard", f"Output path: {output}; reasons={reasons}")
    return PathConvertResult(source=source, output=output, reasons=reasons)


def convert_multiline(text: str, ctx: PathConvertContext, logger=None) -> list[PathConvertResult]:
    results = []
    for line in (text or "").splitlines():
        if not line.strip():
            results.append(PathConvertResult(source=line, output="", reasons=["blank line"]))
            continue
        results.append(convert_path(line, ctx, logger))
    return results
