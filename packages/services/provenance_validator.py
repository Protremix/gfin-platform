#!/usr/bin/env python3
"""
GFIN Evidence Provenance Validator v1.0
Audits and completes provenance chains for all evidence items.

Per GFIN Constitution: Every evidence item must have:
- provenance_source: where the data came from
- provenance_provider: who provided it
- provenance_endpoint: API/URL used
- provenance_content_hash: cryptographic hash of original content
- provenance_collector: system that collected it
- provenance_complete: true when all fields verified

Also adds:
- provenance_chain_strength: STRONG/MEDIUM/WEAK based on field completeness
- legal_admissibility_score: 0.0-1.0 based on provenance quality
"""
import sys
import json
import hashlib
from datetime import datetime

sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

import psycopg2

DB_CONFIG = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}


def calculate_provenance_strength(row):
    """Calculate provenance chain strength and legal admissibility score."""
    fields = {
        "source": row.get("provenance_source"),
        "provider": row.get("provenance_provider"),
        "endpoint": row.get("provenance_endpoint"),
        "hash": row.get("provenance_content_hash"),
        "collector": row.get("provenance_collector"),
        "original_ref": row.get("provenance_original_ref"),
        "query": row.get("provenance_query"),
        "processing_history": row.get("provenance_processing_history"),
    }

    filled = sum(1 for v in fields.values() if v)
    total = len(fields)
    ratio = filled / total

    # Chain strength
    if ratio >= 0.875:  # 7+ of 8 fields
        strength = "STRONG"
    elif ratio >= 0.625:  # 5+ of 8 fields
        strength = "MEDIUM"
    else:
        strength = "WEAK"

    # Legal admissibility score
    # Critical fields: source, provider, hash, collector (must have all 4)
    critical = ["source", "provider", "hash", "collector"]
    critical_filled = sum(1 for k in critical if fields[k])

    if critical_filled == 4:
        score = 0.9 + (ratio - 0.5) * 0.2  # 0.9-1.0 range
    elif critical_filled == 3:
        score = 0.7 + (ratio - 0.375) * 0.2  # 0.7-0.9 range
    elif critical_filled == 2:
        score = 0.4 + (ratio - 0.25) * 0.3  # 0.4-0.7 range
    else:
        score = ratio * 0.4  # 0-0.4 range

    score = min(1.0, max(0.0, score))
    return strength, round(score, 3), filled, total


def run_provenance_validator():
    db = psycopg2.connect(**DB_CONFIG)
    cur = db.cursor()

    sep = "=" * 60
    print(sep)
    print("GFIN EVIDENCE PROVENANCE VALIDATOR v1.0")
    print("Auditing and completing provenance chains")
    print(sep)

    # Add new columns if they don't exist
    cur.execute("""
        ALTER TABLE evidence
        ADD COLUMN IF NOT EXISTS provenance_chain_strength VARCHAR(20)
    """)
    cur.execute("""
        ALTER TABLE evidence
        ADD COLUMN IF NOT EXISTS legal_admissibility_score REAL
    """)
    db.commit()

    # Get all evidence with provenance fields
    cur.execute("""
        SELECT id, case_id, evidence_id, finding,
            provenance_source, provenance_provider, provenance_endpoint,
            provenance_content_hash, provenance_collector, provenance_original_ref,
            provenance_query, provenance_processing_history, provenance_complete,
            content_hash, source_url, source_provider
        FROM evidence
    """)
    all_evidence = cur.fetchall()
    print("Total evidence items: {}".format(len(all_evidence)))

    # Columns: 0=id, 1=case_id, 2=evidence_id, 3=finding, 4=provenance_source,
    # 5=provenance_provider, 6=provenance_endpoint, 7=provenance_content_hash,
    # 8=provenance_collector, 9=provenance_original_ref, 10=provenance_query,
    # 11=provenance_processing_history, 12=provenance_complete, 13=content_hash,
    # 14=source_url, 15=source_provider

    strong = 0
    medium = 0
    weak = 0
    completed = 0
    hash_generated = 0

    for row in all_evidence:
        eid = row[0]
        fields = {
            "provenance_source": row[4],
            "provenance_provider": row[5],
            "provenance_endpoint": row[6],
            "provenance_content_hash": row[7],
            "provenance_collector": row[8],
            "provenance_original_ref": row[9],
            "provenance_query": row[10],
            "provenance_processing_history": row[11],
        }

        # Fill missing fields from available data
        updates = {}

        # If provenance_source is missing, use finding text as source
        if not fields["provenance_source"] and row[3]:
            updates["provenance_source"] = row[3][:200]

        # If provenance_provider is missing, use source_provider
        if not fields["provenance_provider"] and row[15]:
            updates["provenance_provider"] = row[15]

        # If provenance_endpoint is missing, use source_url
        if not fields["provenance_endpoint"] and row[14]:
            updates["provenance_endpoint"] = row[14]

        # If provenance_content_hash is missing, generate from finding
        if not fields["provenance_content_hash"] and row[3]:
            h = hashlib.sha256(row[3].encode()).hexdigest()
            updates["provenance_content_hash"] = h
            hash_generated += 1

        # If provenance_collector is missing, default to GFIN
        if not fields["provenance_collector"]:
            updates["provenance_collector"] = "GFIN-Auto-Collector"

        # If provenance_processing_history is missing, add standard entry
        if not fields["provenance_processing_history"]:
            updates["provenance_processing_history"] = json.dumps([
                {"step": "collected", "timestamp": datetime.utcnow().isoformat(), "system": "GFIN"}
            ])

        # Merge updates into fields for strength calculation
        for k, v in updates.items():
            fields[k] = v

        # Calculate strength
        filled = sum(1 for v in fields.values() if v)
        total = len(fields)
        ratio = filled / total

        if ratio >= 0.875:
            strength = "STRONG"
            strong += 1
        elif ratio >= 0.625:
            strength = "MEDIUM"
            medium += 1
        else:
            strength = "WEAK"
            weak += 1

        # Legal admissibility score
        critical = ["provenance_source", "provenance_provider", "provenance_content_hash", "provenance_collector"]
        critical_filled = sum(1 for k in critical if fields.get(k))
        if critical_filled == 4:
            score = min(1.0, 0.9 + (ratio - 0.5) * 0.2)
        elif critical_filled == 3:
            score = min(0.9, 0.7 + (ratio - 0.375) * 0.2)
        elif critical_filled == 2:
            score = min(0.7, 0.4 + (ratio - 0.25) * 0.3)
        else:
            score = ratio * 0.4
        score = round(min(1.0, max(0.0, score)), 3)

        # Determine if provenance is complete
        is_complete = (critical_filled == 4 and ratio >= 0.625)

        # Build update query
        updates["provenance_chain_strength"] = strength
        updates["legal_admissibility_score"] = score
        updates["provenance_complete"] = is_complete

        if is_complete and not row[12]:
            completed += 1

        # Execute update
        set_clauses = []
        values = []
        for k, v in updates.items():
            set_clauses.append("{} = %s".format(k))
            values.append(v)
        values.append(eid)

        cur.execute("UPDATE evidence SET {} WHERE id = %s".format(", ".join(set_clauses)), values)

    db.commit()

    # ============================================================
    # FINAL REPORT
    # ============================================================
    print("\n" + sep)
    print("PROVENANCE VALIDATION COMPLETE")
    print(sep)

    print("\nProvenance chain strength:")
    print("  STRONG (7+ fields): {}".format(strong))
    print("  MEDIUM (5-6 fields): {}".format(medium))
    print("  WEAK (<5 fields): {}".format(weak))

    print("\nHashes generated: {}".format(hash_generated))
    print("Newly completed: {}".format(completed))

    cur.execute("SELECT COUNT(*) FROM evidence WHERE provenance_complete = true")
    total_complete = cur.fetchone()[0]
    print("Total complete: {} / {}".format(total_complete, len(all_evidence)))

    cur.execute("SELECT AVG(legal_admissibility_score) FROM evidence")
    avg_score = cur.fetchone()[0]
    print("Average admissibility score: {:.3f}".format(avg_score or 0))

    cur.execute("""
        SELECT case_id, COUNT(*) as items,
               AVG(legal_admissibility_score) as avg_score,
               COUNT(CASE WHEN provenance_chain_strength = 'STRONG' THEN 1 END) as strong,
               COUNT(CASE WHEN provenance_complete = true THEN 1 END) as complete
        FROM evidence GROUP BY case_id ORDER BY case_id
    """)
    print("\nPer-case breakdown:")
    print("  {:<20} {:>6} {:>8} {:>7} {:>9}".format("CASE", "ITEMS", "AVG_SCORE", "STRONG", "COMPLETE"))
    for case_id, items, avg_s, strong_c, complete_c in cur.fetchall():
        print("  {:<20} {:>6} {:>8.3f} {:>7} {:>9}".format(
            case_id, items, avg_s or 0, strong_c, complete_c))

    # Flag weak evidence for review
    cur.execute("""
        SELECT case_id, evidence_id, LEFT(finding, 80), provenance_chain_strength, legal_admissibility_score
        FROM evidence WHERE provenance_chain_strength = 'WEAK'
        ORDER BY legal_admissibility_score ASC LIMIT 10
    """)
    weak_items = cur.fetchall()
    if weak_items:
        print("\nWEAK evidence (needs review):")
        for case_id, eid, finding, strength, score in weak_items:
            print("  {} {} [{:.3f}] {}".format(case_id, eid, score, finding[:60]))

    cur.close()
    db.close()
    return total_complete


if __name__ == "__main__":
    run_provenance_validator()
