from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from models import ExeInfo

STATUS_UNKNOWN = "\u672a\u77e5"
STATUS_SIGNED = "\u5df2\u7b7e\u540d"
STATUS_UNSIGNED = "\u672a\u7b7e\u540d"
STATUS_FAILED = "\u7b7e\u540d\u8bfb\u53d6\u5931\u8d25"
STATUS_HASH_MISMATCH = "\u7b7e\u540d\u54c8\u5e0c\u4e0d\u5339\u914d"
STATUS_NOT_TRUSTED = "\u7b7e\u540d\u4e0d\u53d7\u4fe1\u4efb"
STATUS_EXCEPTION = "\u7b7e\u540d\u8bfb\u53d6\u5f02\u5e38"

STATUS_MAP = {
    "Valid": STATUS_SIGNED,
    "NotSigned": STATUS_UNSIGNED,
    "HashMismatch": STATUS_HASH_MISMATCH,
    "NotTrusted": STATUS_NOT_TRUSTED,
    "UnknownError": STATUS_EXCEPTION,
}


PS_SCRIPT = r"""
param([Parameter(Mandatory=$true)][string]$Path)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$sig = Get-AuthenticodeSignature -LiteralPath $Path
[pscustomobject]@{
  Status = [string]$sig.Status
  Subject = [string]$sig.SignerCertificate.Subject
  Issuer = [string]$sig.SignerCertificate.Issuer
  StatusMessage = [string]$sig.StatusMessage
} | ConvertTo-Json -Compress
"""


def _subject_name(raw: str) -> str:
    if not raw:
        return ""
    parts = [p.strip() for p in raw.split(",")]
    for p in parts:
        if p.startswith("CN="):
            return p[3:].strip()
    return raw.strip()


def _run_signature_script(path: str, logger=None) -> subprocess.CompletedProcess[str]:
    ps1 = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8") as f:
            f.write(PS_SCRIPT)
            ps1 = f.name
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1, "-Path", path]
        if logger:
            logger.debug("Signature", f"External command args={cmd} shell=False")
        cp = subprocess.run(cmd, shell=False, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        if logger:
            logger.debug("Signature", f"External command returncode={cp.returncode}")
            logger.debug("Signature", f"External command stdout={cp.stdout.strip()}")
            logger.debug("Signature", f"External command stderr={cp.stderr.strip()}")
        return cp
    finally:
        if ps1:
            try:
                Path(ps1).unlink(missing_ok=True)
            except Exception as exc:
                if logger:
                    logger.debug("Signature", f"Failed to delete temp ps1={ps1}, error={exc}")


def analyze_signature(path: str, logger=None) -> dict[str, str]:
    result = {
        "status": STATUS_UNKNOWN,
        "subject": "",
        "issuer": "",
        "raw_status": "",
        "status_message": "",
        "error": "",
    }
    exists = os.path.exists(path)
    if logger:
        logger.debug("Signature", f"Analyze signature path={path} exists={exists}")
    if os.name != "nt":
        result["error"] = "Authenticode signature detection is only available on Windows."
        if logger:
            logger.debug("Signature", f"Skip signature detection for non-Windows path: {path}")
        return result
    if not exists:
        result["status"] = STATUS_FAILED
        result["error"] = "Path does not exist."
        result["status_message"] = result["error"]
        return result

    try:
        cp = _run_signature_script(path, logger)
        if cp.returncode != 0:
            result["status"] = STATUS_FAILED
            result["error"] = (cp.stderr or cp.stdout or "").strip()
            result["status_message"] = result["error"]
            return result
        data = json.loads(cp.stdout.strip() or "{}")
        status = data.get("Status", "")
        status_message = data.get("StatusMessage", "") or ""
        result["raw_status"] = status
        result["status_message"] = status_message
        result["status"] = STATUS_MAP.get(status, STATUS_UNKNOWN)
        if status == "Valid":
            result["subject"] = _subject_name(data.get("Subject", ""))
            result["issuer"] = _subject_name(data.get("Issuer", ""))
        elif status in STATUS_MAP:
            result["subject"] = _subject_name(data.get("Subject", ""))
            result["issuer"] = _subject_name(data.get("Issuer", ""))
        elif status:
            result["error"] = status_message or status
        if logger:
            logger.debug("Signature", f"Signature result: path={path}, status={result['status']}, raw_status={result['raw_status']}, subject={result['subject']}, issuer={result['issuer']}, status_message={result['status_message']}, error={result['error']}")
    except Exception as exc:
        result["status"] = STATUS_FAILED
        result["error"] = repr(exc)
        result["status_message"] = result["error"]
        if logger:
            logger.exception("Signature", f"Signature read exception: {path}", exc)
    return result


def apply_signature(info: ExeInfo, path: str, logger=None) -> ExeInfo:
    sig = analyze_signature(path, logger)
    info.digital_signature_status = sig["status"]
    info.digital_signature_subject = sig["subject"]
    info.digital_signature_issuer = sig["issuer"]
    info.digital_signature_raw_status = sig["raw_status"]
    info.digital_signature_status_message = sig["status_message"]
    info.digital_signature_error = sig["error"]
    return info
