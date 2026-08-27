#!/usr/bin/env python3
"""Integration script: wire module route batches into gfin_server.py"""

content = open("/gfin/gfin_server.py").read()

# Check if already integrated
if "register_batch1_routes" in content:
    print("Module routes already integrated")
    exit(0)

# Add integration code before the `if __name__` block
integration_code = '''
# ============================================================
# MODULE API ROUTES — Batch Integration (11 modules)
# ============================================================

try:
    from module_routes_batch1 import register_batch1_routes
    register_batch1_routes(app, auth_police, auth_police_admin, rate_limiter)
    print("✅ Batch 1 routes loaded: evidence_vault, fraud_graph, search_platform, compliance")
except Exception as e:
    print(f"Warning: batch 1 routes not loaded: {e}")

try:
    from module_routes_batch2 import register_batch2_routes
    register_batch2_routes(app, auth_police, auth_police_admin, rate_limiter)
    print("✅ Batch 2 routes loaded: campaign_engine, global_matching, early_warning, continuous_monitoring")
except Exception as e:
    print(f"Warning: batch 2 routes not loaded: {e}")

try:
    from module_routes_batch3 import register_batch3_routes
    register_batch3_routes(app, auth_police, auth_police_admin, rate_limiter)
    print("✅ Batch 3 routes loaded: investigation_orchestrator, police_console, entity_resolution")
except Exception as e:
    print(f"Warning: batch 3 routes not loaded: {e}")

'''

# Insert before if __name__ == "__main__"
content = content.replace(
    'if __name__ == "__main__":',
    integration_code + '\nif __name__ == "__main__":'
)

open("/gfin/gfin_server.py", "w").write(content)
print(f"Integration code added to gfin_server.py ({len(content.splitlines())} lines)")
