from __future__ import annotations

from pathlib import Path

from exe_analyzer import read_exe_info
from models import ExeCandidate
from utils import norm_text


def _safe_text(value) -> str:
    return "" if value is None else str(value)


def classify_exe(path: Path, rel: Path, info) -> tuple[str, list[str]]:
    text = " ".join([
        path.name,
        str(rel),
        _safe_text(info.company_name),
        _safe_text(info.product_name),
        _safe_text(info.file_description),
        _safe_text(info.original_filename),
    ]).lower()
    reasons = []
    if any(x in text for x in ["easyanticheat", "eac", "battleye", "anti-cheat", "anticheat"]):
        reasons.append("anti-cheat keyword")
        return "anti-cheat", reasons
    if any(x in text for x in ["webhelper", "cef", "browser", "chrome", "webview"]):
        reasons.append("web helper keyword")
        return "webhelper", reasons
    if any(x in text for x in ["crash", "reporter", "bugreport"]):
        reasons.append("crash reporter keyword")
        return "crash reporter", reasons
    if any(x in text for x in ["launcher", "bootstrapper", "start", "updater"]):
        reasons.append("launcher keyword")
        return "launcher", reasons
    if any(x in text for x in ["setup", "install", "installer", "unins", "uninstall"]):
        reasons.append("installer keyword")
        return "installer", reasons
    if any(x in text for x in ["vcredist", "redist", "directx", "dxsetup", "dotnet", "runtime"]):
        reasons.append("runtime/redist keyword")
        return "runtime/redist", reasons
    if any(x in text for x in ["thirdparty", "third_party", "binaries/thirdparty", "engine/binaries"]):
        reasons.append("third-party path keyword")
        return "third-party component", reasons
    reasons.append("no special category keyword")
    return "unknown", reasons


def score_exe(path: Path, rel: Path, game_name: str, info, size: int, category: str) -> tuple[int, list[str]]:
    score = 10
    reasons = ["base +10"]
    name_norm = norm_text(path.stem)
    game_norm = norm_text(game_name)
    metadata_norm = norm_text(" ".join([_safe_text(info.product_name), _safe_text(info.file_description), _safe_text(info.original_filename)]))
    rel_text = str(rel).replace("\\", "/").lower()

    if game_norm and game_norm in name_norm:
        score += 35
        reasons.append("exe name matches game +35")
    if game_norm and game_norm in metadata_norm:
        score += 45
        reasons.append("version metadata matches game +45")
    if info.product_name:
        score += 15
        reasons.append("has ProductName +15")
    if info.file_description:
        score += 15
        reasons.append("has FileDescription +15")
    if "binaries/win64" in rel_text or "bin/win64" in rel_text or "x64" in rel_text:
        score += 25
        reasons.append("64-bit binaries path +25")
    if len(rel.parts) == 1:
        score += 5
        reasons.append("root exe +5")
    size_mb = int(size / (1024 * 1024))
    size_score = min(size_mb, 80)
    score += size_score
    reasons.append(f"size +{size_score}")

    penalties = {
        "launcher": -35,
        "anti-cheat": -45,
        "webhelper": -45,
        "crash reporter": -50,
        "runtime/redist": -60,
        "installer": -55,
        "third-party component": -35,
    }
    penalty = penalties.get(category, 0)
    if penalty:
        score += penalty
        reasons.append(f"{category} {penalty}")
    return score, reasons


def scan_exes(root: str, game_name: str = "", max_depth: int | None = None, logger=None) -> list[ExeCandidate]:
    out = []
    rootp = Path(root)
    if logger:
        logger.info("Scanner", f"Scan folder: {root}")
        logger.debug("ExeScanner", "No exe is excluded; all discovered exe files are shown.")
    for p in rootp.rglob("*.exe"):
        rel = p.relative_to(rootp)
        if max_depth is not None and len(rel.parts) > max_depth + 1:
            if logger:
                logger.debug("ExeScanner", f"Depth note: {p}, depth>{max_depth}; still included because full exe list is required")
        try:
            size = p.stat().st_size
        except OSError as exc:
            size = 0
            if logger:
                logger.exception("ExeScanner", f"Failed to stat exe: {p}", exc)
        info = read_exe_info(str(p), logger)
        category, category_reasons = classify_exe(p, rel, info)
        score, score_reasons = score_exe(p, rel, game_name, info, size, category)
        reasons = category_reasons + score_reasons
        if logger:
            logger.debug("ExeScanner", f"Candidate: {p}, category={category}, size={size}, rel={rel}, score={score}, reasons={reasons}, signature={info.digital_signature_status}/{info.digital_signature_subject}")
        out.append(ExeCandidate(path=str(p), score=score, reasons=reasons, exe_info=info, size=size, relative_path=str(rel), category=category))
    result = sorted(out, key=lambda x: x.score, reverse=True)
    if logger:
        logger.info("Scanner", f"Found exe count: {len(result)}")
        if result:
            logger.info("Scanner", f"Recommended main exe: {result[0].path}")
            logger.debug("ExeScanner", f"Final main exe reason: score={result[0].score}, category={result[0].category}, reasons={result[0].reasons}")
    return result
