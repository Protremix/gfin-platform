"""Integration tests for GFIN Source Registry and discovery pipeline."""
import pytest
from services.brain.api_discovery.engine import APIDiscoveryEngine, DiscoveryStatus
from packages.sources.registry import SourceRegistry, SourceRecord
from packages.sources.scoring import SourceScorer
from packages.sources.policy import SourcePolicy, AccessStatus, AuthMethod


class TestSourceDiscoveryPipeline:
    """Test the full source discovery pipeline."""

    def setup_method(self):
        self.registry = SourceRegistry()
        self.scorer = SourceScorer()
        self.policy = SourcePolicy()
        self.engine = APIDiscoveryEngine(self.registry, self.scorer, self.policy)

    def test_full_discovery_pipeline_domain(self):
        """Test discovering sources for a domain investigation."""
        result = self.engine.discover_for_gap("CASE-INT-001", "domain")
        assert result["candidates_found"] > 0
        # Should find Google DNS and Verisign RDAP
        providers = [r["provider"] for r in result["results"]]
        assert "Google" in providers or "Verisign" in providers

    def test_full_discovery_pipeline_crypto(self):
        """Test discovering sources for a crypto investigation."""
        result = self.engine.discover_for_gap("CASE-INT-002", "crypto")
        assert result["candidates_found"] > 0
        # Should find blockchain sources
        providers = [r["provider"] for r in result["results"]]
        assert any("block" in p.lower() or "chain" in p.lower() for p in providers)

    def test_discovery_with_registered_source(self):
        """Test that registered sources appear in discovery."""
        source = SourceRecord(
            source_id="custom_src", provider="CustomAPI", connector="custom",
            base_url="https://api.custom.com", auth_method=AuthMethod.API_KEY,
            data_categories=["custom_data"], jurisdictions=["GLOBAL"],
            allowed_data=["custom"], legal_basis="Licensed",
        )
        self.registry.register(source)
        result = self.engine.discover_for_gap("CASE-INT-003", "custom_data")
        providers = [r["provider"] for r in result["results"]]
        assert "CustomAPI" in providers

    def test_discovery_ranking_by_quality(self):
        """Test that sources are ranked by quality score."""
        result = self.engine.discover_for_gap("CASE-INT-004", "domain")
        if len(result["results"]) >= 2:
            scores = [r["quality_score"] for r in result["results"]]
            # Should be sorted descending
            assert scores[0] >= scores[-1]

    def test_discovery_includes_authorization_status(self):
        """Test that discovery results include authorization status."""
        result = self.engine.discover_for_gap("CASE-INT-005", "domain")
        for r in result["results"]:
            assert "access_status" in r
            assert r["access_status"] in [
                DiscoveryStatus.FOUND_AND_ACCESSIBLE.value,
                DiscoveryStatus.FOUND_BUT_AUTH_REQUIRED.value,
                DiscoveryStatus.FOUND_BUT_NOT_SUPPORTED.value,
            ]

    def test_unknown_source_discovery(self):
        """Test the 'unknown source' discovery flow."""
        result = self.engine.discover_unknown("CASE-INT-006", "Need IP address geolocation")
        assert "inferred_data_type" in result
        assert result["inferred_data_type"] == "ip"
        assert "summary" in result

    def test_refresh_catalog(self):
        """Test catalog refresh."""
        result = self.engine.refresh_catalog()
        assert "total_sources" in result
        assert "refreshed" in result

    def test_discovery_history_tracking(self):
        """Test that discovery actions are tracked."""
        self.engine.discover_for_gap("CASE-INT-007", "domain")
        self.engine.discover_for_gap("CASE-INT-008", "crypto")
        history = self.engine.get_discovery_history()
        assert len(history) == 2
        assert history[0]["case_id"] == "CASE-INT-007"
        assert history[1]["case_id"] == "CASE-INT-008"

    def test_failure_no_fabrication(self):
        """Test that discovery never fabricates results."""
        result = self.engine.discover_for_gap("CASE-INT-009", "nonexistent_data_type")
        # Should return empty results, not fabricated data
        assert result["candidates_found"] == 0
        assert result["results"] == []

    def test_all_sources_have_quality_scores(self):
        """Test that every discovered source has a quality score."""
        result = self.engine.discover_for_gap("CASE-INT-010", "domain")
        for r in result["results"]:
            assert "quality_score" in r
            assert 0 <= r["quality_score"] <= 1
