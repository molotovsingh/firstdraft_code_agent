from __future__ import annotations

"""
Lightweight helpers to screen out clearly non-document file types during upload.

Block 0 only needs PDFs and images; we may still allow common office docs and
email containers at the API layer. Executables, installers, disk/VM images, and
mobile/desktop app bundles are nearly never part of litigation document review
and should be denied early.

This module implements a simple denylist with optional environment overrides.
It intentionally avoids heavy content-sniffing deps; we rely on filename
extensions and (optionally) a provided MIME string. Finalize should still
perform business validation as needed.
"""

from typing import Optional, Tuple, Set
import os
import re


_DEFAULT_DENY_EXTS = {
    # Desktop/mobile executables & installers
    "exe", "msi", "msp", "app", "apk", "ipa", "bat", "cmd", "ps1", "sh",
    # Shared libraries & binary blobs
    "dll", "sys", "so", "dylib", "bin", "com", "class", "jar",
    # Disk/VM images and packages
    "dmg", "iso", "img", "vmdk", "vhd", "vhdx", "vdi", "qcow2", "ova", "ovf",
    # Other non-doc artefacts
    "torrent",
}

_DEFAULT_DENY_MIMES = {
    # Executables / installers / scripts
    "application/x-msdownload",  # .exe
    "application/x-msi",         # .msi
    "application/x-executable",  # ELF / Mach-O
    "application/x-sh",          # shell script
    # Disk images
    "application/x-apple-diskimage",  # .dmg
    "application/x-iso9660-image",    # .iso
    # Java
    "application/java-archive",  # .jar
}


def _env_set(name: str, defaults: Set[str]) -> Set[str]:
    val = os.getenv(name)
    if not val:
        return set(defaults)
    parts = [p.strip().lower() for p in val.split(",") if p.strip()]
    return set(parts)


def _clean_filename_ext(filename: str) -> str:
    """Return the lowercase extension without dot. Handles our temp 8-hex suffix
    used at presign time (e.g., "file.pdf.ab12cd34" -> "pdf").
    """
    name = filename or ""
    # Strip trailing .<8 hex> if present
    m = re.match(r"^(.+)\.([0-9a-f]{8})$", name.lower())
    if m:
        name = m.group(1)
    # Plain extension
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower()


def deny_reason_for(filename: str, mime: Optional[str] = None) -> Tuple[bool, str]:
    """Return (deny, reason). Does not raise.

    Denies when the file extension or provided MIME matches configured denylists.
    Set env UPLOAD_DENYLIST_EXTS / UPLOAD_DENYLIST_MIMES to override defaults.
    """
    exts = _env_set("UPLOAD_DENYLIST_EXTS", _DEFAULT_DENY_EXTS)
    mimes = _env_set("UPLOAD_DENYLIST_MIMES", _DEFAULT_DENY_MIMES)

    ext = _clean_filename_ext(filename)
    if ext and ext in exts:
        return True, f"extension '.{ext}' is not allowed for upload"

    m = (mime or "").lower().strip()
    if m and m in mimes:
        return True, f"mime '{m}' is not allowed for upload"

    return False, ""

