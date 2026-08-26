"""Tests for Crypto Intelligence — Module 28."""

import pytest

from services.crypto_intelligence import (
    BlockchainType,
    CryptoIntelligenceService,
    CryptoTransaction,
    WalletProfile,
    WalletRiskLevel,
)


@pytest.fixture
def service():
    return CryptoIntelligenceService()


class TestWalletProfile:
    def test_add_tag(self):
        w = WalletProfile(address="0xABC", blockchain="ETH")
        w.add_tag("scam")
        w.add_tag("scam")
        assert len(w.tags) == 1

    def test_link_entity(self):
        w = WalletProfile(address="0xABC", blockchain="ETH")
        w.link_entity("ent-1")
        w.link_entity("ent-1")
        assert len(w.linked_entities) == 1

    def test_is_high_risk(self):
        w = WalletProfile(address="0xABC", blockchain="ETH", risk_level=WalletRiskLevel.HIGH.value)
        assert w.is_high_risk is True

    def test_is_not_high_risk(self):
        w = WalletProfile(address="0xABC", blockchain="ETH", risk_level=WalletRiskLevel.LOW.value)
        assert w.is_high_risk is False


class TestCryptoTransaction:
    def test_add_risk_indicator(self):
        tx = CryptoTransaction(
            id="T1", tx_hash="0x123", blockchain="ETH",
            from_address="A", to_address="B",
        )
        tx.add_risk_indicator("MIXER")
        assert "MIXER" in tx.risk_indicators


class TestCryptoIntelligenceService:
    def test_register_wallet(self, service):
        w = service.register_wallet("0xABC", BlockchainType.ETHEREUM.value, label="Scam Wallet")
        assert w.address == "0xABC"
        assert service.wallet_count == 1

    def test_get_wallet(self, service):
        service.register_wallet("0xABC", "ETH")
        assert service.get_wallet("0xABC") is not None
        assert service.get_wallet("0xNONEXIST") is None

    def test_list_wallets(self, service):
        service.register_wallet("0xA", "ETH")
        service.register_wallet("0xB", "BTC")
        assert len(service.list_wallets()) == 2
        assert len(service.list_wallets(blockchain="ETH")) == 1

    def test_list_wallets_by_risk(self, service):
        service.register_wallet("0xA", "ETH")
        service.set_wallet_risk("0xA", WalletRiskLevel.HIGH.value)
        service.register_wallet("0xB", "ETH")
        assert len(service.list_wallets(risk_level=WalletRiskLevel.HIGH.value)) == 1

    def test_set_wallet_risk(self, service):
        service.register_wallet("0xA", "ETH")
        assert service.set_wallet_risk("0xA", WalletRiskLevel.CRITICAL.value) is True
        assert service.get_wallet("0xA").risk_level == WalletRiskLevel.CRITICAL.value

    def test_set_wallet_risk_nonexistent(self, service):
        assert service.set_wallet_risk("0xNONEXIST", WalletRiskLevel.HIGH.value) is False

    def test_tag_wallet(self, service):
        service.register_wallet("0xA", "ETH")
        assert service.tag_wallet("0xA", "scam") is True
        assert "scam" in service.get_wallet("0xA").tags

    def test_tag_nonexistent(self, service):
        assert service.tag_wallet("0xNONEXIST", "scam") is False

    def test_link_wallet_to_entity(self, service):
        service.register_wallet("0xA", "ETH")
        assert service.link_wallet_to_entity("0xA", "ent-1") is True
        assert "ent-1" in service.get_wallet("0xA").linked_entities

    def test_record_transaction(self, service):
        service.register_wallet("0xA", "ETH")
        service.register_wallet("0xB", "ETH")
        tx = service.record_transaction("0xHASH", "ETH", "0xA", "0xB", amount=5.0)
        assert tx.id.startswith("CTX-")
        assert service.transaction_count == 1

    def test_record_transaction_updates_wallets(self, service):
        service.register_wallet("0xA", "ETH")
        service.register_wallet("0xB", "ETH")
        service.record_transaction("0xH1", "ETH", "0xA", "0xB", amount=10.0)
        w_a = service.get_wallet("0xA")
        w_b = service.get_wallet("0xB")
        assert w_a.total_sent == 10.0
        assert w_b.total_received == 10.0
        assert w_a.transaction_count == 1
        assert w_b.transaction_count == 1

    def test_get_transaction(self, service):
        tx = service.record_transaction("0xH", "ETH", "A", "B")
        assert service.get_transaction(tx.id) is not None
        assert service.get_transaction("nonexistent") is None

    def test_get_transactions_by_address(self, service):
        service.register_wallet("0xA", "ETH")
        service.record_transaction("0xH1", "ETH", "0xA", "0xB", amount=1)
        service.record_transaction("0xH2", "ETH", "0xC", "0xA", amount=2)
        txs = service.get_transactions_by_address("0xA")
        assert len(txs) == 2

    def test_list_transactions(self, service):
        service.record_transaction("0xH1", "ETH", "A", "B")
        service.record_transaction("0xH2", "BTC", "C", "D")
        assert len(service.list_transactions()) == 2
        assert len(service.list_transactions(blockchain="ETH")) == 1

    def test_trace_funds(self, service):
        service.register_wallet("A", "ETH")
        service.register_wallet("B", "ETH")
        service.register_wallet("C", "ETH")
        service.record_transaction("0xH1", "ETH", "A", "B", amount=5)
        service.record_transaction("0xH2", "ETH", "B", "C", amount=3)
        result = service.trace_funds("A", depth=2)
        assert result["start_address"] == "A"
        assert result["addresses_traced"] >= 2

    def test_assess_risk_low(self, service):
        service.register_wallet("A", "ETH")
        service.record_transaction("0xH1", "ETH", "A", "B", amount=10, confirmed=True)
        result = service.assess_risk("A")
        assert result["risk_level"] == WalletRiskLevel.LOW.value

    def test_assess_risk_high_tag(self, service):
        service.register_wallet("A", "ETH")
        service.tag_wallet("A", "scam")
        service.record_transaction("0xH1", "ETH", "A", "B", amount=10)
        result = service.assess_risk("A")
        assert result["risk_level"] == WalletRiskLevel.CRITICAL.value

    def test_assess_risk_high_volume(self, service):
        service.register_wallet("A", "ETH")
        for i in range(101):
            service.record_transaction(f"0xH{i}", "ETH", "A", "B", amount=100)
        result = service.assess_risk("A")
        assert "HIGH_TRANSACTION_VOLUME" in result["indicators"]

    def test_assess_risk_unknown(self, service):
        result = service.assess_risk("nonexistent")
        assert result["risk_level"] == "UNKNOWN"

    def test_get_summary(self, service):
        service.register_wallet("A", "ETH")
        service.register_wallet("B", "BTC")
        service.record_transaction("0xH1", "ETH", "A", "B")
        summary = service.get_summary()
        assert summary["total_wallets"] == 2
        assert summary["total_transactions"] == 1

    def test_summary_empty(self, service):
        summary = service.get_summary()
        assert summary["total_wallets"] == 0
