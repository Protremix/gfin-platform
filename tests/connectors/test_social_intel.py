import json, sys, importlib.util, time

sys.path.insert(0, '/gfin/packages/connectors')
spec_base = importlib.util.spec_from_file_location("base", "/gfin/packages/connectors/base.py")
base_module = importlib.util.module_from_spec(spec_base)
sys.modules["base"] = base_module
spec_base.loader.exec_module(base_module)

spec = importlib.util.spec_from_file_location("social_intel", "/gfin/packages/connectors/social_intel.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["social_intel"] = mod
spec.loader.exec_module(mod)

results = {"tests": [], "passed": 0, "failed": 0}
def record(name, passed, details=""):
    results["tests"].append({"test": name, "passed": passed, "details": details[:200]})
    if passed: results["passed"] += 1
    else: results["failed"] += 1

# === LIVE TESTS (free, no auth) ===

# 1. Telegram public channel search — live test
conn = mod.TelegramPublicConnector()
result = conn.query(channel="durov")
record("telegram_public_live", result.success, f"Messages: {result.data.get('messages_found',0) if isinstance(result.data, dict) else 'N/A'}")

# 2. Reddit search — live test
conn = mod.RedditConnector()
result = conn.query(search_term="fraud scam company")
record("reddit_live", result.success, f"Posts: {result.data.get('posts_found',0) if isinstance(result.data, dict) else 'N/A'}")

# 3. Reddit user lookup — live test
result = conn.query(username="spez")
record("reddit_user_live", result.success, f"Success: {result.success}")

# 4. Mastodon search — live test
conn = mod.MastodonConnector()
result = conn.query(search_term="fraud")
record("mastodon_live", result.success, f"Accounts: {result.data.get('accounts_found',0) if isinstance(result.data, dict) else 'N/A'}")

# 5. ThreatFox — live test (free, no auth)
conn = mod.ThreatFoxConnector()
result = conn.query(search_term="192.168.1.1")
record("threatfox_live", result.success, f"Found: {result.data.get('found',False) if isinstance(result.data, dict) else 'N/A'}")

# 6. URLHaus — live test (free, no auth)
conn = mod.URLHausConnector()
result = conn.query(domain="example.com")
record("urlhaus_live", result.success, f"URLs: {result.data.get('malicious_urls_found',0) if isinstance(result.data, dict) else 'N/A'}")

# 7. URLScan.io — live test (search is free)
conn = mod.URLScanConnector()
result = conn.query(domain="google.com")
record("urlscan_live", result.success, f"Scans: {result.data.get('scans_found',0) if isinstance(result.data, dict) else 'N/A'}")

# 8. Wayback social — live test
conn = mod.WaybackSocialConnector()
result = conn.query(url="facebook.com/smartstar")
record("wayback_social_live", result.success, f"Captures: {result.data.get('captures_found',0) if isinstance(result.data, dict) else 'N/A'}")

# === AUTH-REQUIRED TESTS (should fail closed) ===

# 9. Telegram Bot API — auth test
conn = mod.TelegramBotConnector()
result = conn.query(chat_id="@test")
record("telegram_bot_auth", not result.success and "AUTH" in str(result.error), "Correctly returned AUTH_REQUIRED")

# 10. VK — auth test
conn = mod.VKConnector()
result = conn.query(search_term="test")
record("vk_auth", not result.success and "AUTH" in str(result.error), "Correctly returned AUTH_REQUIRED")

# 11. Discord — auth test
conn = mod.DiscordConnector()
result = conn.query(user_id="123")
record("discord_auth", not result.success and "AUTH" in str(result.error), "Correctly returned AUTH_REQUIRED")

# 12. HIBP — auth test
conn = mod.HaveIBeenPwnedConnector()
result = conn.query(email="test@test.com")
record("hibp_auth", not result.success and "AUTH" in str(result.error), "Correctly returned AUTH_REQUIRED")

# 13. Facebook — auth test
conn = mod.FacebookConnector()
result = conn.query(page_name="test")
record("facebook_auth", not result.success and "AUTH" in str(result.error), "Correctly returned AUTH_REQUIRED")

# 14. Twitter/X — auth test
conn = mod.TwitterConnector()
result = conn.query(search_term="test")
record("twitter_auth", not result.success and "AUTH" in str(result.error), "Correctly returned AUTH_REQUIRED")

# 15. WhatsApp — limited functionality test
conn = mod.WhatsAppConnector()
result = conn.query(phone="+447451261353")
record("whatsapp_limited", not result.success and "LIMITED" in str(result.authorization_status), "Correctly returned LIMITED (no public API)")

# === SECURITY TESTS ===
for name in mod.SOCIAL_INTEL_REGISTRY:
    conn_cls = mod.SOCIAL_INTEL_REGISTRY[name]
    conn = conn_cls()
    if conn.credential_type != "NONE":
        result = conn.query(search_term="test", channel="test", domain="test.com", email="test@test.com", invite_code="test", phone="+1234567890")
        fail_closed = not result.success and ("AUTH" in str(result.error) or "LIMITED" in str(result.authorization_status) or "AUTH" in str(result.authorization_status))
        record(f"security_{name}", fail_closed, "Fail-closed verified")
    else:
        record(f"security_{name}", True, "No auth required — public data only")

print(json.dumps(results, indent=2))
