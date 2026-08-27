#!/usr/bin/env python3
"""Test the proxy piercer module."""
import sys
sys.path.insert(0, "/gfin")
from proxy_piercer import ProxyPiercer
import asyncio

async def test():
    p = ProxyPiercer()
    result = await p.investigate("cncintelinfo.com")
    
    print("Domain:", result["domain"])
    print("Privacy detected:", result["privacy_detected"])
    print("CDN detected:", result["cdn_detected"])
    print("CDN provider:", result["cdn_provider"])
    print("Origin IP:", result["origin_ip"])
    print("Physical location:", result["physical_location"])
    print("Real identity:", result["real_identity"])
    print("Confidence:", result["confidence"])
    print("Evidence count:", len(result["evidence"]))
    print("Correlations:", len(result["correlations"]))
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
    print()
    print("=== METHODS TRIED ===")
    for m in result["methods_tried"]:
        print(f"  - {m}")

asyncio.run(test())
