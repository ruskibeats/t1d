"""Tests for the CGM Bridge Service."""

import pytest
from app.services.cgm_bridge_service import (
    CgmBridgeService,
    CgmSource,
    DexcomAdapter,
    LibreLinkUpAdapter,
    CgmConnectionConfig,
    CgmConnectionResult,
)


@pytest.mark.asyncio
class TestCgmBridgeService:
    async def test_available_sources(self):
        """Should list available CGM sources."""
        service = CgmBridgeService(None)  # session not needed for this
        sources = await service.get_available_sources()
        source_ids = [s["id"] for s in sources]
        assert "dexcom" in source_ids
        assert "librelinkup" in source_ids
        assert "nightscout" in source_ids

    async def test_dexcom_available_first(self):
        """Dexcom should be listed as recommended."""
        sources = await CgmBridgeService(None).get_available_sources()
        dexcom = next(s for s in sources if s["id"] == "dexcom")
        assert dexcom["is_recommended"] is True
        assert dexcom["requires_consent"] is False

    async def test_librelinkup_requires_consent(self):
        """LibreLinkUp should flag that consent is needed."""
        sources = await CgmBridgeService(None).get_available_sources()
        ll = next(s for s in sources if s["id"] == "librelinkup")
        assert ll["requires_consent"] is True

    async def test_connect_unsupported_source(self):
        """Unsupported source should return error."""
        service = CgmBridgeService(None)
        result = await service.connect("invalid_source", 1)  # type: ignore
        assert result.success is False

    async def test_get_connected_sources_none(self):
        """User with no connections should return empty list."""
        class MockUser:
            dexcom_access_token = None
            librelinkup_email = None
            nightscout_url = None

        service = CgmBridgeService(None)
        sources = await service.get_connected_sources(MockUser())
        assert sources == []

    async def test_get_connected_sources_dexcom(self):
        """User with Dexcom should show it as connected."""
        class MockUser:
            dexcom_access_token = "abc"
            librelinkup_email = None
            nightscout_url = None

        service = CgmBridgeService(None)
        sources = await service.get_connected_sources(MockUser())
        assert len(sources) == 1
        assert sources[0]["id"] == "dexcom"
        assert sources[0]["connected"] is True

    async def test_get_connected_sources_all(self):
        """User with all sources connected."""
        class MockUser:
            dexcom_access_token = "abc"
            librelinkup_email = "test@example.com"
            nightscout_url = "https://my-ns.example.com"

        service = CgmBridgeService(None)
        sources = await service.get_connected_sources(MockUser())
        assert len(sources) == 3


class TestDexcomAdapter:
    def test_no_token_fails(self):
        adapter = DexcomAdapter()

        async def run():
            config = CgmConnectionConfig(source=CgmSource.DEXCOM, user_id=1)
            result = await adapter.test_connection(config)
            assert result.success is False
            assert "access token" in result.message.lower()

        import asyncio
        asyncio.run(run())


class TestLibreLinkUpAdapter:
    def test_no_credentials_fails(self):
        adapter = LibreLinkUpAdapter()

        async def run():
            config = CgmConnectionConfig(source=CgmSource.LIBRELINKUP, user_id=1)
            result = await adapter.test_connection(config)
            assert result.success is False

        import asyncio
        asyncio.run(run())


class TestCgmSourceEnum:
    def test_all_sources(self):
        assert CgmSource.DEXCOM.value == "dexcom"
        assert CgmSource.LIBRELINKUP.value == "librelinkup"
        assert CgmSource.NIGHTSCOUT.value == "nightscout"

    def test_covers_all_integrations(self):
        sources = {s.value for s in CgmSource}
        assert "dexcom" in sources
        assert "librelinkup" in sources
        assert "nightscout" in sources


if __name__ == "__main__":
    pytest.main([__file__, "-v"])