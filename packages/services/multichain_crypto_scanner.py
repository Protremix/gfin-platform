import os
#!/usr/bin/env python3
"""
GFIN Multi-Chain Crypto Wallet Detection & Tracing Module
Supports: BTC, ETH, USDT (all chains), TRX, SOL, TON, BSC, Polygon, Avalanche, Algorand
"""
import json, re, ssl, urllib.request, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

# ==================== ADDRESS DETECTION PATTERNS ====================

WALLET_PATTERNS = {
    # Bitcoin
    "BTC_LEGACY": {
        "regex": r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
        "chain": "Bitcoin",
        "asset": "BTC",
        "api": "blockchain_info",
    },
    "BTC_BECH32": {
        "regex": r'\bbc1[a-z0-9]{39,59}\b',
        "chain": "Bitcoin",
        "asset": "BTC",
        "api": "blockchain_info",
    },
    # Ethereum / EVM chains (ETH, BSC, Polygon, Avalanche, etc.)
    "EVM": {
        "regex": r'\b0x[a-fA-F0-9]{40}\b',
        "chain": "Ethereum/EVM",
        "asset": "ETH/ERC20/BEP20",
        "api": "etherscan_blockscout",
    },
    # Tron (TRC-20 — USDT most common here)
    "TRON": {
        "regex": r'\bT[A-Za-z0-9]{33}\b',
        "chain": "Tron",
        "asset": "TRX/TRC20",
        "api": "tronscan",
    },
    # Solana
    "SOLANA": {
        "regex": r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b',
        "chain": "Solana",
        "asset": "SOL/SPL",
        "api": "solscan",
        "note": "Solana addresses are base58, 32-44 chars. May have false positives — verify on-chain.",
    },
    # TON
    "TON": {
        "regex": r'\b[EU]Q[A-Za-z0-9_-]{46}\b',
        "chain": "TON",
        "asset": "TON",
        "api": "tonscan",
    },
    # Algorand
    "ALGORAND": {
        "regex": r'\b[A-Z2-7]{58}\b',
        "chain": "Algorand",
        "asset": "ALGO/ASA",
        "api": "algoexplorer",
        "note": "Algorand addresses are base32, 58 chars. May have false positives.",
    },
    # XRP (Ripple)
    "XRP": {
        "regex": r'\br[A-Za-z0-9]{24,34}\b',
        "chain": "Ripple",
        "asset": "XRP",
        "api": "xrpl",
    },
    # Litecoin
    "LTC": {
        "regex": r'\b[LM3][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
        "chain": "Litecoin",
        "asset": "LTC",
        "api": "blockchair",
    },
    # Dogecoin
    "DOGE": {
        "regex": r'\bD[A-Za-z0-9]{27,34}\b',
        "chain": "Dogecoin",
        "asset": "DOGE",
        "api": "blockchair",
        "note": "High false positive rate — 'D' prefix is common. Verify on-chain.",
    },
}

# Known USDT contract addresses across chains
USDT_CONTRACTS = {
    "ethereum": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "tron": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",  # Tether USD on Tron
    "bsc": "0x55d398326f99059fF775485246999027B3197955",
    "polygon": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    "avalanche": "0x9702230A8Ea53601f5cD2dc00fDBc2779458E5c3",
    "solana": "Es9vMFrzaCERmJfrF4H2FYD4KConKy4dXN8MpQyS5F4e",  # USDT on Solana
    "arbitrum": "0xFd086bC711DB8d8012d9ebC2E5b0d33c0c68D518",
    "optimism": "0x94b008aA00cb7944dC9fC3E4c39F9D2FF8faD2e5",
    "ton": "EQCxE6mUtFY4gDqmK3L2tq7Lj9n3D2Wz5n9v9g2k5j4m8n6p",  # Approximate
}


class MultiChainCryptoScanner:
    """Detect and trace crypto wallets across ALL blockchains."""

    def __init__(self):
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

    def _http_get_json(self, url, timeout=12):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "GFIN-CryptoScanner/1.0 (Law Enforcement)",
                "Accept": "application/json",
            })
            resp = urllib.request.urlopen(req, timeout=timeout, context=self.ssl_ctx)
            return json.loads(resp.read().decode('utf-8', errors='replace'))
        except:
            return None

    def detect_wallets(self, content: str) -> List[Dict]:
        """Detect ALL crypto wallet addresses in page content."""
        wallets = []
        seen = set()

        for wallet_type, config in WALLET_PATTERNS.items():
            matches = re.findall(config["regex"], content)
            for match in matches:
                if match in seen:
                    continue
                seen.add(match)
                wallets.append({
                    "address": match,
                    "type": wallet_type,
                    "chain": config["chain"],
                    "asset": config["asset"],
                    "api": config["api"],
                    "note": config.get("note", ""),
                })

        return wallets

    def trace_wallet(self, address: str, wallet_type: str = None) -> Optional[Dict]:
        """Trace a wallet on its blockchain — returns balance, tx count, and USDT info."""
        # Auto-detect wallet type if not provided
        if not wallet_type:
            for wt, config in WALLET_PATTERNS.items():
                if re.search(config["regex"], address):
                    wallet_type = wt
                    break

        if not wallet_type:
            return None

        if wallet_type in ("BTC_LEGACY", "BTC_BECH32"):
            return self._trace_btc(address)
        elif wallet_type == "EVM":
            return self._trace_evm(address)
        elif wallet_type == "TRON":
            return self._trace_tron(address)
        elif wallet_type == "SOLANA":
            return self._trace_solana(address)
        elif wallet_type == "TON":
            return self._trace_ton(address)
        elif wallet_type == "XRP":
            return self._trace_xrp(address)
        elif wallet_type == "LTC":
            return self._trace_blockchair(address, "litecoin")
        elif wallet_type == "DOGE":
            return self._trace_blockchair(address, "dogecoin")
        elif wallet_type == "ALGORAND":
            return self._trace_algorand(address)
        else:
            return None

    def _trace_btc(self, address: str) -> Optional[Dict]:
        """Trace Bitcoin wallet."""
        data = self._http_get_json(f"https://blockchain.info/rawaddr/{address}", timeout=15)
        if data:
            return {
                "address": address,
                "chain": "Bitcoin",
                "asset": "BTC",
                "total_received": data.get("total_received", 0) / 1e8,
                "total_sent": data.get("total_sent", 0) / 1e8,
                "final_balance": data.get("final_balance", 0) / 1e8,
                "transaction_count": data.get("n_tx", 0),
                "has_usdt": False,
                "usdt_balance": 0,
                "source": "blockchain.info",
            }
        return None

    def _trace_evm(self, address: str) -> Optional[Dict]:
        """Trace Ethereum/EVM wallet — checks ETH balance + USDT (ERC-20) + other tokens."""
        results = {
            "address": address,
            "chain": "Ethereum",
            "asset": "ETH",
            "eth_balance": 0,
            "transaction_count": 0,
            "usdt_balance": 0,
            "has_usdt": False,
            "usdt_chain": "ERC-20",
            "tokens": [],
            "source": "blockscout",
        }

        # Use Blockscout (free, no API key) for ETH balance and tx count
        eth_data = self._http_get_json(f"https://eth.blockscout.com/api/v2/addresses/{address}", timeout=12)
        if eth_data:
            coin_balance = eth_data.get("coin_balance", "0")
            try:
                results["eth_balance"] = int(coin_balance) / 1e18 if coin_balance else 0
            except:
                results["eth_balance"] = 0
            results["transaction_count"] = eth_data.get("transactions_count", 0)

            # Get token holdings
            tokens_data = self._http_get_json(f"https://eth.blockscout.com/api/v2/addresses/{address}/tokens", timeout=12)
            if tokens_data and tokens_data.get("data"):
                for token in tokens_data["data"][:20]:
                    token_addr = token.get("address", "")
                    symbol = token.get("symbol", "")
                    value = token.get("value", "0")
                    holder = token.get("holder", {})
                    # Check if USDT
                    if token_addr.lower() == USDT_CONTRACTS["ethereum"].lower() or symbol.upper() == "USDT":
                        try:
                            results["usdt_balance"] = float(value) / 1e6  # USDT has 6 decimals
                            results["has_usdt"] = True
                        except:
                            pass
                    results["tokens"].append({
                        "symbol": symbol,
                        "name": token.get("name", ""),
                        "address": token_addr,
                        "value": value,
                        "is_usdt": symbol.upper() == "USDT",
                    })

        # Also check BSC (same address format)
        bsc_data = self._http_get_json(f"https://bsc.blockscout.com/api/v2/addresses/{address}", timeout=12)
        if bsc_data and bsc_data.get("coin_balance"):
            try:
                bsc_balance = int(bsc_data.get("coin_balance", "0")) / 1e18
            except:
                bsc_balance = 0
            bsc_tx = bsc_data.get("transactions_count", 0)
            if bsc_balance > 0 or bsc_tx > 0:
                results["bsc_balance"] = bsc_balance
                results["bsc_transaction_count"] = bsc_tx
                results["chains_active"] = ["Ethereum", "BSC"]

                # Check BSC USDT
                bsc_tokens = self._http_get_json(f"https://bsc.blockscout.com/api/v2/addresses/{address}/tokens", timeout=12)
                if bsc_tokens and bsc_tokens.get("data"):
                    for token in bsc_tokens["data"][:20]:
                        if token.get("address", "").lower() == USDT_CONTRACTS["bsc"].lower() or token.get("symbol", "").upper() == "USDT":
                            try:
                                results["usdt_balance_bsc"] = float(token.get("value", "0")) / 1e18
                                results["has_usdt"] = True
                            except:
                                pass

        # Check Polygon
        poly_data = self._http_get_json(f"https://polygon.blockscout.com/api/v2/addresses/{address}", timeout=12)
        if poly_data and poly_data.get("coin_balance"):
            try:
                poly_balance = int(poly_data.get("coin_balance", "0")) / 1e18
            except:
                poly_balance = 0
            if poly_balance > 0 or poly_data.get("transactions_count", 0) > 0:
                results["polygon_balance"] = poly_balance
                results["polygon_tx_count"] = poly_data.get("transactions_count", 0)
                chains = results.get("chains_active", ["Ethereum"])
                if "BSC" not in chains:
                    chains.append("BSC")
                chains.append("Polygon")
                results["chains_active"] = chains

        # Check Arbitrum
        arb_data = self._http_get_json(f"https://arbitrum.blockscout.com/api/v2/addresses/{address}", timeout=10)
        if arb_data and arb_data.get("coin_balance"):
            try:
                arb_balance = int(arb_data.get("coin_balance", "0")) / 1e18
            except:
                arb_balance = 0
            if arb_balance > 0 or arb_data.get("transactions_count", 0) > 0:
                results["arbitrum_balance"] = arb_balance
                results["arbitrum_tx_count"] = arb_data.get("transactions_count", 0)
                chains = results.get("chains_active", ["Ethereum"])
                if "Arbitrum" not in chains:
                    chains.append("Arbitrum")
                results["chains_active"] = chains

        return results

    def _trace_tron(self, address: str) -> Optional[Dict]:
        """Trace Tron wallet — TRX balance + USDT (TRC-20) + other tokens."""
        results = {
            "address": address,
            "chain": "Tron",
            "asset": "TRX",
            "trx_balance": 0,
            "transaction_count": 0,
            "usdt_balance": 0,
            "has_usdt": False,
            "usdt_chain": "TRC-20",
            "tokens": [],
            "source": "tronscan",
        }

        # Tronscan API (free, no auth)
        tronscan_key = os.getenv("TRONSCAN_API_KEY", "")
        tronscan_headers = {"TRON-PRO-API-KEY": tronscan_key} if tronscan_key else {}
        data = self._http_get_json(f"https://apilist.tronscanapi.com/api/account/tokens?address={address}&show=15,10,100", timeout=12, headers=tronscan_headers)
        if data:
            # TRX balance
            tron_data = data.get("trc20token_balances", [])
            token_data = data.get("tokenBalances", [])

            # Get TRX balance
            trx_info = data.get("balance", 0)
            try:
                results["trx_balance"] = float(trx_info) / 1e6
            except:
                pass

            # Check for USDT (TRC-20)
            for token in tron_data:
                token_name = token.get("name", "")
                token_symbol = token.get("symbol", "")
                token_balance = token.get("balance", "0")
                token_decimal = token.get("tokenDecimal", 6)
                if "USDT" in token_name.upper() or token_symbol.upper() == "USDT":
                    try:
                        results["usdt_balance"] = float(token_balance) / (10 ** token_decimal)
                        results["has_usdt"] = True
                    except:
                        pass
                results["tokens"].append({
                    "name": token_name,
                    "symbol": token_symbol,
                    "balance": token_balance,
                    "is_usdt": "USDT" in token_name.upper() or token_symbol.upper() == "USDT",
                })

        # Also try TronGrid API
        grid_data = self._http_get_json(f"https://api.trongrid.io/v1/accounts/{address}", timeout=12)
        if grid_data and grid_data.get("data"):
            account = grid_data["data"][0]
            try:
                results["trx_balance"] = float(account.get("balance", 0)) / 1e6
            except:
                pass
            results["transaction_count"] = len(account.get("transactions", []))

            # Check TRC-20 tokens for USDT
            trc20 = account.get("trc20", [])
            for token_entry in trc20:
                if isinstance(token_entry, list) and len(token_entry) >= 2:
                    contract = token_entry[0]
                    balance = token_entry[1]
                    if contract == USDT_CONTRACTS["tron"]:
                        try:
                            results["usdt_balance"] = float(balance) / 1e6
                            results["has_usdt"] = True
                        except:
                            pass

        # Get transaction count from Tronscan
        tx_data = self._http_get_json(f"https://apilist.tronscanapi.com/api/transaction?sort=-timestamp&count=true&limit=1&start=0&address={address}", timeout=10)
        if tx_data:
            results["transaction_count"] = tx_data.get("total", 0)

        return results

    def _trace_solana(self, address: str) -> Optional[Dict]:
        """Trace Solana wallet — SOL balance + USDT (SPL) + tokens."""
        results = {
            "address": address,
            "chain": "Solana",
            "asset": "SOL",
            "sol_balance": 0,
            "transaction_count": 0,
            "usdt_balance": 0,
            "has_usdt": False,
            "usdt_chain": "SPL",
            "tokens": [],
            "source": "solscan",
        }

        # Solscan API (free)
        solscan_key = os.getenv("SOLSCAN_API_KEY", "")
        solscan_headers = {"token": solscan_key} if solscan_key else {}
        data = self._http_get_json(f"https://pro-api.solscan.io/v2/account/metadata?address={address}", timeout=12, headers=solscan_headers)
        if data:
            try:
                lamports = data.get("lamports", 0)
                results["sol_balance"] = lamports / 1e9
            except:
                pass
            results["transaction_count"] = data.get("txCount", 0)

        # Check for token accounts (USDT SPL)
        tokens_data = self._http_get_json(f"https://pro-api.solscan.io/v2/account/token/balance?address={address}", timeout=12, headers=solscan_headers)
        if tokens_data and isinstance(tokens_data, list):
            for token in tokens_data[:20]:
                token_addr = token.get("tokenAddress", "")
                symbol = token.get("symbol", "")
                amount = token.get("lamports", 0) or token.get("amount", 0)
                decimals = token.get("decimals", 6)
                if symbol.upper() == "USDT" or token_addr == USDT_CONTRACTS["solana"]:
                    try:
                        results["usdt_balance"] = float(amount) / (10 ** decimals)
                        results["has_usdt"] = True
                    except:
                        pass
                results["tokens"].append({
                    "symbol": symbol,
                    "name": token.get("name", ""),
                    "amount": amount,
                    "is_usdt": symbol.upper() == "USDT",
                })

        return results

    def _trace_ton(self, address: str) -> Optional[Dict]:
        """Trace TON wallet."""
        results = {
            "address": address,
            "chain": "TON",
            "asset": "TON",
            "ton_balance": 0,
            "transaction_count": 0,
            "usdt_balance": 0,
            "has_usdt": False,
            "usdt_chain": "TON",
            "source": "tonscan",
        }

        data = self._http_get_json(f"https://tonscan.org/api/v1/account/{address}", timeout=12)
        if data:
            try:
                results["ton_balance"] = float(data.get("balance", 0)) / 1e9
            except:
                pass
            results["transaction_count"] = data.get("transaction_count", 0)

        return results

    def _trace_xrp(self, address: str) -> Optional[Dict]:
        """Trace XRP wallet."""
        results = {
            "address": address,
            "chain": "Ripple",
            "asset": "XRP",
            "xrp_balance": 0,
            "transaction_count": 0,
            "has_usdt": False,
            "source": "xrpl",
        }

        data = self._http_get_json(f"https://api.xrpscan.com/api/v1/account/{address}", timeout=12)
        if data:
            try:
                results["xrp_balance"] = float(data.get("xrpBalance", 0))
            except:
                pass
            results["transaction_count"] = data.get("transactionCount", 0)

        return results

    def _trace_blockchair(self, address: str, blockchain: str) -> Optional[Dict]:
        """Trace via Blockchair (LTC, DOGE, etc.)."""
        data = self._http_get_json(f"https://api.blockchair.com/{blockchain}/dashboards/address/{address}", timeout=12)
        if data and data.get("data", {}).get(address):
            addr_data = data["data"][address]
            return {
                "address": address,
                "chain": blockchain.capitalize(),
                "asset": blockchain.upper(),
                "balance": addr_data.get("address", {}).get("balance", 0) / 1e8,
                "total_received": addr_data.get("address", {}).get("received", 0) / 1e8,
                "total_sent": addr_data.get("address", {}).get("spent", 0) / 1e8,
                "transaction_count": addr_data.get("address", {}).get("transaction_count", 0),
                "has_usdt": False,
                "source": "blockchair",
            }
        return None

    def _trace_algorand(self, address: str) -> Optional[Dict]:
        """Trace Algorand wallet."""
        results = {
            "address": address,
            "chain": "Algorand",
            "asset": "ALGO",
            "algo_balance": 0,
            "transaction_count": 0,
            "has_usdt": False,
            "source": "algoexplorer",
        }

        data = self._http_get_json(f"https://indexer.algoexplorerapi.io/v2/accounts/{address}", timeout=12)
        if data and data.get("account"):
            acct = data["account"]
            try:
                results["algo_balance"] = float(acct.get("amount", 0)) / 1e6
            except:
                pass
            # Check for USDT ASA (asset ID 312769)
            for asset in acct.get("assets", []):
                if asset.get("asset-id") == 312769:  # USDT on Algorand
                    try:
                        results["usdt_balance"] = float(asset.get("amount", 0)) / 1e6
                        results["has_usdt"] = True
                    except:
                        pass

        return results

    def trace_all(self, wallets: List[Dict]) -> List[Dict]:
        """Trace all detected wallets in parallel."""
        results = []

        def trace_one(wallet):
            return self.trace_wallet(wallet["address"], wallet["type"])

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(trace_one, w): w for w in wallets[:10]}
            for future in as_completed(futures, timeout=30):
                try:
                    result = future.result(timeout=30)
                    if result:
                        result["wallet_type"] = futures[future]["type"]
                        result["detected_chain"] = futures[future]["chain"]
                        results.append(result)
                except:
                    pass

        return results

    def scan_and_trace(self, content: str) -> Dict:
        """Full pipeline: detect wallets in content, then trace each on-chain."""
        wallets = self.detect_wallets(content)

        # Filter out likely false positives
        # Solana addresses that look like regular words (too short or all lowercase common words)
        filtered = []
        for w in wallets:
            addr = w["address"]
            # Skip addresses that are likely false positives
            if w["type"] == "DOGE" and len(addr) < 30:
                continue
            if w["type"] == "ALGORAND" and not all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in addr):
                continue
            filtered.append(w)

        traces = self.trace_all(filtered)

        return {
            "wallets_detected": len(filtered),
            "wallets_traced": len(traces),
            "wallets": filtered,
            "traces": traces,
            "usdt_found": any(t.get("has_usdt") for t in traces),
            "usdt_total": sum(t.get("usdt_balance", 0) for t in traces if t.get("has_usdt")),
            "chains_detected": list(set(w["chain"] for w in filtered)),
            "total_balance_usd_estimate": sum(
                t.get("usdt_balance", 0) for t in traces if t.get("has_usdt")
            ),
        }
