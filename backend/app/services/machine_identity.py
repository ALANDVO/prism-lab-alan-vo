"""Machine identity derivation with OEM fallback.

Primary: SMBIOS UUID + board/BIOS serial (from /sys/class/dmi/id/ on Linux)
Fallback: Windows MachineGuid registry (reg query) — graceful fallback on non-Windows
License validation works on OEM machines when primary identity is unavailable.
"""

import logging
import platform
import re
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MachineIdentity:
    """Derived machine identity components."""
    smbios_uuid: Optional[str] = None
    board_vendor: Optional[str] = None
    board_name: Optional[str] = None
    board_serial: Optional[str] = None
    bios_vendor: Optional[str] = None
    bios_version: Optional[str] = None
    bios_date: Optional[str] = None
    machine_guid: Optional[str] = None  # Windows fallback
    uses_fallback: bool = False
    warning_issued: bool = False


def _read_dmi(path: str) -> Optional[str]:
    """Read a value from /sys/class/dmi/id/.

    Returns the stripped content or None on failure/permission denied.
    """
    import subprocess
    result = subprocess.run(
        ["cat", path],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    if not value:
        return None
    return value


def _derive_from_dmi() -> MachineIdentity:
    """Derive identity from Linux SMBIOS /sys interface.

    Reads from /sys/class/dmi/id/ which is the modern Linux
    interface to DMI/SMBIOS tables without requiring root/dmidecode.
    """
    identity = MachineIdentity()

    # product UUID
    uuid = _read_dmi("/sys/class/dmi/id/product_uuid")
    if uuid:
        identity.smbios_uuid = uuid

    # board vendor/name/serial
    board_vendor = _read_dmi("/sys/class/dmi/id/board_vendor")
    if board_vendor:
        identity.board_vendor = board_vendor

    board_name = _read_dmi("/sys/class/dmi/id/board_name")
    if board_name:
        identity.board_name = board_name

    board_serial = _read_dmi("/sys/class/dmi/id/board_serial")
    if board_serial:
        identity.board_serial = board_serial

    # BIOS info
    bios_vendor = _read_dmi("/sys/class/dmi/id/bios_vendor")
    if bios_vendor:
        identity.bios_vendor = bios_vendor

    bios_version = _read_dmi("/sys/class/dmi/id/bios_version")
    if bios_version:
        identity.bios_version = bios_version

    bios_date = _read_dmi("/sys/class/dmi/id/bios_date")
    if bios_date:
        identity.bios_date = bios_date

    return identity


def _derive_windows_machine_guid() -> Optional[str]:
    """Attempt to derive Windows MachineGuid.

    On non-Windows platforms this returns None gracefully.
    On Windows, attempts reg query under HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Setup.
    """
    if platform.system() != "Windows":
        return None

    import subprocess
    try:
        result = subprocess.run(
            ["reg", "query", "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Setup", "/v", "MachineGuid"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        output = result.stdout
        match = re.search(r"MachineGuid\s+REG_SZ\s+(.+)", output)
        if match:
            guid = match.group(1).strip()
            if re.match(r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", guid):
                return guid
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    return None


def derive_machine_identity() -> MachineIdentity:
    """Derive the best available machine identity.

    Strategy:
    1. Primary: SMBIOS UUID + board/BIOS serial from /sys/class/dmi/id/ (Linux)
    2. Fallback: Windows MachineGuid registry (Windows)
    3. If neither is available, issue a warning and return identity with
       available fields — license validation will use available metadata
       and fall back gracefully.

    Returns:
        MachineIdentity dataclass with derived values.
        uses_fallback is True if Windows MachineGuid was used.
        warning_issued is True if no identity could be derived at all.
    """
    identity = _derive_from_dmi()

    # Fallback to Windows MachineGuid if primary is insufficient
    machine_guid = _derive_windows_machine_guid()
    if machine_guid:
        identity.machine_guid = machine_guid
        identity.uses_fallback = True

    # Issue warning if we have essentially no identity
    has_primary = any(
        [
            identity.smbios_uuid,
            identity.board_vendor,
            identity.board_name,
            identity.board_serial,
            identity.bios_vendor,
            identity.bios_version,
            identity.bios_date,
        ]
    )

    if not has_primary and not identity.machine_guid:
        identity.warning_issued = True
        logger.warning(
            "No machine identity could be derived from SMBIOS or Windows "
            "Registry. License validation will use available metadata only. "
            "This is expected in containerized/virtualized environments."
        )

    return identity


def machine_identity_summary(identity: MachineIdentity) -> str:
    """Produce a human-readable summary of the machine identity.

    Used for logging and diagnostic output.
    """
    parts = []

    if identity.smbios_uuid:
        parts.append(f"UUID:{identity.smbios_uuid}")
    if identity.board_vendor:
        parts.append(f"BoardV:{identity.board_vendor}")
    if identity.board_name:
        parts.append(f"BoardN:{identity.board_name}")
    if identity.board_serial:
        parts.append(f"BoardS:{identity.board_serial}")
    if identity.bios_vendor:
        parts.append(f"BiosV:{identity.bios_vendor}")
    if identity.bios_version:
        parts.append(f"BiosVer:{identity.bios_version}")
    if identity.bios_date:
        parts.append(f"BiosDt:{identity.bios_date}")
    if identity.machine_guid:
        parts.append(f"MG:{identity.machine_guid}")
    if identity.uses_fallback:
        parts.append("[fallback]")
    if identity.warning_issued:
        parts.append("[warning]")

    return " | ".join(parts) if parts else "[no identity data]"
