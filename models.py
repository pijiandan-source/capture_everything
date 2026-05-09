from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ExeInfo:
    company_name: str = ""
    product_name: str = ""
    file_description: str = ""
    file_version: str = ""
    product_version: str = ""
    original_filename: str = ""
    internal_name: str = ""
    legal_copyright: str = ""
    digital_signature_status: str = "\u672a\u77e5"
    digital_signature_subject: str = "\u672a\u77e5"
    digital_signature_issuer: str = "\u672a\u77e5"
    digital_signature_error: str = ""


@dataclass
class ExeCandidate:
    path: str
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    exe_info: ExeInfo = field(default_factory=ExeInfo)
    size: int = 0
    relative_path: str = ""


@dataclass
class RegistryCandidate:
    key: str
    values: dict[str, Any] = field(default_factory=dict)
    score: int = 0
    reasons: list[str] = field(default_factory=list)


@dataclass
class GameInfo:
    platform: str = "steam"
    steam_appid: str = ""
    steam_url: str = ""
    game_name: str = ""
    install_dir: str = ""
    main_exe_path: str = ""
    process_name: str = ""
    exe_info: ExeInfo = field(default_factory=ExeInfo)
    exe_candidates: list[ExeCandidate] = field(default_factory=list)
    registry_candidates: list[RegistryCandidate] = field(default_factory=list)
    registry: dict[str, str] = field(default_factory=lambda: {
        "display_name": "",
        "install_location": "",
        "publisher": "",
        "display_icon": "",
        "uninstall_string": "",
        "key": "",
    })

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
