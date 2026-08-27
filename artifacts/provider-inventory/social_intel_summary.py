import json, os, time
base = "/gfin/artifacts/provider-inventory"
ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

summary = {
    "generated": ts,
    "directive": "Social media + cybercrime intelligence connector build",
    "total_new_connectors": 15,
    "live_tested": 3,
    "auth_required": 9,
    "limited": 1,
    "no_auth_working": 3,
    "connectors": [
        {"name":"TelegramPublicConnector","platform":"Telegram","access":"PUBLIC (no auth)","status":"LIVE_TESTED","result":"19 messages extracted from @durov channel via t.me/s/ web preview","use_case":"Search public Telegram channels for fraud/scam posts, crypto scam channels, darknet market links"},
        {"name":"MastodonConnector","platform":"Mastodon","access":"PUBLIC (no auth)","status":"LIVE_TESTED","result":"10 accounts found for 'fraud' search on mastodon.social","use_case":"Search federated social network for fraud indicators, scam accounts, crypto scams"},
        {"name":"URLScanConnector","platform":"URLScan.io","access":"PUBLIC (search free)","status":"LIVE_TESTED","result":"10 scans found for google.com domain","use_case":"Scan URLs for phishing, get screenshots, network data, track malicious infrastructure"},
        {"name":"RedditConnector","platform":"Reddit","access":"OAUTH_REQUIRED","status":"AUTH_REQUIRED","result":"Reddit now blocks bot access (403). Needs OAuth app registration.","use_case":"Search for scam reports, fraud complaints, reputation research"},
        {"name":"TelegramBotConnector","platform":"Telegram Bot API","access":"BOT_TOKEN","status":"AUTH_REQUIRED","result":"Connector ready. Needs bot token from @BotFather (free).","use_case":"GetChat, getChatAdministrators, forwardMessage — deep channel investigation"},
        {"name":"VKConnector","platform":"VKontakte (VK)","access":"API_KEY","status":"AUTH_REQUIRED","result":"Connector ready. Needs VK access token (free at dev.vk.com).","use_case":"Russian/CIS fraud investigation — search users, groups, posts, photos"},
        {"name":"DiscordConnector","platform":"Discord","access":"BOT_TOKEN","status":"AUTH_REQUIRED","result":"Connector ready. Needs Discord bot token (free at discord.com/developers).","use_case":"Search public servers, get user profiles, investigate scam servers"},
        {"name":"HaveIBeenPwnedConnector","platform":"HIBP","access":"API_KEY","status":"AUTH_REQUIRED","result":"Connector ready. Needs API key (haveibeenpwned.com).","use_case":"Check if email/phone appeared in data breaches — credential exposure"},
        {"name":"ThreatFoxConnector","platform":"ThreatFox (abuse.ch)","access":"API_KEY","status":"AUTH_REQUIRED","result":"API now requires auth key. Connector ready.","use_case":"Search malware IOCs: IPs, domains, URLs, hashes"},
        {"name":"URLHausConnector","platform":"URLHaus (abuse.ch)","access":"API_KEY","status":"AUTH_REQUIRED","result":"API now requires auth key. Connector ready.","use_case":"Search malicious URLs by domain"},
        {"name":"PulsediveConnector","platform":"Pulsedive","access":"API_KEY (optional)","status":"AUTH_REQUIRED","result":"Connector ready. Free tier available.","use_case":"Search IPs, domains, URLs for threat indicators"},
        {"name":"WaybackSocialConnector","platform":"Internet Archive","access":"PUBLIC (no auth)","status":"TESTED","result":"CDX search for archived social media pages","use_case":"Recover deleted social media content — critical for evidence preservation"},
        {"name":"FacebookConnector","platform":"Facebook/Meta","access":"OAUTH","status":"AUTH_REQUIRED","result":"Connector ready. Needs app review + access token.","use_case":"Public pages, posts, Ad Library — advertising intelligence"},
        {"name":"TwitterConnector","platform":"X (Twitter)","access":"BEARER_TOKEN","status":"AUTH_REQUIRED","result":"Connector ready. Needs paid API ($100/mo Basic).","use_case":"Search tweets, user profiles, timelines — real-time fraud signals"},
        {"name":"WhatsAppConnector","platform":"WhatsApp","access":"LIMITED","status":"LIMITED","result":"No public search API. Only invite link verification. E2E encrypted.","use_case":"Verify public group invite links. Phone number presence requires WhatsApp Business API."},
    ],
    "investigator_notes": {
        "telegram_public": "MAJOR WIN — Telegram public channel search works with NO authentication. Can extract messages, channel titles from any public channel via t.me/s/channelname. This is the single most valuable new capability for crypto scam investigation.",
        "mastodon": "Federated social network search works. Many fraud actors use Mastodon after being banned from mainstream platforms.",
        "urlscan": "URL scanning works. Can get screenshots, network data, DOM for any URL. Critical for phishing investigation.",
        "whatsapp_limitation": "WhatsApp is end-to-end encrypted with no public search. Only public group invite links (chat.whatsapp.com/CODE) can be verified. For phone number intelligence, the WhatsApp Business API requires Meta business verification.",
        "reddit_limitation": "Reddit now blocks bot access (403). Needs OAuth app registration at reddit.com/prefs/apps (free). Reddit is a major source for scam reports and fraud complaints.",
        "telegram_bot": "Getting a bot token from @BotFather is free and takes 2 minutes. This unlocks getChat, getChatAdministrators, getChatMember — critical for investigating Telegram-based scams.",
        "vk_importance": "VK is essential for investigations involving Russian, Latvian, Lithuanian, Estonian, Ukrainian, and Belarusian actors. Free API at dev.vk.com.",
    },
    "free_credentials_needed": [
        {"platform":"Telegram Bot API","process":"Message @BotFather on Telegram, create bot, get token","time":"2 minutes","priority":"CRITICAL"},
        {"platform":"VKontakte","process":"Register at dev.vk.com, create app, get access token","time":"10 minutes","priority":"HIGH (for CIS investigations)"},
        {"platform":"Reddit","process":"Register at reddit.com/prefs/apps, create OAuth app","time":"10 minutes","priority":"HIGH (for scam reports)"},
        {"platform":"Discord","process":"Register at discord.com/developers, create bot, get token","time":"10 minutes","priority":"MEDIUM"},
        {"platform":"HaveIBeenPwned","process":"Register at haveibeenpwned.com/API","time":"5 minutes","priority":"HIGH (for credential exposure)"},
        {"platform":"ThreatFox (abuse.ch)","process":"Register at abuse.ch","time":"5 minutes","priority":"MEDIUM"},
        {"platform":"URLHaus (abuse.ch)","process":"Register at abuse.ch","time":"5 minutes","priority":"MEDIUM"},
        {"platform":"Pulsedive","process":"Register at pulsedive.com","time":"5 minutes","priority":"LOW"},
        {"platform":"Facebook/Meta","process":"App review at developers.facebook.com","time":"2-4 weeks","priority":"MEDIUM (for Ad Library)"},
        {"platform":"X/Twitter","process":"Subscribe at developer.x.com","time":"Instant","priority":"LOW ($100/mo)"},
    ],
}

with open(os.path.join(base, "social-intel-summary.json"), 'w') as f:
    json.dump(summary, f, indent=2)

# Now update the master provider registry to include the new social connectors
with open(os.path.join(base, "provider-registry.json")) as f:
    reg = json.load(f)

new_providers = [
    {"provider_id":"telegram-public","company":"Telegram","service":"Public Channel Search (t.me)","category":"SOCIAL_MESSAGING","jurisdictions":["Global"],"authority_level":"PUBLIC","official_url":"t.me","api_url":"t.me/s","auth_method":"NONE","credential_type":"NONE","license":"Public content","rate_limit":"Reasonable use","cost_model":"Free","connector_status":"IMPLEMENTED_LIVE_TESTED","tier":1,"last_verified":ts},
    {"provider_id":"telegram-bot","company":"Telegram","service":"Bot API (getChat, etc.)","category":"SOCIAL_MESSAGING","jurisdictions":["Global"],"authority_level":"PUBLIC_API","official_url":"core.telegram.org/bots","api_url":"api.telegram.org","auth_method":"BOT_TOKEN","credential_type":"telegram_bot_token","license":"Free","rate_limit":"Varies","cost_model":"Free","connector_status":"IMPLEMENTED_AUTH_REQUIRED","tier":1,"last_verified":ts},
    {"provider_id":"reddit","company":"Reddit","service":"Social Platform Search","category":"SOCIAL_MESSAGING","jurisdictions":["Global"],"authority_level":"PUBLIC_API","official_url":"reddit.com","api_url":"reddit.com","auth_method":"OAUTH_REQUIRED","credential_type":"reddit_token","license":"Free","rate_limit":"60 req/min","cost_model":"Free","connector_status":"IMPLEMENTED_AUTH_REQUIRED","tier":1,"last_verified":ts},
    {"provider_id":"mastodon","company":"Mastodon","service":"Federated Social Search","category":"SOCIAL_MESSAGING","jurisdictions":["Global"],"authority_level":"PUBLIC","official_url":"joinmastodon.org","api_url":"mastodon.social/api/v2","auth_method":"NONE","credential_type":"NONE","license":"AGPLv3","rate_limit":"Varies","cost_model":"Free","connector_status":"IMPLEMENTED_LIVE_TESTED","tier":1,"last_verified":ts},
    {"provider_id":"vk","company":"VKontakte","service":"Russian Social Network API","category":"SOCIAL_MESSAGING","jurisdictions":["Russia","CIS"],"authority_level":"PUBLIC_API","official_url":"vk.com","api_url":"api.vk.com","auth_method":"API_KEY","credential_type":"vk_access_token","license":"Free","rate_limit":"3 req/sec","cost_model":"Free","connector_status":"IMPLEMENTED_AUTH_REQUIRED","tier":1,"last_verified":ts},
    {"provider_id":"discord","company":"Discord","service":"Server + User API","category":"SOCIAL_MESSAGING","jurisdictions":["Global"],"authority_level":"PUBLIC_API","official_url":"discord.com","api_url":"discord.com/api/v10","auth_method":"BOT_TOKEN","credential_type":"discord_bot_token","license":"Free","rate_limit":"Varies","cost_model":"Free","connector_status":"IMPLEMENTED_AUTH_REQUIRED","tier":2,"last_verified":ts},
    {"provider_id":"hibp","company":"HaveIBeenPwned","service":"Breach Intelligence","category":"BREACH_INTELLIGENCE","jurisdictions":["Global"],"authority_level":"PUBLIC_API","official_url":"haveibeenpwned.com","api_url":"haveibeenpwned.com/api/v3","auth_method":"API_KEY","credential_type":"hibp_api_key","license":"Freemium","rate_limit":"Varies","cost_model":"Free tier + paid","connector_status":"IMPLEMENTED_AUTH_REQUIRED","tier":1,"last_verified":ts},
    {"provider_id":"urlscan","company":"urlscan.io","service":"URL Scanner","category":"THREAT_INTERNET_INFRASTRUCTURE","jurisdictions":["Global"],"authority_level":"PUBLIC_API","official_url":"urlscan.io","api_url":"urlscan.io/api/v1","auth_method":"OPTIONAL_API_KEY","credential_type":"urlscan_api_key","license":"Freemium","rate_limit":"Varies","cost_model":"Free tier + paid","connector_status":"IMPLEMENTED_LIVE_TESTED","tier":1,"last_verified":ts},
    {"provider_id":"threatfox","company":"abuse.ch","service":"ThreatFox IOC Database","category":"THREAT_INTERNET_INFRASTRUCTURE","jurisdictions":["Global"],"authority_level":"PUBLIC_API","official_url":"threatfox.abuse.ch","api_url":"threatfox-api.abuse.ch","auth_method":"API_KEY","credential_type":"threatfox_api_key","license":"Free (CC0)","rate_limit":"Varies","cost_model":"Free","connector_status":"IMPLEMENTED_AUTH_REQUIRED","tier":1,"last_verified":ts},
    {"provider_id":"urlhaus","company":"abuse.ch","service":"URLHaus Malicious URLs","category":"THREAT_INTERNET_INFRASTRUCTURE","jurisdictions":["Global"],"authority_level":"PUBLIC_API","official_url":"urlhaus.abuse.ch","api_url":"urlhaus-api.abuse.ch","auth_method":"API_KEY","credential_type":"urlhaus_api_key","license":"Free (CC0)","rate_limit":"Varies","cost_model":"Free","connector_status":"IMPLEMENTED_AUTH_REQUIRED","tier":1,"last_verified":ts},
    {"provider_id":"pulsedive","company":"Pulsedive","service":"Threat Intelligence","category":"THREAT_INTERNET_INFRASTRUCTURE","jurisdictions":["Global"],"authority_level":"PUBLIC_API","official_url":"pulsedive.com","api_url":"pulsedive.com/api","auth_method":"OPTIONAL_API_KEY","credential_type":"pulsedive_api_key","license":"Freemium","rate_limit":"Varies","cost_model":"Free tier + paid","connector_status":"IMPLEMENTED_AUTH_REQUIRED","tier":2,"last_verified":ts},
    {"provider_id":"whatsapp","company":"WhatsApp","service":"Invite Link Verification (LIMITED)","category":"SOCIAL_MESSAGING","jurisdictions":["Global"],"authority_level":"LIMITED","official_url":"whatsapp.com","api_url":"chat.whatsapp.com","auth_method":"NONE","credential_type":"NONE","license":"N/A (E2E encrypted)","rate_limit":"N/A","cost_model":"N/A","connector_status":"IMPLEMENTED_LIMITED","tier":2,"last_verified":ts},
    {"provider_id":"twitter-x-social","company":"X (Twitter)","service":"Tweet/User Search","category":"SOCIAL_MESSAGING","jurisdictions":["Global"],"authority_level":"LICENSED","official_url":"x.com","api_url":"api.twitter.com/2","auth_method":"BEARER_TOKEN","credential_type":"twitter_bearer_token","license":"Commercial","rate_limit":"Varies","cost_model":"Paid ($100/mo+)","connector_status":"IMPLEMENTED_AUTH_REQUIRED","tier":2,"last_verified":ts},
]

reg["providers"].extend(new_providers)
reg["total_providers"] = len(reg["providers"])
reg["status_breakdown"]["IMPLEMENTED_LIVE_TESTED"] = len([p for p in reg["providers"] if p["connector_status"] == "IMPLEMENTED_LIVE_TESTED"])
reg["status_breakdown"]["IMPLEMENTED_AUTH_REQUIRED"] = len([p for p in reg["providers"] if p["connector_status"] == "IMPLEMENTED_AUTH_REQUIRED"])
reg["status_breakdown"]["NOT_IMPLEMENTED"] = len([p for p in reg["providers"] if p["connector_status"] == "NOT_IMPLEMENTED"])

with open(os.path.join(base, "provider-registry.json"), 'w') as f:
    json.dump(reg, f, indent=2)

print(f"Summary created. Provider registry updated: {reg['total_providers']} total providers, {reg['status_breakdown']['IMPLEMENTED_LIVE_TESTED']} live-tested.")
