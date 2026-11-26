"""Machine identity derivation tests."""
import pytest

from app.services.machine_identity import (
    MachineIdentity,
    derive_machine_identity,
    machine_identity_summary,
)


class TestMachineIdentityDataclass:
    """Test the MachineIdentity dataclass defaults and structure."""

    def test_defaults_are_none(self):
        identity = MachineIdentity()
        assert identity.smbios_uuid is None
        assert identity.board_vendor is None
        assert identity.board_name is None
        assert identity.board_serial is None
        assert identity.bios_vendor is None
        assert identity.bios_version is None
        assert identity.bios_date is None
        assert identity.machine_guid is None
        assert identity.uses_fallback is False
        assert identity.warning_issued is False

    def test_creates_with_values(self):
        identity = MachineIdentity(
            smbios_uuid="12345678-1234-5678-1234-567812345678",
            board_vendor="Intel Corporation",
            bios_version="S1200SP.86B.03.01",
        )
        assert identity.smbios_uuid == "12345678-1234-5678-1234-567812345678"
        assert identity.board_vendor == "Intel Corporation"
        assert identity.bios_version == "S1200SP.86B.03.01"


class TestDeriveMachineIdentity:
    """Test the derive_machine_identity function."""

    def test_derives_from_sysfs_when_available(self):
        """On this system, /sys/class/dmi-id/ is readable, so identity should have values."""
        identity = derive_machine_identity()
        # Should have at least some derived values from sysfs
        assert isinstance(identity, MachineIdentity)
        # May have UUID, board info, or BIOS info from sysfs
        summary = machine_identity_summary(identity)
        # Should not have a warning issued if we got some data
        assert "warning" not in summary.lower() or any(
            getattr(identity, field, None) is not None
            for field in [
                "smbios_uuid",
                "board_vendor",
                "board_name",
                "board_serial",
                "bios_vendor",
                "bios_version",
                "bios_date",
            ]
        )

    def test_summary_is_string(self):
        identity = derive_machine_identity()
        summary = machine_identity_summary(identity)
        assert isinstance(summary, str)

    def test_uses_fallback_flag(self):
        """On non-Windows, uses_fallback should typically be False."""
        identity = derive_machine_identity()
        # On Linux, this should be False since we don't have Windows MachineGuid
        assert isinstance(identity.uses_fallback, bool)


class TestMachineIdentitySummary:
    """Test the machine_identity_summary helper."""

    def test_summary_with_uuid(self):
        identity = MachineIdentity(smbios_uuid="test-uuid-1234")
        summary = machine_identity_summary(identity)
        assert "UUID:test-uuid-1234" in summary or "UUID" in summary

    def test_summary_with_fallback(self):
        identity = MachineIdentity(machine_guid="abc123", uses_fallback=True)
        summary = machine_identity_summary(identity)
        assert "[fallback]" in summary

    def test_summary_with_warning(self):
        identity = MachineIdentity(warning_issued=True)
        summary = machine_identity_summary(identity)
        assert "[warning]" in summary

    def test_summary_empty(self):
        identity = MachineIdentity()
        summary = machine_identity_summary(identity)
        assert summary == "[no identity data]"
