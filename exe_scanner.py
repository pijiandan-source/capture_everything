from __future__ import annotations
import os
from pathlib import Path
from models import ExeCandidate
from exe_analyzer import read_exe_info
from utils import norm_text


def scan_exes(root: str, game_name: str = "", max_depth: int = 3) -> list[ExeCandidate]:
    out = []
    rootp = Path(root)
    for p in rootp.rglob("*.exe"):
        rel = p.relative_to(rootp)
        if len(rel.parts) > max_depth + 1:
            continue
        name = p.name.lower()
        if any(x in name for x in ["unins", "uninstall", "crash", "vcredist", "dxsetup"]):
            continue
        score = 10
        reasons = ["base"]
        if norm_text(game_name) and norm_text(game_name) in norm_text(name):
            score += 30; reasons.append("name match")
        if p.parent == rootp:
            score += 20; reasons.append("root dir")
        size = p.stat().st_size
        score += min(int(size / (1024*1024)), 30)
        info = read_exe_info(str(p))
        out.append(ExeCandidate(path=str(p), score=score, reasons=reasons, exe_info=info))
    return sorted(out, key=lambda x: x.score, reverse=True)
