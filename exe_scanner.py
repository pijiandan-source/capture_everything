from __future__ import annotations

from pathlib import Path

from exe_analyzer import read_exe_info
from models import ExeCandidate
from utils import norm_text


def scan_exes(root: str, game_name: str = "", max_depth: int = 3, logger=None) -> list[ExeCandidate]:
    out = []
    rootp = Path(root)
    if logger:
        logger.info("Scanner", f"Scan folder: {root}")
    for p in rootp.rglob("*.exe"):
        rel = p.relative_to(rootp)
        if len(rel.parts) > max_depth + 1:
            if logger:
                logger.debug("ExeScanner", f"Skip folder/file: {p}, reason=depth>{max_depth}")
            continue
        name = p.name.lower()
        if any(x in name for x in ["unins", "uninstall", "crash", "vcredist", "dxsetup"]):
            if logger:
                logger.debug("ExeScanner", f"Skip exe: {p}, reason=excluded name")
            continue
        score = 10
        reasons = ["base"]
        if norm_text(game_name) and norm_text(game_name) in norm_text(name):
            score += 30
            reasons.append("name match")
        if p.parent == rootp:
            score += 20
            reasons.append("root dir")
        size = p.stat().st_size
        score += min(int(size / (1024 * 1024)), 30)
        info = read_exe_info(str(p), logger)
        if logger:
            logger.debug("ExeScanner", f"Candidate: {p}, size={size}, rel={rel}, score={score}, reasons={reasons}, signature={info.digital_signature_status}/{info.digital_signature_subject}")
        out.append(ExeCandidate(path=str(p), score=score, reasons=reasons, exe_info=info, size=size, relative_path=str(rel)))
    result = sorted(out, key=lambda x: x.score, reverse=True)
    if logger:
        logger.info("Scanner", f"Found exe count: {len(result)}")
        if result:
            logger.info("Scanner", f"Recommended main exe: {result[0].path}")
            logger.debug("ExeScanner", f"Final main exe reason: score={result[0].score}, reasons={result[0].reasons}")
    return result
