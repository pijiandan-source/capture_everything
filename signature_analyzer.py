from __future__ import annotations

import json
import os
import subprocess

from models import ExeInfo

STATUS_UNKNOWN = "\u672a\u77e5"
STATUS_SIGNED = "\u5df2\u7b7e\u540d"
STATUS_UNSIGNED = "\u672a\u7b7e\u540d"
STATUS_FAILED = "\u8bfb\u53d6\u5931\u8d25"


def _subject_name(raw: str) -> str:
    if not raw:
        return ""
    parts = [p.strip() for p in raw.split(",")]
    for p in parts:
        if p.startswith("CN="):
            return p[3:].strip()
    return raw.strip()


def analyze_signature(path: str, logger=None) -> dict[str, str]:
    result = {
        "status": STATUS_UNKNOWN,
        "subject": STATUS_UNKNOWN,
        "issuer": STATUS_UNKNOWN,
        "error": "",
    }
    if os.name != "nt":
        result["error"] = "Authenticode signature detection is only available on Windows."
        if logger:
            logger.debug("Signature", f"Skip signature detection for non-Windows path: {path}")
        return result

    script = (
        "$sig = Get-AuthenticodeSignature -LiteralPath $args[0]; "
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
        "[pscustomobject]@{"
        "Status=[string]$sig.Status;"
        "Subject=[string]$sig.SignerCertificate.Subject;"
        "Issuer=[string]$sig.SignerCertificate.Issuer;"
        "StatusMessage=[string]$sig.StatusMessage"
        "} | ConvertTo-Json -Compress"
    )
    try:
        cp = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script, path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=12,
        )
        if cp.returncode != 0:
            result["status"] = STATUS_FAILED
            result["error"] = (cp.stderr or cp.stdout or "").strip()
            if logger:
                logger.debug("Signature", f"Signature read failed: {path}, error={result['error']}")
            return result
        data = json.loads(cp.stdout.strip() or "{}")
        status = data.get("Status", "")
        if status == "Valid":
            result["status"] = STATUS_SIGNED
            result["subject"] = _subject_name(data.get("Subject", "")) or STATUS_UNKNOWN
            result["issuer"] = _subject_name(data.get("Issuer", "")) or STATUS_UNKNOWN
        elif status == "NotSigned":
            result["status"] = STATUS_UNSIGNED
            result["error"] = data.get("StatusMessage", "")
        elif status:
            result["status"] = STATUS_FAILED
            result["error"] = data.get("StatusMessage", "") or status
        if logger:
            logger.debug(
                "Signature",
                f"Signature result: {path}, status={result['status']}, subject={result['subject']}, issuer={result['issuer']}, error={result['error']}",
            )
    except Exception as exc:
        result["status"] = STATUS_FAILED
        result["error"] = repr(exc)
        if logger:
            logger.exception("Signature", f"Signature read exception: {path}", exc)
    return result


def apply_signature(info: ExeInfo, path: str, logger=None) -> ExeInfo:
    sig = analyze_signature(path, logger)
    info.digital_signature_status = sig["status"]
    info.digital_signature_subject = sig["subject"]
    info.digital_signature_issuer = sig["issuer"]
    info.digital_signature_error = sig["error"]
    return info
