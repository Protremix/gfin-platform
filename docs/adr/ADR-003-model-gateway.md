# ADR-003: Model Gateway for AI Provider Independence

**Date:** 2026-08-25
**Status:** ACCEPTED
**Context:** GFIN requires AI capabilities for fraud analysis, entity extraction, and investigation orchestration. Hard-coding to a single AI provider would create vendor lock-in and violate the Constitution's principle of provider independence.

**Decision:** Implement a Model Gateway abstraction layer that routes AI requests through a unified interface. The gateway supports multiple providers:
- OpenAI (gpt-5.6-luna) — primary engineering model
- Local/open-source models — for cost-sensitive or privacy-sensitive operations
- Other approved providers — added through the gateway adapter pattern

The gateway handles:
- Request routing and fallback
- Classification-aware model selection
- Rate limiting and retry
- Token tracking and cost attribution
- Empty content retry (for reasoning models)

**Rationale:**
- Constitution Article on Provider Independence mandates no hard-coded provider dependencies
- Different tasks may benefit from different models (reasoning vs. extraction vs. classification)
- Cost and latency optimization through provider selection
- Risk mitigation if a provider becomes unavailable

**Consequences:**
- All AI operations go through ModelRequest/ModelResponse interfaces
- Provider adapters implement the gateway interface
- The OpenAI adapter (gpt-5.6-luna) is the only currently implemented adapter (17 tests)
- Additional adapters (Anthropic, local Llama, etc.) can be added without application changes
- The gateway itself is tested and verified as part of Module 01/19/20
