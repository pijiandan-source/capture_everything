from __future__ import annotations

import win32api
from models import ExeInfo
from signature_analyzer import apply_signature


def _metadata_text(value) -> str:
    return "" if value is None else str(value)


def _winerror(exc: BaseException) -> int | None:
    value = getattr(exc, "winerror", None)
    if value is not None:
        return value
    if getattr(exc, "args", None) and isinstance(exc.args[0], int):
        return exc.args[0]
    return None


def read_exe_info(path: str, logger=None) -> ExeInfo:
    info = ExeInfo()
    try:
        data = win32api.GetFileVersionInfo(path, "\\")
        lang, codepage = win32api.GetFileVersionInfo(path, "\\VarFileInfo\\Translation")[0]
        base = f"\\StringFileInfo\\{lang:04X}{codepage:04X}\\"
        for k, attr in {
            "CompanyName": "company_name",
            "ProductName": "product_name",
            "FileDescription": "file_description",
            "FileVersion": "file_version",
            "ProductVersion": "product_version",
            "OriginalFilename": "original_filename",
            "InternalName": "internal_name",
            "LegalCopyright": "legal_copyright",
        }.items():
            try:
                value = _metadata_text(win32api.GetFileVersionInfo(path, base + k))
                setattr(info, attr, value)
                if logger:
                    logger.debug("ExeAnalyzer", f"{path} {k}={value}")
            except Exception:
                pass
    except Exception as exc:
        if logger:
            if _winerror(exc) == 1813:
                logger.warning("ExeAnalyzer", f"Version info not found: {path}")
                logger.debug("ExeAnalyzer", f"Version info resource missing winerror=1813 path={path}")
            else:
                logger.exception("ExeAnalyzer", f"Failed to read version info: {path}", exc)
    apply_signature(info, path, logger)
    return info
