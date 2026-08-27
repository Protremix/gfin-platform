#!/usr/bin/env python3
"""
GFIN Money Laundering Detection & Alert Module
Detects money laundering infrastructure and patterns from Telegram intelligence.

Detection patterns:
1. "Defrauded funds" exchange services
2. USDT exchange for stolen/illegal money
3. Third-party payment acceptance across multiple countries
4. "Wash" or "clean" money services
5. Anonymous crypto exchange without KYC
6. Bulk USDT transfer services
7. Cross-border money movement infrastructure
"""

import re
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Money laundering detection patterns
LAUNDERING_PATTERNS = {
    "defrauded_funds_exchange": {
        "keywords": [
            r"defrauded\s+(money|funds)",
            r"defrauding\s+funds",
            r"defrauded\s+money",
            r"exchange\s+(defrauded|stolen|illegal)\s+(funds|money)",
        ],
        "weight": 0.95,
        "description": "Service explicitly offers exchange of defrauded/stolen funds"
    },
    "bulk_usdt_laundering": {
        "keywords": [
            r"(sell|exchange)\s+(for\s+)?usdt.*accept.*funds",
            r"usdt.*accept.*third.?(party|payment)",
            r"send\s+usdt.*within.*minutes",
            r"usdt.*exchange.*defrauded",
            r"flash\s+usdt",
            r"flash\s+btc",
            r"flash\s+(bitcoin|ethereum|crypto)",
        ],
        "weight": 0.85,
        "description": "Bulk USDT exchange service accepting illicit funds"
    },
    "multi_country_laundering": {
        "keywords": [
            r"\d+\s*(country|countries)\s+accounts",
            r"global\s+accounts",
            r"accept.*third.?(party|payment).*bank\s+transfer",
            r"support\s+\d+\s*country",
            r"worldwide.*account",
        ],
        "weight": 0.80,
        "description": "Multi-country account infrastructure for moving illicit funds"
    },
    "no_kyc_anonymous_exchange": {
        "keywords": [
            r"no\s+(kyc|verification|id|required)",
            r"anonymous\s+(exchange|transfer|wallet)",
            r"no\s+registration\s+needed",
            r"instant\s+(exchange|transfer).*(no\s+questions|discreet)",
        ],
        "weight": 0.70,
        "description": "Anonymous exchange service without KYC/AML checks"
    },
    "cash_to_crypto_laundering": {
        "keywords": [
            r"cash\s+deposit.*(usdt|crypto|bitcoin)",
            r"physical\s+cash.*exchange",
            r"cash\s+to\s+(crypto|usdt|btc)",
            r"accept\s+cash.*deposit.*send\s+usdt",
        ],
        "weight": 0.75,
        "description": "Cash-to-crypto conversion service (common laundering method)"
    },
    "wash_service": {
        "keywords": [
            r"(wash|clean|mix|tumble).*(money|funds|crypto|usdt|btc)",
            r"money\s+laundering",
            r"clean\s+(dirty|stolen|illegal)\s+(money|funds)",
            r"(swap|split|convert).*defrauded",
        ],
        "weight": 0.90,
        "description": "Explicit money washing/mixing service"
    },
    "flash_crypto_scam": {
        "keywords": [
            r"flash\s+(usdt|btc|bitcoin|ethereum)",
            r"flash\s+crypto",
            r"flash\s+(transferable|tradable|validity)",
            r"flash\s+\d+\s*days",
            r"flash\s+software",
        ],
        "weight": 0.85,
        "description": "Flash crypto scam - fake cryptocurrency that disappears after time period"
    },
    "investment_fraud_laundering": {
        "keywords": [
            r"(defrauded|stolen|scammed).*(invest|forex|crypto)",
            r"recover.*defrauded.*funds.*invest",
            r"exchange.*scammed.*money",
        ],
        "weight": 0.80,
        "description": "Laundering proceeds from investment fraud"
    },
}


def detect_money_laundering(text: str) -> Dict[str, Any]:
    """
    Analyze text for money laundering indicators.
    
    Returns:
        {
            "is_laundering": bool,
            "risk_level": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "MINIMAL",
            "risk_score": float,
            "detected_patterns": list of pattern names,
            "evidence": list of matched text snippets,
            "classification": str,
            "recommendation": str
        }
    """
    text_lower = text.lower()
    detected = []
    evidence = []
    total_score = 0.0
    
    for pattern_name, pattern_def in LAUNDERING_PATTERNS.items():
        for regex in pattern_def["keywords"]:
            matches = re.findall(regex, text_lower, re.IGNORECASE)
            if matches:
                detected.append(pattern_name)
                for m in matches[:3]:
                    evidence.append({
                        "pattern": pattern_name,
                        "description": pattern_def["description"],
                        "weight": pattern_def["weight"],
                        "match": m if isinstance(m, str) else str(m)
                    })
                total_score = max(total_score, pattern_def["weight"])
                break
    
    # Multiple patterns increase score
    if len(detected) >= 2:
        total_score = min(total_score + 0.1 * (len(detected) - 1), 1.0)
    if len(detected) >= 3:
        total_score = min(total_score + 0.05, 1.0)
    
    # Determine risk level
    if total_score >= 0.85:
        risk_level = "CRITICAL"
        classification = "Confirmed money laundering infrastructure"
        recommendation = "Immediate law enforcement referral required. Flag all associated wallets, accounts, and Telegram channels."
    elif total_score >= 0.70:
        risk_level = "HIGH"
        classification = "Probable money laundering operation"
        recommendation = "Refer to financial crimes unit. Monitor all associated transactions and entities."
    elif total_score >= 0.50:
        risk_level = "MEDIUM"
        classification = "Suspicious financial activity"
        recommendation = "Investigate further. Cross-reference with known scam networks."
    elif total_score >= 0.30:
        risk_level = "LOW"
        classification = "Potential financial anomaly"
        recommendation = "Log and monitor for escalation."
    else:
        risk_level = "MINIMAL"
        classification = "No laundering indicators detected"
        recommendation = "No action required."
    
    return {
        "is_laundering": total_score >= 0.50,
        "risk_level": risk_level,
        "risk_score": round(total_score, 2),
        "detected_patterns": detected,
        "evidence": evidence,
        "pattern_count": len(detected),
        "classification": classification,
        "recommendation": recommendation,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def create_laundering_alert(
    source: str,
    group_name: str,
    group_username: str,
    message_text: str,
    detected: Dict[str, Any],
    entities: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Create a GFIN alert for money laundering activity."""
    alert_id = f"LAUNDER-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{group_username.replace('@', '')}"
    
    alert = {
        "alert_id": alert_id,
        "type": "MONEY_LAUNDERING",
        "level": detected["risk_level"],
        "risk_score": detected["risk_score"],
        "source": source,
        "group_name": group_name,
        "group_username": group_username,
        "classification": detected["classification"],
        "detected_patterns": detected["detected_patterns"],
        "recommendation": detected["recommendation"],
        "message_excerpt": message_text[:500],
        "entities": entities or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "NEW"
    }
    
    return alert


# Known laundering operations identified from Telegram surveillance
KNOWN_LAUNDERING_OPERATIONS = [
    {
        "group_username": "@Ghanausdt_exchange",
        "group_name": "Ghana buy usdt/Ghana defrauded Money/Ghana Defrauding funds/Ghana usdt exchange",
        "country": "Ghana",
        "operator": "@btcv123",
        "description": "Accepts defrauded funds, provides USDT in exchange. Supports 70 countries. Third-party payments accepted.",
        "risk_level": "CRITICAL",
        "patterns": ["defrauded_funds_exchange", "bulk_usdt_laundering", "multi_country_laundering", "cash_to_crypto_laundering"]
    },
    {
        "group_username": "@Malta_buy_usdt",
        "group_name": "Malta buy usdt/Malta defrauded Money/Malta Defrauding funds/Malta exchange usdt",
        "country": "Malta",
        "operator": "@btcv123",
        "description": "Same operator as Ghana channel. Defrauded funds exchange, 70 country accounts, third-party payments.",
        "risk_level": "CRITICAL",
        "patterns": ["defrauded_funds_exchange", "bulk_usdt_laundering", "multi_country_laundering", "cash_to_crypto_laundering"]
    },
    {
        "group_username": "@Colombia_buy_usdt",
        "group_name": "Colombia buy usdt/Colombia defrauded Money/Colombia Defrauding funds//Colombia Ponzi",
        "country": "Colombia",
        "operator": "@btcv123",
        "description": "Same operator. Explicitly mentions Ponzi schemes. Defrauded funds exchange infrastructure.",
        "risk_level": "CRITICAL",
        "patterns": ["defrauded_funds_exchange", "bulk_usdt_laundering", "multi_country_laundering", "investment_fraud_laundering"]
    },
    {
        "group_username": "@Brazil_exchange_usdt0",
        "group_name": "Brazil buy usdt/Brazil defrauded Money/Brazil Defrauding funds/Brazil exchange usdt",
        "country": "Brazil",
        "operator": "@btcv123",
        "description": "Same operator. Defrauded funds exchange targeting Brazilian fraud victims.",
        "risk_level": "CRITICAL",
        "patterns": ["defrauded_funds_exchange", "bulk_usdt_laundering", "multi_country_laundering"]
    },
    {
        "group_username": "@Romania_buy_usdt",
        "group_name": "Romania buy usdt/Romania defrauded Money/Romania Defrauding funds/Romania usdt exchange",
        "country": "Romania",
        "operator": "@btcv123",
        "description": "Same operator. Defrauded funds exchange targeting Romanian fraud victims.",
        "risk_level": "CRITICAL",
        "patterns": ["defraunded_funds_exchange", "bulk_usdt_laundering", "multi_country_laundering"]
    },
    {
        "group_username": "@Luxembourgexchangeusdt",
        "group_name": "Luxembourg buy usdt/Luxembourg defrauded Money/Luxembourg Defrauding funds/Luxembourg exchange usdt",
        "country": "Luxembourg",
        "operator": "@btcv123",
        "description": "Same operator. Defrauded funds exchange targeting EU fraud victims.",
        "risk_level": "CRITICAL",
        "patterns": ["defrauded_funds_exchange", "bulk_usdt_laundering", "multi_country_laundering"]
    },
    {
        "group_username": "@fxscammersexposed",
        "group_name": "Forex Scammers Exposed",
        "country": "Unknown",
        "operator": "@KarI_Fx (KarI Fx)",
        "description": "Flash USDT/BTC scam operation inside scam exposure group. Offers fake flash cryptocurrency with 180-day validity.",
        "risk_level": "HIGH",
        "patterns": ["flash_crypto_scam", "bulk_usdt_laundering"]
    },
]


def generate_laundering_report():
    """Generate a full money laundering intelligence report from known operations."""
    report = {
        "report_id": f"GFIN-LAUDR-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "title": "GFIN Money Laundering Intelligence Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_operations": len(KNOWN_LAUNDERING_OPERATIONS),
            "critical": sum(1 for op in KNOWN_LAUNDERING_OPERATIONS if op["risk_level"] == "CRITICAL"),
            "high": sum(1 for op in KNOWN_LAUNDERING_OPERATIONS if op["risk_level"] == "HIGH"),
            "countries_affected": list(set(op["country"] for op in KNOWN_LAUNDERING_OPERATIONS)),
            "primary_operator": "@btcv123",
            "operator_reach": "7 country-specific channels, 70+ countries supported",
            "total_telegram_channels": len(KNOWN_LAUNDERING_OPERATIONS)
        },
        "operations": KNOWN_LAUNDERING_OPERATIONS,
        "intelligence_assessment": {
            "operator_correlation": "All 6 country USDT exchange channels are operated by the same entity: @btcv123. This indicates a coordinated, multi-jurisdictional money laundering network.",
            "modus_operandi": "The operator accepts 'defrauded funds' (proceeds from fraud/scams) and exchanges them for USDT cryptocurrency, charging a commission. They maintain accounts in 70+ countries and accept third-party payments, bank transfers, and cash deposits.",
            "scale": "The operation spans at minimum 6 countries (Ghana, Malta, Colombia, Brazil, Romania, Luxembourg) with claimed capability in 70+ countries. This is a significant transnational money laundering infrastructure.",
            "flash_crypto_scam": "A separate operation by @KarI_Fx promotes 'flash' cryptocurrency (fake USDT/BTC that allegedly lasts 180 days). This is a known scam type where victims pay for fake crypto that disappears.",
            "recommended_actions": [
                "1. Flag all wallets associated with @btcv123 for blockchain analysis",
                "2. Refer to national FIUs (Financial Intelligence Units) in all 6 affected countries",
                "3. Refer to INTERPOL and Europol for cross-border coordination",
                "4. Monitor @btcv123 Telegram account for wallet address disclosures",
                "5. Cross-reference with existing GFIN scam cases for victim correlation",
                "6. Issue takedown requests to Telegram for channels facilitating money laundering",
                "7. Flag @KarI_Fx flash crypto operation as additional scam vector"
            ]
        }
    }
    return report


if __name__ == "__main__":
    # Test detection on known laundering messages
    test_messages = [
        "Sell and exchange for USDT, Accept various funds and Money. We have global accounts, Support 70 Country accounts. Accept third-party payment, bank transfer and Cash deposit. Send USDT within 30 minutes.",
        "FLASH USDT TRC20/ERC20. FLASH BITCOIN. FLASH ETHEREUM. VALIDITY 180 DAYS. AVAILABLE P2P TRADING. SWAP & SPLIT & CONVERT.",
        "Hello everyone, I was scammed by a forex broker and lost $5000.",
    ]
    
    for msg in test_messages:
        result = detect_money_laundering(msg)
        print(f"Risk: {result['risk_level']} ({result['risk_score']}) | Patterns: {result['detected_patterns']}")
        print(f"  Classification: {result['classification']}")
        print()
    
    # Generate report
    report = generate_laundering_report()
    print(f"\nReport: {report['report_id']}")
    print(f"Operations: {report['summary']['total_operations']}")
    print(f"Countries: {', '.join(report['summary']['countries_affected'])}")
    print(f"Primary operator: {report['summary']['primary_operator']}")
