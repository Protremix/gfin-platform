import sys, inspect
sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")
sys.path.insert(0, "/gfin/packages")

print("=== SearchType ===")
from search_platform import SearchType
print([e.value for e in SearchType])

print("\n=== EvidenceVault.list ===")
from evidence_vault import EvidenceVault
print(inspect.signature(EvidenceVault.list))

print("\n=== ComplianceService ===")
from compliance import ComplianceService
for name in ["check_count", "violation_count", "unresolved_violation_count"]:
    attr = inspect.getattr_static(ComplianceService, name, None)
    print(f"  {name}: {type(attr).__name__}")

print("\n=== SubscriptionService.list_subscriptions ===")
from continuous_monitoring import SubscriptionService
print(inspect.signature(SubscriptionService.list_subscriptions))

print("\n=== CampaignEngine methods ===")
from campaign_engine import CampaignEngine
print([m for m in dir(CampaignEngine) if not m.startswith('_')])

print("\n=== CampaignScorer methods ===")
from campaign_engine import CampaignScorer
print([m for m in dir(CampaignScorer) if not m.startswith('_')])

print("\n=== CampaignDetector methods ===")
from campaign_engine import CampaignDetector
print([m for m in dir(CampaignDetector) if not m.startswith('_')])

print("\n=== EnhancedSearchService methods ===")
from search_platform import EnhancedSearchService
print([m for m in dir(EnhancedSearchService) if not m.startswith('_')])

print("\n=== EarlyWarningEngine methods ===")
from early_warning import EarlyWarningEngine
print([m for m in dir(EarlyWarningEngine) if not m.startswith('_')])

print("\n=== GlobalEntityIndex methods ===")
from global_matching import GlobalEntityIndex
print([m for m in dir(GlobalEntityIndex) if not m.startswith('_')])

print("\n=== PoliceConsoleService methods ===")
from police_console import PoliceConsoleService
print([m for m in dir(PoliceConsoleService) if not m.startswith('_')])

print("\n=== InvestigationPlan ===")
from investigation_orchestrator import InvestigationPlan
print(inspect.signature(InvestigationPlan))

print("\n=== ChangeDetector methods ===")
from continuous_monitoring import ChangeDetector
print([m for m in dir(ChangeDetector) if not m.startswith('_')])

print("\n=== ComplianceService methods ===")
print([m for m in dir(ComplianceService) if not m.startswith('_')])
