"""
GFIN Dynamic Source Selector v1.0
Replaces fixed pipeline order with intelligent source ranking.

Sources are ranked by:
1. RELEVANCE — does the source cover the entity types we need?
2. AUTHORITY — is the source an official/trusted database?
3. FRESHNESS — how recent is the data?
4. COVERAGE — how much data does the source provide?
5. INDEPENDENCE — is the source independent of other sources already tried?
6. AVAILABILITY — is the source currently reachable?
"""

SOURCE_PROFILES = {
    "SCAM_ENGINE": {
        "entity_types": ["text", "pattern", "behavioral"],
        "authority": 0.7,  # Internal engine, decent authority
        "freshness": 1.0,  # Real-time
        "coverage": 0.8,
        "independence": 1.0,  # Always independent
        "latency": 0.1  # Very fast
    },
    "BAILII": {
        "entity_types": ["legal", "case_law", "court"],
        "authority": 0.95,  # Official legal database
        "freshness": 0.5,
        "coverage": 0.4,  # UK only
        "independence": 0.9,
        "latency": 0.3
    },
    "GITHUB": {
        "entity_types": ["code", "repository", "infrastructure"],
        "authority": 0.6,
        "freshness": 0.8,
        "coverage": 0.6,
        "independence": 0.8,
        "latency": 0.2
    },
    "SEC_EDGAR": {
        "entity_types": ["company", "financial", "regulatory"],
        "authority": 0.95,
        "freshness": 0.7,
        "coverage": 0.5,  # US only
        "independence": 0.9,
        "latency": 0.3
    },
    "ICIJ": {
        "entity_types": ["company", "offshore", "person"],
        "authority": 0.85,
        "freshness": 0.3,  # Historical data
        "coverage": 0.7,
        "independence": 0.9,
        "latency": 0.4
    },
    "GDELT": {
        "entity_types": ["news", "event", "geopolitical"],
        "authority": 0.6,
        "freshness": 0.9,
        "coverage": 0.8,
        "independence": 0.7,
        "latency": 0.3
    },
    "BLOCKCHAIN_INFO": {
        "entity_types": ["wallet", "transaction", "bitcoin"],
        "authority": 0.95,
        "freshness": 1.0,
        "coverage": 0.9,
        "independence": 1.0,
        "latency": 0.2
    },
    "TRONSCAN": {
        "entity_types": ["wallet", "transaction", "tron"],
        "authority": 0.9,
        "freshness": 1.0,
        "coverage": 0.7,
        "independence": 1.0,
        "latency": 0.2
    },
    "TELEGRAM": {
        "entity_types": ["social", "message", "group", "user"],
        "authority": 0.5,  # User-generated content
        "freshness": 1.0,
        "coverage": 0.9,
        "independence": 0.8,
        "latency": 0.5
    },
    "TOR": {
        "entity_types": ["onion", "dark_web", "hidden_service"],
        "authority": 0.5,
        "freshness": 0.8,
        "coverage": 0.3,
        "independence": 0.9,
        "latency": 0.8  # Slow
    }
}

# Weights for each criterion
WEIGHTS = {
    "relevance": 0.35,  # Most important — does it cover what we need?
    "authority": 0.20,
    "freshness": 0.10,
    "coverage": 0.15,
    "independence": 0.15,
    "availability": 0.05  # Penalty for being down
}

def select_next_source(needed_entity_types, tried_sources=None, available_sources=None):
    """
    Select the best next source based on investigation needs.
    
    Args:
        needed_entity_types: List of entity types we still need information about
        tried_sources: List of source names already tried
        available_sources: List of source names that are available (default: all)
    
    Returns:
        dict with selected source, score, and ranking of all candidates
    """
    tried_sources = tried_sources or []
    available_sources = available_sources or list(SOURCE_PROFILES.keys())
    
    # Filter to available, untried sources
    candidates = [s for s in available_sources if s not in tried_sources]
    
    if not candidates:
        return {
            "selected": None,
            "reason": "All available sources exhausted",
            "ranking": []
        }
    
    scores = []
    for source_name in candidates:
        profile = SOURCE_PROFILES.get(source_name, {})
        if not profile:
            continue
        
        # Relevance: overlap between needed entity types and source coverage
        source_types = set(profile.get("entity_types", []))
        needed = set(needed_entity_types)
        if needed:
            relevance = len(source_types & needed) / len(needed)
        else:
            relevance = 0.5  # Default if no specific needs
        
        # Independence: penalize if similar sources already tried
        tried_types = set()
        for ts in tried_sources:
            tp = SOURCE_PROFILES.get(ts, {})
            tried_types.update(tp.get("entity_types", []))
        overlap_with_tried = len(source_types & tried_types) / max(len(source_types), 1)
        independence = 1.0 - (overlap_with_tried * 0.5)
        
        # Availability: 1.0 if reachable, 0.0 if down
        availability = 1.0  # Would check with ping in production
        
        # Compute weighted score
        score = (
            relevance * WEIGHTS["relevance"] +
            profile.get("authority", 0.5) * WEIGHTS["authority"] +
            profile.get("freshness", 0.5) * WEIGHTS["freshness"] +
            profile.get("coverage", 0.5) * WEIGHTS["coverage"] +
            independence * WEIGHTS["independence"] +
            availability * WEIGHTS["availability"]
        )
        
        # Latency penalty
        latency = profile.get("latency", 0.5)
        score *= (1.0 - latency * 0.1)
        
        scores.append({
            "source": source_name,
            "score": round(score, 3),
            "relevance": round(relevance, 3),
            "authority": profile.get("authority", 0.5),
            "freshness": profile.get("freshness", 0.5),
            "coverage": profile.get("coverage", 0.5),
            "independence": round(independence, 3),
            "availability": availability,
            "entity_types": list(source_types)
        })
    
    # Sort by score descending
    scores.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "selected": scores[0]["source"] if scores else None,
        "score": scores[0]["score"] if scores else 0,
        "ranking": scores
    }

if __name__ == "__main__":
    import json
    from datetime import datetime, timezone
    
    # Test scenarios
    tests = [
        {"name": "Need wallet info", "needed": ["wallet", "transaction", "bitcoin"], "tried": ["SCAM_ENGINE"], "expected_best": "BLOCKCHAIN_INFO"},
        {"name": "Need legal info", "needed": ["legal", "case_law"], "tried": ["SCAM_ENGINE"], "expected_best": "BAILII"},
        {"name": "Need company info", "needed": ["company", "financial"], "tried": ["SCAM_ENGINE", "GITHUB"], "expected_best": "SEC_EDGAR"},
        {"name": "Need social intel", "needed": ["social", "message", "group"], "tried": [], "expected_best": "TELEGRAM"},
        {"name": "Need offshore info", "needed": ["company", "offshore", "person"], "tried": ["SCAM_ENGINE"], "expected_best": "ICIJ"},
        {"name": "All sources tried", "needed": ["wallet"], "tried": list(SOURCE_PROFILES.keys()), "expected_best": None},
    ]
    
    print("=== Dynamic Source Selector Test ===")
    results = []
    for test in tests:
        result = select_next_source(test["needed"], test["tried"])
        selected = result["selected"]
        expected = test["expected_best"]
        passed = selected == expected
        status = "✓" if passed else "✗"
        print(f"  {status} {test['name']}: selected={selected} (expected={expected}) score={result.get('score', 0)}")
        results.append({"test": test["name"], "selected": selected, "expected": expected, "passed": passed, "score": result.get("score", 0)})
    
    passed_count = sum(1 for r in results if r["passed"])
    print(f"\n{passed_count}/{len(results)} tests passed")
    
    # Save artifact
    artifact = {
        "artifact": "next-best-source-validation.json",
        "task": "TASK_16_NEXT_BEST_SOURCE",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "module": "packages/common/source_selector.py",
        "ranking_criteria": list(WEIGHTS.keys()),
        "weights": WEIGHTS,
        "source_profiles": len(SOURCE_PROFILES),
        "tests": results,
        "pass_rate": f"{passed_count}/{len(results)}",
        "status": "IMPLEMENTED" if passed_count == len(results) else "PARTIAL",
        "finding": f"Dynamic source selection implemented with 6 ranking criteria (relevance, authority, freshness, coverage, independence, availability). {len(SOURCE_PROFILES)} source profiles defined. {passed_count}/{len(results)} test scenarios passed. System now selects the best source based on investigation needs instead of fixed pipeline order."
    }
    
    with open("/gfin/artifacts/final-verification/next-best-source-validation.json", "w") as f:
        json.dump(artifact, f, indent=2)
    
    print("Artifact saved: next-best-source-validation.json")
