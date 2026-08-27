#!/usr/bin/env python3
"""Test proxy piercer with a known CDN-protected domain."""
import sys
sys.path.insert(0, "/gfin")
from proxy_piercer import ProxyPiercer
import asyncio

async def test():
    # Test with a domain that uses Cloudflare
    p = ProxyPiercer()
    print("Testing: scam-warning-example.com (known scam pattern)")
    result = await p.investigate("scam-warning-example.com")
    
    print("Domain:", result["domain"])
    print("Privacy detected:", result["privacy_detected"])
    print("CDN detected:", result["cdn_detected"])
    print("CDN provider:", result["cdn_provider"])
    print("Origin IP:", result["origin_ip"])
    print("Physical location:", result["physical_location"])
    print("Real hosting:", result["real_hosting"])
    print("Real identity:", result["real_identity"])
    print("Confidence:", result["confidence"])
    print("Evidence count:", len(result["evidence"]))
    print()
    print("=== SUMMARY ===")
    print(result["summary"])
    print()
    print("=== EVIDENCE ===")
    for e in result["evidence"][:15]:
        conf = e["confidence"]
        method = e["method"]
        finding = e["finding"]
        print(f"  [{conf}] {method}: {finding}")

asyncio.run(test())
