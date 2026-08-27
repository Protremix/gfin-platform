"""GFIN Crypto Intelligence — Module 28.

Cryptocurrency wallet analysis, blockchain tracing, and crypto fraud detection.
Per Master Spec: CryptoWallet entity, blockchain analysis, exchange integration.

Layer A: In-memory crypto intelligence framework
Layer B: Real blockchain API integration, exchange data feeds (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class WalletRiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TransactionType(StrEnum):
    INCOMING = "INCOMING"
    OUTGOING = "OUTGOING"
    INTERNAL = "INTERNAL"


class BlockchainType(StrEnum):
    BITCOIN = "BITCOIN"
    ETHEREUM = "ETHEREUM"
    TRON = "TRON"
    BSC = "BSC"
    SOLANA = "SOLANA"
    OTHER = "OTHER"


RISK_ORDER: dict[str, int] = {
    WalletRiskLevel.LOW.value: 1,
    WalletRiskLevel.MEDIUM.value: 2,
    WalletRiskLevel.HIGH.value: 3,
    WalletRiskLevel.CRITICAL.value: 4,
}


class CryptoTransaction(BaseModel):
    """A cryptocurrency transaction."""

    id: str
    tx_hash: str
    blockchain: str
    from_address: str
    to_address: str
    amount: float = 0.0
    token: str = ""
    tx_type: str = TransactionType.INCOMING.value
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confirmed: bool = False
    risk_indicators: list[str] = Field(default_factory=list)

    def add_risk_indicator(self, indicator: str) -> None:
        self.risk_indicators.append(indicator)


class WalletProfile(BaseModel):
    """A cryptocurrency wallet profile."""

    address: str
    blockchain: str
    label: str = ""
    risk_level: str = WalletRiskLevel.LOW.value
    total_received: float = 0.0
    total_sent: float = 0.0
    balance: float = 0.0
    transaction_count: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    linked_entities: list[str] = Field(default_factory=list)
    exchange: str = ""

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def link_entity(self, entity_id: str) -> None:
        if entity_id not in self.linked_entities:
            self.linked_entities.append(entity_id)

    @property
    def is_high_risk(self) -> bool:
        return RISK_ORDER.get(self.risk_level, 0) >= RISK_ORDER[WalletRiskLevel.HIGH.value]


class CryptoIntelligenceService:
    """Service for crypto intelligence and blockchain analysis.

    Per Master Spec: CryptoWallet entity, blockchain analysis.
    """

    def __init__(self) -> None:
        self._wallets: dict[str, WalletProfile] = {}
        self._transactions: dict[str, CryptoTransaction] = {}
        self._tx_counter = 0
        self._address_index: dict[str, list[str]] = {}  # address -> tx_ids

    def register_wallet(
        self,
        address: str,
        blockchain: str,
        label: str = "",
        exchange: str = "",
    ) -> WalletProfile:
        """Register or update a wallet profile."""
        wallet = WalletProfile(
            address=address,
            blockchain=blockchain,
            label=label,
            exchange=exchange,
        )
        self._wallets[address] = wallet
        return wallet

    def get_wallet(self, address: str) -> WalletProfile | None:
        return self._wallets.get(address)

    def list_wallets(
        self,
        blockchain: str | None = None,
        risk_level: str | None = None,
    ) -> list[WalletProfile]:
        wallets = list(self._wallets.values())
        if blockchain:
            wallets = [w for w in wallets if w.blockchain == blockchain]
        if risk_level:
            wallets = [w for w in wallets if w.risk_level == risk_level]
        return wallets

    def set_wallet_risk(self, address: str, risk_level: str) -> bool:
        wallet = self._wallets.get(address)
        if wallet is None:
            return False
        wallet.risk_level = risk_level
        return True

    def tag_wallet(self, address: str, tag: str) -> bool:
        wallet = self._wallets.get(address)
        if wallet is None:
            return False
        wallet.add_tag(tag)
        return True

    def link_wallet_to_entity(self, address: str, entity_id: str) -> bool:
        wallet = self._wallets.get(address)
        if wallet is None:
            return False
        wallet.link_entity(entity_id)
        return True

    def record_transaction(
        self,
        tx_hash: str,
        blockchain: str,
        from_address: str,
        to_address: str,
        amount: float = 0.0,
        token: str = "",
        tx_type: str = TransactionType.INCOMING.value,
        confirmed: bool = False,
    ) -> CryptoTransaction:
        """Record a crypto transaction."""
        self._tx_counter += 1
        tx = CryptoTransaction(
            id=f"CTX-{self._tx_counter:06d}",
            tx_hash=tx_hash,
            blockchain=blockchain,
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            token=token,
            tx_type=tx_type,
            confirmed=confirmed,
        )
        self._transactions[tx.id] = tx

        # Index by address
        for addr in [from_address, to_address]:
            if addr not in self._address_index:
                self._address_index[addr] = []
            self._address_index[addr].append(tx.id)

        # Update wallet stats
        if from_address in self._wallets:
            w = self._wallets[from_address]
            w.total_sent += amount
            w.transaction_count += 1
            w.last_seen = tx.timestamp
            if w.first_seen is None:
                w.first_seen = tx.timestamp
        if to_address in self._wallets:
            w = self._wallets[to_address]
            w.total_received += amount
            w.transaction_count += 1
            w.last_seen = tx.timestamp
            if w.first_seen is None:
                w.first_seen = tx.timestamp

        return tx

    def get_transaction(self, tx_id: str) -> CryptoTransaction | None:
        return self._transactions.get(tx_id)

    def get_transactions_by_address(self, address: str) -> list[CryptoTransaction]:
        tx_ids = self._address_index.get(address, [])
        return [self._transactions[tid] for tid in tx_ids if tid in self._transactions]

    def list_transactions(
        self,
        blockchain: str | None = None,
        tx_type: str | None = None,
    ) -> list[CryptoTransaction]:
        txs = list(self._transactions.values())
        if blockchain:
            txs = [t for t in txs if t.blockchain == blockchain]
        if tx_type:
            txs = [t for t in txs if t.tx_type == tx_type]
        return txs

    def trace_funds(self, start_address: str, depth: int = 3) -> dict[str, Any]:
        """Trace fund flow from a starting address (BFS)."""
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(start_address, 0)]
        path: list[dict[str, Any]] = []

        while queue:
            addr, current_depth = queue.pop(0)
            if addr in visited or current_depth > depth:
                continue
            visited.add(addr)

            wallet = self._wallets.get(addr)
            txs = self.get_transactions_by_address(addr)

            path.append(
                {
                    "address": addr,
                    "depth": current_depth,
                    "wallet": wallet.label if wallet else "Unknown",
                    "risk_level": wallet.risk_level if wallet else "UNKNOWN",
                    "transaction_count": len(txs),
                }
            )

            for tx in txs:
                next_addr = tx.to_address if tx.from_address == addr else tx.from_address
                if next_addr not in visited and current_depth < depth:
                    queue.append((next_addr, current_depth + 1))

        return {
            "start_address": start_address,
            "addresses_traced": len(visited),
            "path": path,
        }

    def assess_risk(self, address: str) -> dict[str, Any]:
        """Assess risk for a wallet address."""
        wallet = self._wallets.get(address)
        if wallet is None:
            return {"address": address, "risk_level": "UNKNOWN", "indicators": []}

        indicators: list[str] = []
        txs = self.get_transactions_by_address(address)

        # High transaction volume
        if wallet.transaction_count > 100:
            indicators.append("HIGH_TRANSACTION_VOLUME")

        # Large total received
        if wallet.total_received > 100000:
            indicators.append("LARGE_VOLUME")

        # High-risk tags
        high_risk_tags = {"scam", "fraud", "mixer", "darknet", "ransomware"}
        if any(tag.lower() in high_risk_tags for tag in wallet.tags):
            indicators.append("HIGH_RISK_TAG")

        # Unconfirmed transactions
        unconfirmed = sum(1 for t in txs if not t.confirmed)
        if unconfirmed > 0:
            indicators.append(f"UNCONFIRMED_TXS:{unconfirmed}")

        # Determine risk level
        if "HIGH_RISK_TAG" in indicators:
            risk = WalletRiskLevel.CRITICAL.value
        elif len(indicators) >= 3:
            risk = WalletRiskLevel.HIGH.value
        elif len(indicators) >= 1:
            risk = WalletRiskLevel.MEDIUM.value
        else:
            risk = WalletRiskLevel.LOW.value

        return {
            "address": address,
            "risk_level": risk,
            "indicators": indicators,
            "transaction_count": wallet.transaction_count,
            "total_received": wallet.total_received,
            "total_sent": wallet.total_sent,
        }

    def get_summary(self) -> dict[str, Any]:
        """Get crypto intelligence summary."""
        wallets = list(self._wallets.values())
        return {
            "total_wallets": len(wallets),
            "high_risk_wallets": sum(1 for w in wallets if w.is_high_risk),
            "total_transactions": len(self._transactions),
            "by_blockchain": self._count_by_blockchain(),
        }

    def _count_by_blockchain(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for w in self._wallets.values():
            counts[w.blockchain] = counts.get(w.blockchain, 0) + 1
        return counts

    @property
    def wallet_count(self) -> int:
        return len(self._wallets)

    @property
    def transaction_count(self) -> int:
        return len(self._transactions)
