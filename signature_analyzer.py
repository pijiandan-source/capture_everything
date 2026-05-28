from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from models import ExeInfo
from process_utils import resolve_powershell_exe, run_command_hidden

STATUS_UNKNOWN = "\u672a\u77e5"
STATUS_SIGNED = "\u5df2\u7b7e\u540d"
STATUS_UNSIGNED = "\u672a\u7b7e\u540d"
STATUS_FAILED = "\u7b7e\u540d\u8bfb\u53d6\u5931\u8d25"
STATUS_HASH_MISMATCH = "\u7b7e\u540d\u54c8\u5e0c\u4e0d\u5339\u914d"
STATUS_NOT_TRUSTED = "\u7b7e\u540d\u4e0d\u53d7\u4fe1\u4efb"
STATUS_EXCEPTION = "\u7b7e\u540d\u8bfb\u53d6\u5f02\u5e38"
STATUS_TOOL_UNAVAILABLE = "\u7b7e\u540d\u5de5\u5177\u4e0d\u53ef\u7528"

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
$cert = $sig.SignerCertificate
[pscustomobject]@{
  Status = [string]$sig.Status
  StatusMessage = [string]$sig.StatusMessage
  SubjectRaw = if ($cert) { [string]$cert.Subject } else { "" }
  IssuerRaw = if ($cert) { [string]$cert.Issuer } else { "" }
  SubjectSimple = if ($cert) { [string]$cert.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName, $false) } else { "" }
  IssuerSimple = if ($cert) { [string]$cert.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName, $true) } else { "" }
} | ConvertTo-Json -Compress
"""


def _run_signature_script(path: str, logger=None):
    ps1 = None
    powershell_exe = resolve_powershell_exe(logger)
    if not powershell_exe:
        if logger:
            logger.error("Signature", "PowerShell executable not found")
            logger.error("Signature", f"target_path={path}")
            logger.error("Signature", f"target_exists={os.path.exists(path)}")
            logger.error("Signature", f"PATH={os.environ.get('PATH', '')}")
        return None
    if logger:
        logger.debug("Signature", f"Using PowerShell executable: {powershell_exe}")
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8") as f:
            f.write(PS_SCRIPT)
            ps1 = f.name
        cmd = [powershell_exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1, "-Path", path]
        try:
            return run_command_hidden(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15, logger=logger, module="Signature")
        except FileNotFoundError as exc:
            if logger:
                logger.error("Signature", "PowerShell command not found while reading signature")
                logger.error("Signature", f"command={cmd[0]}")
                logger.error("Signature", f"target_path={path}")
                logger.error("Signature", f"target_exists={os.path.exists(path)}")
                logger.error("Signature", f"cwd={os.getcwd()}")
                logger.error("Signature", f"PATH={os.environ.get('PATH', '')}")
                logger.exception("Signature", "PowerShell FileNotFoundError", exc)
            raise
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
        "subject_raw": "",
        "issuer_raw": "",
        "subject_simple": "",
        "issuer_simple": "",
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
        if cp is None:
            result["status"] = STATUS_TOOL_UNAVAILABLE
            result["raw_status"] = "ToolNotFound"
            result["error"] = "PowerShell executable not found."
            result["status_message"] = result["error"]
            return result
        if cp.returncode != 0:
            result["status"] = STATUS_FAILED
            result["error"] = (cp.stderr or cp.stdout or "").strip()
            result["status_message"] = result["error"]
            return result
        try:
            data = json.loads(cp.stdout.strip() or "{}")
        except json.JSONDecodeError as exc:
            result["status"] = STATUS_FAILED
            result["raw_status"] = "ParseError"
            result["error"] = f"Signature result parse failed: {exc}"
            result["status_message"] = result["error"]
            if logger:
                logger.exception("Signature", f"Signature JSON parse failed: path={path}, stdout={cp.stdout!r}", exc)
            return result
        status = data.get("Status", "")
        status_message = data.get("StatusMessage", "") or ""
        result["raw_status"] = status
        result["status_message"] = status_message
        result["status"] = STATUS_MAP.get(status, STATUS_UNKNOWN)
        result["subject_raw"] = data.get("SubjectRaw", "") or ""
        result["issuer_raw"] = data.get("IssuerRaw", "") or ""
        result["subject_simple"] = data.get("SubjectSimple", "") or ""
        result["issuer_simple"] = data.get("IssuerSimple", "") or ""
        result["subject"] = result["subject_simple"] or result["subject_raw"]
        result["issuer"] = result["issuer_simple"] or result["issuer_raw"]
        if status and status not in STATUS_MAP:
            result["error"] = status_message or status
        if logger:
            logger.debug("Signature", f"Signature result: path={path}, status={result['status']}, raw_status={result['raw_status']}, subject_simple={result['subject_simple']}, issuer_simple={result['issuer_simple']}, subject_raw={result['subject_raw']}, issuer_raw={result['issuer_raw']}, status_message={result['status_message']}, error={result['error']}")
    except FileNotFoundError as exc:
        result["status"] = STATUS_TOOL_UNAVAILABLE
        result["raw_status"] = "CommandNotFound"
        result["error"] = f"Signature command not found: {exc.filename or exc}"
        result["status_message"] = result["error"]
        if logger:
            logger.error("Signature", "Signature command missing; target exe is not the missing file")
            logger.error("Signature", f"target_path={path}")
            logger.error("Signature", f"target_exists={os.path.exists(path)}")
            logger.error("Signature", f"PATH={os.environ.get('PATH', '')}")
            logger.exception("Signature", f"Signature command FileNotFoundError: {path}", exc)
    except subprocess.TimeoutExpired as exc:
        result["status"] = STATUS_FAILED
        result["raw_status"] = "Timeout"
        result["error"] = f"Signature read timeout: {exc}"
        result["status_message"] = result["error"]
        if logger:
            logger.exception("Signature", f"Signature read timeout: {path}", exc)
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
    info.digital_signature_subject_raw = sig["subject_raw"]
    info.digital_signature_issuer_raw = sig["issuer_raw"]
    info.digital_signature_subject_simple = sig["subject_simple"]
    info.digital_signature_issuer_simple = sig["issuer_simple"]
    info.digital_signature_raw_status = sig["raw_status"]
    info.digital_signature_status_message = sig["status_message"]
    info.digital_signature_error = sig["error"]
    return info
