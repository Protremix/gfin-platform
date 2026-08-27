"""GFIN Brain service — central AI reasoning brain.

Uses lazy imports to avoid import chain issues during test collection.
"""
__all__ = [
    "BrainOrchestrator", "ContextEngine", "DecisionEngine",
    "ToolRouter", "StateManager", "BrainState",
    "ConflictResolver", "BrainHealth",
]

def __getattr__(name):
    if name == "BrainOrchestrator":
        from packages.services.brain.orchestrator import BrainOrchestrator
        return BrainOrchestrator
    if name == "ContextEngine":
        from packages.services.brain.context import ContextEngine
        return ContextEngine
    if name == "DecisionEngine":
        from packages.services.brain.decision import DecisionEngine
        return DecisionEngine
    if name == "ToolRouter":
        from packages.services.brain.tool_router import ToolRouter
        return ToolRouter
    if name == "StateManager":
        from packages.services.brain.state import StateManager
        return StateManager
    if name == "BrainState":
        from packages.brain.schemas import BrainState
        return BrainState
    if name == "ConflictResolver":
        from packages.services.brain.conflict import ConflictResolver
        return ConflictResolver
    if name == "BrainHealth":
        from packages.services.brain.health import BrainHealth
        return BrainHealth
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
