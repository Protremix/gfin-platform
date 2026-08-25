# GFIN Search Platform — Module 07
#
# Per Master Spec §11 (Search Platform):
# Support: exact, normalized, fuzzy, semantic, entity, graph-assisted,
# campaign, infrastructure, and report search.
# All search results must respect authorization and data-sharing policies.

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from schemas.base import utc_now
from schemas.enums import DataClassification

# ═══════════════════════════════════════════════
# SEARCH QUERY TYPES
# ═══════════════════════════════════════════════


class SearchType(str, Enum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    ENTITY = "entity"
    GRAPH_ASSISTED = "graph_assisted"
    CAMPAIGN = "campaign"
    INFRASTRUCTURE = "infrastructure"
    REPORT = "report"


class AuthorizationContext(BaseModel):
    user_id: str
    user_classification_level: DataClassification = DataClassification.PUBLIC
    user_role: str = "public"
    organization_id: str | None = None
    jurisdiction: str | None = None
    purpose: str | None = None
    recipient_organization: str | None = None

    model_config = {"use_enum_values": True}


class DataSharingPolicy(BaseModel):
    policy_id: str = "DSP-DEFAULT"
    policy_version: str = "1.0"
    approved_purposes: list[str] = Field(
        default_factory=lambda: [
            "fraud_investigation",
            "law_enforcement",
            "research",
            "compliance",
            "internal_review",
        ]
    )
    allowed_jurisdictions: list[str] = Field(default_factory=list)
    no_share_fields: list[str] = Field(default_factory=list)
    named_partners: list[str] = Field(default_factory=list)
    allow_public_access: bool = True

    model_config = {"use_enum_values": True}


class PolicyDecision(BaseModel):
    policy_id: str
    policy_version: str
    entity_id: str
    decision: str
    reason: str
    requester: str
    purpose: str | None
    timestamp: datetime = Field(default_factory=utc_now)

    model_config = {"use_enum_values": True}


class SearchQueryV2(BaseModel):
    query: str
    search_type: SearchType = SearchType.EXACT
    entity_type: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    authorization: AuthorizationContext | None = None
    fuzzy_distance: int = 2
    graph_depth: int = 2
    limit: int = 50
    offset: int = 0
    explain: bool = False

    model_config = {"use_enum_values": True}


class SearchResultV2(BaseModel):
    entity_id: str
    entity_type: str
    normalized_value: str
    raw_value: str = ""
    score: float = 1.0
    highlights: dict[str, str] = Field(default_factory=dict)
    explanation: dict[str, Any] = Field(default_factory=dict)
    related_entities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}


class SearchResponseV2(BaseModel):
    results: list[SearchResultV2] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0
    has_more: bool = False
    search_type: str = "exact"
    query_time_ms: float = 0.0
    authorized_results: int = 0
    blocked_results: int = 0

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# LEVENSHTEIN DISTANCE
# ═══════════════════════════════════════════════


def levenshtein(s1: str, s2: str, max_dist: int | None = None) -> int:
    if s1 == s2:
        return 0
    len1, len2 = len(s1), len(s2)
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1
    prev_row = list(range(len2 + 1))
    for i in range(1, len1 + 1):
        curr_row = [i] + [0] * len2
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr_row[j] = min(prev_row[j] + 1, curr_row[j - 1] + 1, prev_row[j - 1] + cost)
        if max_dist is not None and min(curr_row) > max_dist:
            return max_dist + 1
        prev_row = curr_row
    return prev_row[len2]


def normalize_query(text: str) -> str:
    import re

    text = text.lower().strip()
    text = re.sub(r"[^\w\s@.+\-]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str) -> list[str]:
    normalized = normalize_query(text)
    if not normalized:
        return []
    return normalized.replace("-", " ").split()


# ═══════════════════════════════════════════════
# AUTHORIZATION
# ═══════════════════════════════════════════════

_CLASSIFICATION_LEVELS = {
    DataClassification.PUBLIC: 0,
    DataClassification.COMMUNITY: 1,
    DataClassification.RESTRICTED: 2,
    DataClassification.LAW_ENFORCEMENT: 3,
    DataClassification.HIGHLY_RESTRICTED: 4,
}


def can_access(entity_classification, entity_org_id, entity_jurisdiction, auth):
    if entity_classification is None:
        return False, "Missing classification metadata — access denied (fail closed)"
    required_level = _CLASSIFICATION_LEVELS.get(entity_classification, 0)
    actor_level = _CLASSIFICATION_LEVELS.get(auth.user_classification_level, 0)
    if actor_level < required_level:
        return False, f"Insufficient classification: requires {entity_classification}"
    if entity_org_id and auth.organization_id:
        if entity_org_id != auth.organization_id and auth.user_role != "admin":
            return False, "Organization isolation — different organization"
    if (
        entity_classification == DataClassification.LAW_ENFORCEMENT.value
        and auth.user_role not in ("admin", "investigator")
        and entity_jurisdiction
        and auth.jurisdiction
        and entity_jurisdiction != auth.jurisdiction
    ):
        return False, "Jurisdiction restriction"
    return True, "Access granted"


def check_sharing_policy(entity, auth, policy):
    entity_id = getattr(entity, "id", "unknown")
    ts = utc_now()
    if auth.purpose is None:
        return (
            False,
            "No purpose provided — sharing denied",
            PolicyDecision(
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                entity_id=entity_id,
                decision="DENIED",
                reason="No purpose provided — data-sharing requires explicit purpose",
                requester=auth.user_id,
                purpose=None,
                timestamp=ts,
            ),
        )
    if auth.purpose not in policy.approved_purposes:
        return (
            False,
            f"Purpose not approved: {auth.purpose}",
            PolicyDecision(
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                entity_id=entity_id,
                decision="DENIED",
                reason=f"Purpose '{auth.purpose}' not approved",
                requester=auth.user_id,
                purpose=auth.purpose,
                timestamp=ts,
            ),
        )
    entity_class = getattr(getattr(entity, "classification", None), "classification", None)
    if hasattr(entity_class, "value"):
        entity_class = entity_class.value  # type: ignore[union-attr]
    if auth.user_role == "public" or auth.user_classification_level == DataClassification.PUBLIC:
        if entity_class and entity_class in (
            DataClassification.RESTRICTED.value,
            DataClassification.LAW_ENFORCEMENT.value,
            DataClassification.HIGHLY_RESTRICTED.value,
        ):
            if not policy.allow_public_access:
                return (
                    False,
                    "Public access denied for restricted data",
                    PolicyDecision(
                        policy_id=policy.policy_id,
                        policy_version=policy.policy_version,
                        entity_id=entity_id,
                        decision="DENIED",
                        reason=f"Public access not allowed for {entity_class} data",
                        requester=auth.user_id,
                        purpose=auth.purpose,
                        timestamp=ts,
                    ),
                )
    if policy.allowed_jurisdictions:
        entity_juris = getattr(entity, "jurisdiction", None)
        if (
            entity_juris
            and entity_juris not in policy.allowed_jurisdictions
            and auth.jurisdiction not in policy.allowed_jurisdictions
        ):
            return (
                False,
                f"Cross-border transfer denied: {entity_juris}",
                PolicyDecision(
                    policy_id=policy.policy_id,
                    policy_version=policy.policy_version,
                    entity_id=entity_id,
                    decision="DENIED",
                    reason=f"Jurisdiction {entity_juris} not in allowed jurisdictions",
                    requester=auth.user_id,
                    purpose=auth.purpose,
                    timestamp=ts,
                ),
            )
    if entity_class == DataClassification.HIGHLY_RESTRICTED.value and policy.named_partners:
        if (
            auth.organization_id
            and auth.organization_id not in policy.named_partners
            and auth.user_role != "admin"
        ):
            return (
                False,
                "Not a named partner for highly restricted data",
                PolicyDecision(
                    policy_id=policy.policy_id,
                    policy_version=policy.policy_version,
                    entity_id=entity_id,
                    decision="DENIED",
                    reason="Highly restricted data requires named partner",
                    requester=auth.user_id,
                    purpose=auth.purpose,
                    timestamp=ts,
                ),
            )
    return (
        True,
        "Sharing allowed",
        PolicyDecision(
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            entity_id=entity_id,
            decision="ALLOWED",
            reason="Data-sharing policy checks passed",
            requester=auth.user_id,
            purpose=auth.purpose,
            timestamp=ts,
        ),
    )


# ═══════════════════════════════════════════════
# ENHANCED SEARCH SERVICE
# ═══════════════════════════════════════════════


class EnhancedSearchService:
    def __init__(self, repository=None, graph_store=None, campaign_store=None, report_store=None):
        self._repo = repository
        self._graph = graph_store
        self._campaigns = campaign_store or {}
        self._reports = report_store or {}
        self._entities = {}
        self._entity_index = {}
        self._normalized_index = {}
        self._token_index = {}
        self._campaign_index = {}
        self._report_index = {}
        self._sharing_policy = DataSharingPolicy()
        self._policy_audit = []

    def set_sharing_policy(self, policy):
        self._sharing_policy = policy

    def get_policy_audit(self):
        return list(self._policy_audit)

    def index_entity(self, entity):
        eid = entity.id
        self._entities[eid] = entity
        etype = getattr(entity, "entity_type", "unknown")
        if etype not in self._entity_index:
            self._entity_index[etype] = []
        if eid not in self._entity_index[etype]:
            self._entity_index[etype].append(eid)
        nval = getattr(entity, "normalized_value", "")
        if nval:
            if nval not in self._normalized_index:
                self._normalized_index[nval] = []
            if eid not in self._normalized_index[nval]:
                self._normalized_index[nval].append(eid)
        raw_values = getattr(entity, "raw_values", [])
        all_text = " ".join([nval, *list(raw_values)])
        for token in tokenize(all_text):
            if token not in self._token_index:
                self._token_index[token] = []
            if eid not in self._token_index[token]:
                self._token_index[token].append(eid)

    def index_campaign(self, campaign):
        cid = getattr(campaign, "id", None)
        if cid:
            self._campaign_index[cid] = campaign
            self._campaigns[cid] = campaign

    def index_report(self, report):
        rid = getattr(report, "id", None)
        if rid:
            self._report_index[rid] = report
            self._reports[rid] = report

    def delete_index(self, entity_id):
        if entity_id not in self._entities:
            return False
        entity = self._entities.pop(entity_id)
        etype = getattr(entity, "entity_type", "unknown")
        if etype in self._entity_index and entity_id in self._entity_index[etype]:
            self._entity_index[etype].remove(entity_id)
        nval = getattr(entity, "normalized_value", "")
        if nval and nval in self._normalized_index:
            if entity_id in self._normalized_index[nval]:
                self._normalized_index[nval].remove(entity_id)
                if not self._normalized_index[nval]:
                    del self._normalized_index[nval]
        raw_values = getattr(entity, "raw_values", [])
        all_text = " ".join([nval, *list(raw_values)])
        for token in tokenize(all_text):
            if token in self._token_index and entity_id in self._token_index[token]:
                self._token_index[token].remove(entity_id)
                if not self._token_index[token]:
                    del self._token_index[token]
        return True

    def search(self, query):
        start_time = datetime.now()
        if query.authorization is None:
            return SearchResponseV2(
                results=[],
                total=0,
                search_type=query.search_type.value
                if hasattr(query.search_type, "value")
                else str(query.search_type),
                query_time_ms=0.0,
                authorized_results=0,
                blocked_results=0,
            )

        search_type = query.search_type
        if hasattr(search_type, "value"):
            search_type = search_type.value

        if search_type == SearchType.EXACT.value:
            raw_results = self._search_exact(query)
        elif search_type == SearchType.NORMALIZED.value:
            raw_results = self._search_normalized(query)
        elif search_type == SearchType.FUZZY.value:
            raw_results = self._search_fuzzy(query)
        elif search_type == SearchType.ENTITY.value:
            raw_results = self._search_entity(query)
        elif search_type == SearchType.GRAPH_ASSISTED.value:
            raw_results = self._search_graph_assisted(query)
        elif search_type == SearchType.CAMPAIGN.value:
            raw_results = self._search_campaign(query)
        elif search_type == SearchType.INFRASTRUCTURE.value:
            raw_results = self._search_infrastructure(query)
        elif search_type == SearchType.REPORT.value:
            raw_results = self._search_report(query)
        elif search_type == SearchType.SEMANTIC.value:
            raw_results = []
        else:
            raw_results = self._search_exact(query)

        authorized_results = []
        blocked_count = 0
        is_campaign_or_report_search = search_type in (
            SearchType.CAMPAIGN.value,
            SearchType.REPORT.value,
        )

        for entity_id, score, explanation in raw_results:
            if is_campaign_or_report_search:
                if query.authorization is not None:
                    if search_type == SearchType.REPORT.value:
                        entity = self._report_index.get(entity_id, {})
                        result = SearchResultV2(
                            entity_id=entity_id,
                            entity_type="report",
                            normalized_value=getattr(entity, "description", "")
                            or getattr(entity, "name", "")
                            or "",
                            raw_value="",
                            score=score,
                            explanation=explanation if query.explain else {},
                            metadata={"access_reason": "Authenticated campaign/report search"},
                        )
                        authorized_results.append(result)
                    else:
                        entity = self._campaign_index.get(entity_id, {})
                        result = SearchResultV2(
                            entity_id=entity_id,
                            entity_type="campaign",
                            normalized_value=getattr(entity, "name", "") or "",
                            raw_value="",
                            score=score,
                            explanation=explanation if query.explain else {},
                            metadata={"access_reason": "Authenticated campaign/report search"},
                        )
                        authorized_results.append(result)
                continue

            entity = self._entities.get(entity_id)
            if entity is None:
                continue
            entity_class = None
            classification = getattr(entity, "classification", None)
            if classification:
                entity_class = getattr(classification, "classification", None)
                if hasattr(entity_class, "value"):
                    entity_class = entity_class.value  # type: ignore[union-attr]
            entity_org = getattr(entity, "organization_id", None)
            entity_juris = getattr(entity, "jurisdiction", None)
            can, reason = can_access(entity_class, entity_org, entity_juris, query.authorization)
            if can:
                can_share, share_reason, policy_decision = check_sharing_policy(
                    entity, query.authorization, self._sharing_policy
                )
                if policy_decision:
                    self._policy_audit.append(policy_decision)
                if not can_share:
                    can = False
                    reason = share_reason
            if can:
                if not query.explain and "entity_type" not in explanation:
                    explanation = dict(explanation)
                    explanation.setdefault("entity_type", getattr(entity, "entity_type", "unknown"))
                result = SearchResultV2(
                    entity_id=entity_id,
                    entity_type=getattr(entity, "entity_type", "unknown"),
                    normalized_value=getattr(entity, "normalized_value", ""),
                    raw_value=getattr(entity, "raw_values", [""])[0]
                    if getattr(entity, "raw_values", [])
                    else "",
                    score=score,
                    explanation=explanation if query.explain else explanation,
                    related_entities=explanation.get("related_entities", []),
                    metadata={"access_reason": reason},
                )
                authorized_results.append(result)
            else:
                blocked_count += 1

        total = len(authorized_results)
        offset = query.offset
        limit = query.limit
        paginated = authorized_results[offset : offset + limit]
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        return SearchResponseV2(
            results=paginated,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
            search_type=search_type,
            query_time_ms=round(elapsed, 2),
            authorized_results=len(authorized_results),
            blocked_results=blocked_count,
        )

    def _search_exact(self, query):
        results = []
        q = query.query
        if q in self._normalized_index:
            for eid in self._normalized_index[q]:
                results.append((eid, 1.0, {"match_type": "exact", "field": "normalized_value"}))
        for eid, entity in self._entities.items():
            raw_values = getattr(entity, "raw_values", [])
            if q in raw_values and eid not in [r[0] for r in results]:
                results.append((eid, 1.0, {"match_type": "exact", "field": "raw_values"}))
        return results

    def _search_normalized(self, query):
        results = []
        norm_q = normalize_query(query.query)
        if norm_q in self._normalized_index:
            for eid in self._normalized_index[norm_q]:
                results.append((eid, 1.0, {"match_type": "normalized", "normalized_query": norm_q}))
        for nval, eids in self._normalized_index.items():
            if nval.startswith(norm_q) and nval != norm_q:
                for eid in eids:
                    score = len(norm_q) / len(nval) if nval else 0
                    if eid not in [r[0] for r in results]:
                        results.append((eid, score, {"match_type": "normalized_prefix"}))
        return results

    def _search_fuzzy(self, query):
        results = []
        norm_q = normalize_query(query.query)
        max_dist = query.fuzzy_distance
        q_tokens = tokenize(norm_q)
        max_candidates = 10000
        for candidates_checked, (nval, eids) in enumerate(self._normalized_index.items(), start=1):
            if candidates_checked > max_candidates:
                break
            dist = levenshtein(norm_q, nval, max_dist=max_dist)
            if dist <= max_dist:
                score = 1.0 - (dist / max(len(norm_q), len(nval), 1))
                for eid in eids:
                    results.append(
                        (
                            eid,
                            score,
                            {"match_type": "fuzzy", "distance": dist, "max_distance": max_dist},
                        )
                    )
        if q_tokens:
            for token, eids in self._token_index.items():
                for qt in q_tokens:
                    if token == qt:
                        for eid in eids:
                            if eid not in [r[0] for r in results]:
                                results.append(
                                    (
                                        eid,
                                        1.0,
                                        {"match_type": "fuzzy_token_exact", "matched_token": qt},
                                    )
                                )
                    else:
                        dist = levenshtein(qt, token, max_dist=max_dist)
                        if dist <= max_dist:
                            score = 1.0 - (dist / max(len(qt), len(token), 1))
                            for eid in eids:
                                if eid not in [r[0] for r in results]:
                                    results.append(
                                        (
                                            eid,
                                            score * 0.8,
                                            {
                                                "match_type": "fuzzy_token",
                                                "matched_token": token,
                                                "distance": dist,
                                            },
                                        )
                                    )
        seen: dict = {}
        for eid, score, explanation in results:
            if eid not in seen or score > seen[eid][1]:
                seen[eid] = (eid, score, explanation)
        return sorted(seen.values(), key=lambda x: -x[1])

    def _search_entity(self, query):
        results = []
        entity_type = query.entity_type or query.filters.get("entity_type")
        if entity_type and entity_type in self._entity_index:
            for eid in self._entity_index[entity_type]:
                entity = self._entities.get(eid)
                if entity is None:
                    continue
                nval = getattr(entity, "normalized_value", "")
                raw_values = getattr(entity, "raw_values", [])
                score = 0.0
                if query.query.lower() in nval.lower():
                    score = 1.0 if nval.lower() == query.query.lower() else 0.8
                elif any(query.query.lower() in rv.lower() for rv in raw_values):
                    score = 0.7
                if score > 0:
                    results.append(
                        (eid, score, {"match_type": "entity", "entity_type": entity_type})
                    )
        return results

    def _search_graph_assisted(self, query):
        initial = self._search_normalized(query)
        if not initial:
            initial = self._search_fuzzy(query)
        results = list(initial)
        seen_ids = {r[0] for r in results}
        if self._graph is not None:
            for eid, score, _ in initial:
                try:
                    import asyncio

                    loop = asyncio.new_event_loop()
                    neighbors, edges = loop.run_until_complete(
                        self._graph.get_neighbors(eid, max_depth=query.graph_depth)
                    )
                    loop.close()
                    for neighbor in neighbors:
                        if neighbor.entity_id not in seen_ids:
                            related_score = score * 0.5
                            results.append(
                                (
                                    neighbor.entity_id,
                                    related_score,
                                    {
                                        "match_type": "graph_assisted",
                                        "source_entity": eid,
                                        "graph_depth": query.graph_depth,
                                        "related_entities": [eid],
                                    },
                                )
                            )
                            seen_ids.add(neighbor.entity_id)
                except Exception:
                    pass
        return results

    def _search_campaign(self, query):
        results = []
        norm_q = normalize_query(query.query).lower()
        for cid, campaign in self._campaign_index.items():
            campaign_name = getattr(campaign, "name", "")
            campaign_desc = getattr(campaign, "fraud_type", "") or getattr(
                campaign, "description", ""
            )
            campaign_status = getattr(campaign, "campaign_status", "") or getattr(
                campaign, "status", ""
            )
            searchable = f"{campaign_name} {campaign_desc} {campaign_status}".lower()
            score = 0.0
            if norm_q and norm_q in searchable:
                if norm_q in campaign_name.lower():
                    score = 1.0
                elif norm_q in campaign_desc.lower():
                    score = 0.8
                else:
                    score = 0.6
                results.append(
                    (
                        cid,
                        score,
                        {
                            "match_type": "campaign",
                            "campaign_field": "name" if score == 1.0 else "other",
                        },
                    )
                )
        return results

    def _search_infrastructure(self, query):
        infra_types = {"IP", "DOMAIN", "URL", "ASN", "NETWORK"}
        results = []
        for etype in infra_types:
            if etype in self._entity_index:
                for eid in self._entity_index[etype]:
                    entity = self._entities.get(eid)
                    if entity is None:
                        continue
                    nval = getattr(entity, "normalized_value", "")
                    raw_values = getattr(entity, "raw_values", [])
                    score = 0.0
                    if query.query.lower() in nval.lower():
                        score = 1.0 if nval.lower() == query.query.lower() else 0.8
                    elif any(query.query.lower() in rv.lower() for rv in raw_values):
                        score = 0.7
                    if score > 0:
                        results.append(
                            (eid, score, {"match_type": "infrastructure", "entity_type": etype})
                        )
        return results

    def _search_report(self, query):
        results = []
        norm_q = normalize_query(query.query).lower()
        for rid, report in self._report_index.items():
            description = getattr(report, "description", "") or ""
            category = getattr(report, "category", "") or ""
            status = getattr(report, "status", "") or ""
            searchable = f"{description} {category} {status}".lower()
            score = 0.0
            if norm_q and norm_q in searchable:
                if norm_q in category.lower():
                    score = 1.0
                elif norm_q in description.lower():
                    score = 0.8
                else:
                    score = 0.6
                results.append(
                    (
                        rid,
                        score,
                        {
                            "match_type": "report",
                            "report_field": "category" if score == 1.0 else "other",
                        },
                    )
                )
        return results

    def get_metrics(self):
        return {
            "total_entities": len(self._entities),
            "total_campaigns": len(self._campaign_index),
            "total_reports": len(self._report_index),
            "entity_type_count": len(self._entity_index),
            "normalized_index_size": len(self._normalized_index),
            "token_index_size": len(self._token_index),
        }
