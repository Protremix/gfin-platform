"""
GFIN Load Test — Validates concurrent request capacity.
Tests: API response times, DB query performance, concurrent connections.
"""
import asyncio
import aiohttp
import time
import statistics
import sys

BASE_URL = "http://127.0.0.1:8000"
CONCURRENT_LEVELS = [1, 10, 50, 100, 200]
REQUESTS_PER_LEVEL = 50

async def make_request(session, endpoint, method="GET", payload=None):
    """Make a single request and return timing + status."""
    start = time.time()
    try:
        if method == "GET":
            async with session.get(f"{BASE_URL}{endpoint}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                await resp.read()
                elapsed = time.time() - start
                return elapsed, resp.status
        elif method == "POST":
            async with session.post(f"{BASE_URL}{endpoint}", json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                await resp.read()
                elapsed = time.time() - start
                return elapsed, resp.status
    except Exception as e:
        elapsed = time.time() - start
        return elapsed, 0

async def run_concurrent(endpoint, concurrency, total_requests, method="GET", payload=None):
    """Run requests at a given concurrency level."""
    semaphore = asyncio.Semaphore(concurrency)
    
    async def worker(session, results):
        async with semaphore:
            elapsed, status = await make_request(session, endpoint, method, payload)
            results.append((elapsed, status))
    
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(worker(session, results)) for _ in range(total_requests)]
        await asyncio.gather(*tasks)
    
    return results

def analyze_results(results, label):
    times = [r[0] for r in results]
    statuses = [r[1] for r in results]
    success = [r for r in results if r[1] == 200]
    fail = [r for r in results if r[1] != 200]
    
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"{'='*60}")
    print(f"  Total requests:  {len(results)}")
    print(f"  Success (200):   {len(success)} ({len(success)/len(results)*100:.1f}%)")
    print(f"  Failures:        {len(fail)} ({len(fail)/len(results)*100:.1f}%)")
    print(f"  Min time:        {min(times)*1000:.1f}ms")
    print(f"  Max time:        {max(times)*1000:.1f}ms")
    print(f"  Mean time:       {statistics.mean(times)*1000:.1f}ms")
    print(f"  Median time:     {statistics.median(times)*1000:.1f}ms")
    if len(times) > 10:
        print(f"  95th percentile: {statistics.quantiles(times, n=20)[18]*1000:.1f}ms")
    if fail:
        fail_codes = {}
        for _, s in fail:
            fail_codes[s] = fail_codes.get(s, 0) + 1
        print(f"  Error codes:     {fail_codes}")
    return len(success), len(fail)

async def main():
    print("GFIN LOAD TEST")
    print(f"Server: {BASE_URL}")
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    all_results = {}
    
    # Test 1: Health endpoint (lightweight)
    print("\n" + "="*60)
    print("TEST 1: Health endpoint (/health)")
    for c in CONCURRENT_LEVELS:
        results = await run_concurrent("/health", c, REQUESTS_PER_LEVEL)
        s, f = analyze_results(results, f"/health @ {c} concurrent")
        all_results[f"health_{c}"] = (s, f)
    
    # Test 2: Cases list (DB query)
    print("\n" + "="*60)
    print("TEST 2: Cases list (/api/cases)")
    for c in CONCURRENT_LEVELS:
        results = await run_concurrent("/api/cases", c, REQUESTS_PER_LEVEL)
        s, f = analyze_results(results, f"/api/cases @ {c} concurrent")
        all_results[f"cases_{c}"] = (s, f)
    
    # Test 3: Metrics endpoint
    print("\n" + "="*60)
    print("TEST 3: Metrics (/metrics)")
    for c in CONCURRENT_LEVELS:
        results = await run_concurrent("/metrics", c, REQUESTS_PER_LEVEL)
        s, f = analyze_results(results, f"/metrics @ {c} concurrent")
        all_results[f"metrics_{c}"] = (s, f)
    
    # Test 4: Telegram intel (heavier DB query)
    print("\n" + "="*60)
    print("TEST 4: Telegram intel (/api/telegram/intelligence?limit=50)")
    for c in [1, 10, 50, 100]:
        results = await run_concurrent("/api/telegram/intelligence?limit=50", c, REQUESTS_PER_LEVEL)
        s, f = analyze_results(results, f"/api/telegram/intelligence @ {c} concurrent")
        all_results[f"tg_{c}"] = (s, f)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    total_s = sum(s for s, f in all_results.values())
    total_f = sum(f for s, f in all_results.values())
    total = total_s + total_f
    print(f"  Total requests sent:   {total}")
    print(f"  Total successful:      {total_s} ({total_s/total*100:.1f}%)")
    print(f"  Total failures:        {total_f} ({total_f/total*100:.1f}%)")
    print(f"  Tests passed:          {sum(1 for s, f in all_results.values() if f == 0)}/{len(all_results)}")
    
    # Verdict
    if total_f == 0:
        print("\n  VERDICT: PASS — All requests succeeded at all concurrency levels")
    elif total_f / total < 0.01:
        print("\n  VERDICT: PASS (with warnings) — <1% failure rate")
    elif total_f / total < 0.05:
        print("\n  VERDICT: MARGINAL — <5% failure rate, investigate failures")
    else:
        print("\n  VERDICT: FAIL — >5% failure rate, server needs optimization")
    
    print(f"\n  Load test completed: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

asyncio.run(main())
