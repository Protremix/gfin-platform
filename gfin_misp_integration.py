#!/usr/bin/env python3
"""
GFIN MISP Integration Module — Threat Intelligence Sharing
Enables inter-agency sharing of IOCs, evidence, and threat intelligence
via the MISP (Malware Information Sharing Platform) standard.
Can share to a MISP instance or export STIX 2.1 format for federation.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

class GFINMISPIntegration:
    """Bridge GFIN cases to MISP-compatible threat intel sharing"""
    
    def __init__(self):
        self.misp_url = os.environ.get("MISP_URL", "")
        self.misp_key = os.environ.get("MISP_KEY", "")
        self.misp_verifycert = False
        self._client = None
    
    def _get_client(self):
        """Get or create MISP client"""
        if self._client:
            return self._client
        if not self.misp_url or not self.misp_key:
            return None
        try:
            from pymisp import PyMISP
            self._client = PyMISP(self.misp_url, self.misp_key, self.misp_verifycert)
            return self._client
        except Exception as e:
            print(f"MISP connection error: {e}")
            return None
    
    def case_to_misp_event(self, case: Dict) -> Dict:
        """Convert a GFIN case to a MISP event structure"""
        event = {
            "Event": {
                "info": f"GFIN Case {case.get('case_id', '')}: {case.get('summary', case.get('target', ''))[:200]}",
                "threat_level_id": self._threat_level(case),
                "analysis": self._analysis_level(case),
                "distribution": 0,  # Only your organization
                "tags": self._case_to_tags(case),
                "Attribute": [],
                "Galaxy": [],
                "date": datetime.now().strftime("%Y-%m-%d"),
                "Attribute": self._case_to_attributes(case),
            }
        }
        return event
    
    def _threat_level(self, case: Dict) -> int:
        """Map GFIN confidence to MISP threat level (1=high, 2=medium, 3=low, 4=undefined)"""
        conf = case.get("confidence", 0)
        if conf >= 0.8:
            return 1  # High
        elif conf >= 0.5:
            return 2  # Medium
        elif conf > 0:
            return 3  # Low
        return 4  # Undefined
    
    def _analysis_level(self, case: Dict) -> int:
        """Map GFIN status to MISP analysis level"""
        status = case.get("status", "").upper()
        if status in ("CLOSED", "COMPLETED"):
            return 2  # Completed
        elif status in ("INVESTIGATING", "ACTIVE"):
            return 1  # Ongoing
        return 0  # Initial
    
    def _case_to_tags(self, case: Dict) -> List[Dict]:
        """Convert GFIN case tags to MISP tag format"""
        tags = []
        tags.append({"name": "GFIN", "exportable": True})
        
        classification = case.get("classification", "")
        if classification:
            tags.append({"name": f"GFIN:class=\"{classification}\"", "exportable": True})
        
        for pattern in case.get("scam_patterns", []):
            if isinstance(pattern, str):
                tags.append({"name": f"GFIN:scam-pattern=\"{pattern}\"", "exportable": True})
        
        if case.get("victim_count", 0) > 0:
            tags.append({"name": f"GFIN:victims=\"{case['victim_count']}\"", "exportable": True})
        
        return tags
    
    def _case_to_attributes(self, case: Dict) -> List[Dict]:
        """Extract IOCs from GFIN case as MISP attributes"""
        attrs = []
        now = datetime.now().strftime("%Y-%m-%d")
        
        # Domains
        for di in case.get("digital_identifiers", []):
            if isinstance(di, dict) and di.get("type") == "domain":
                attrs.append({
                    "category": "Network activity",
                    "type": "domain",
                    "value": di.get("value", ""),
                    "comment": f"GFIN case {case.get('case_id', '')} — domain indicator",
                    "to_ids": False,
                    "date": now
                })
            elif isinstance(di, dict) and di.get("type") == "ip":
                attrs.append({
                    "category": "Network activity",
                    "type": "ip-dst",
                    "value": di.get("value", ""),
                    "comment": f"GFIN case {case.get('case_id', '')} — IP indicator",
                    "to_ids": False,
                    "date": now
                })
            elif isinstance(di, dict) and di.get("type") == "url":
                attrs.append({
                    "category": "Network activity",
                    "type": "url",
                    "value": di.get("value", ""),
                    "comment": f"GFIN case {case.get('case_id', '')} — URL indicator",
                    "to_ids": False,
                    "date": now
                })
        
        # Wallets
        for fi in case.get("financial_indicators", []):
            if isinstance(fi, dict) and fi.get("type", "").startswith("wallet"):
                wallet_type = fi.get("type", "")
                attrs.append({
                    "category": "Financial fraud",
                    "type": "btc" if "btc" in wallet_type else "xmr" if "xmr" in wallet_type else "other",
                    "value": fi.get("value", ""),
                    "comment": f"GFIN case {case.get('case_id', '')} — crypto wallet ({wallet_type})",
                    "to_ids": False,
                    "date": now
                })
            elif isinstance(fi, dict) and fi.get("type") == "phone":
                attrs.append({
                    "category": "Social network",
                    "type": "phone-number",
                    "value": fi.get("value", ""),
                    "comment": f"GFIN case {case.get('case_id', '')} — phone number",
                    "to_ids": False,
                    "date": now
                })
        
        return attrs
    
    def export_stix(self, case: Dict) -> Dict:
        """Export GFIN case as STIX 2.1 bundle (no MISP instance needed)"""
        bundle = {
            "type": "bundle",
            "id": f"bundle--{case.get('case_id', 'unknown')}",
            "objects": []
        }
        
        # Report object
        report = {
            "type": "report",
            "spec_version": "2.1",
            "id": f"report--{case.get('case_id', 'unknown')}",
            "created": case.get("created_date", datetime.now().isoformat()),
            "modified": datetime.now().isoformat(),
            "name": f"GFIN Investigation: {case.get('target', case.get('case_id', ''))}",
            "description": case.get("summary", ""),
            "report_types": ["fraud-report"],
            "published": datetime.now().isoformat(),
            "object_refs": []
        }
        
        # Indicator objects
        for di in case.get("digital_identifiers", []):
            if isinstance(di, dict):
                indicator_type = di.get("type", "")
                pattern_val = di.get("value", "")
                if indicator_type == "domain":
                    pattern = f"[domain-name:value = '{pattern_val}']"
                    stix_type = "domain-name"
                elif indicator_type == "ip":
                    pattern = f"[ipv4-addr:value = '{pattern_val}']"
                    stix_type = "ipv4-addr"
                elif indicator_type == "url":
                    pattern = f"[url:value = '{pattern_val}']"
                    stix_type = "url"
                else:
                    continue
                
                indicator_id = f"indicator--{pattern_val.replace('.', '-')}-{case.get('case_id', '')}"
                indicator = {
                    "type": "indicator",
                    "spec_version": "2.1",
                    "id": indicator_id,
                    "created": case.get("created_date", datetime.now().isoformat()),
                    "modified": datetime.now().isoformat(),
                    "name": pattern_val,
                    "pattern": pattern,
                    "pattern_type": "stix",
                    "valid_from": case.get("created_date", datetime.now().isoformat()),
                    "labels": [case.get("classification", "fraud")] + case.get("scam_patterns", []) if isinstance(case.get("scam_patterns"), list) else ["fraud"]
                }
                bundle["objects"].append(indicator)
                report["object_refs"].append(indicator_id)
        
        # Wallet as observed data
        for fi in case.get("financial_indicators", []):
            if isinstance(fi, dict) and fi.get("type", "").startswith("wallet"):
                wallet_id = f"observed-data--wallet-{fi.get('value', '')[:20]}"
                observed = {
                    "type": "observed-data",
                    "spec_version": "2.1",
                    "id": wallet_id,
                    "created": case.get("created_date", datetime.now().isoformat()),
                    "modified": datetime.now().isoformat(),
                    "first_observed": case.get("created_date", datetime.now().isoformat()),
                    "last_observed": datetime.now().isoformat(),
                    "number_observed": case.get("victim_count", 1),
                    "objects": {
                        "0": {
                            "type": "cryptocurrency-wallet",
                            "value": fi.get("value", ""),
                            "currency": fi.get("type", "").replace("wallet_", "")
                        }
                    }
                }
                bundle["objects"].append(observed)
                report["object_refs"].append(wallet_id)
        
        bundle["objects"].append(report)
        return bundle
    
    async def share_case_to_misp(self, case: Dict) -> Dict:
        """Push a GFIN case to a configured MISP instance"""
        client = self._get_client()
        if not client:
            return {"success": False, "error": "MISP not configured. Set MISP_URL and MISP_KEY environment variables."}
        
        from pymisp import MISPEvent
        event_data = self.case_to_misp_event(case)
        
        try:
            misp_event = MISPEvent()
            misp_event.from_dict(**event_data["Event"])
            result = client.add_event(misp_event)
            return {"success": True, "misp_event_id": result.id if hasattr(result, 'id') else None}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_status(self) -> Dict:
        """Get MISP integration status"""
        return {
            "configured": bool(self.misp_url and self.misp_key),
            "misp_url": self.misp_url or "Not configured",
            "stix_export": True,  # Always available — no MISP needed
            "misp_sharing": bool(self.misp_url and self.misp_key)
        }


# Singleton
misp_integration = GFINMISPIntegration()
