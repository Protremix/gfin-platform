"""
GFIN Social Media + Cybercrime Intelligence Connectors v1.0
Built for digital footprint tracing in fraud/cybercrime investigations.
Every connector respects access controls — public data only, no bypasses.
"""
import json, time, urllib.request, urllib.parse, ssl, hashlib, sys, re
sys.path.insert(0, '/gfin/packages/connectors')
from base import BaseConnector, ConnectorResult

# 1. TELEGRAM — Public channel search via t.me web previews (NO AUTH NEEDED)
class TelegramPublicConnector(BaseConnector):
    """Search public Telegram channels/groups via t.me web preview.
    No bot token required. Accesses only public content.
    """
    provider_id = "telegram-public"
    provider = "Telegram (Public Channels)"
    source_class = "SOCIAL_MESSAGING"
    jurisdiction = "Global"
    auth_method = "API_KEY"
    credential_type = "NONE"
    rate_limit = "Reasonable use"
    api_url = "https://t.me"
    documentation = "https://t.me"
    license = "Public content"
    
    def query(self, channel: str = "", search_term: str = "", **kwargs) -> ConnectorResult:
        # t.me/s/channelname provides public web preview of channel messages
        if channel:
            url = f"https://t.me/s/{urllib.parse.quote(channel)}"
        else:
            # Search via Telegram's public directory (telegramchannels.me)
            url = f"https://telegramchannels.me/search?q={urllib.parse.quote(search_term)}"
        try:
            result = self._make_request(url)
            if result.success:
                text = result.data if isinstance(result.data, str) else json.dumps(result.data)
                # Extract public messages from the web preview page
                messages = []
                # Look for message text patterns in the HTML
                msg_patterns = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', text, re.DOTALL)
                for msg in msg_patterns[:20]:
                    clean = re.sub(r'<[^>]+>', '', msg).strip()
                    if clean and len(clean) > 10:
                        messages.append(clean[:500])
                
                # Extract channel info
                channel_name = ""
                title_match = re.search(r'<div class="tgme_channel_info_header_title[^"]*"[^>]*>(.*?)</div>', text, re.DOTALL)
                if title_match:
                    channel_name = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
                
                result.data = {
                    "channel": channel,
                    "channel_title": channel_name,
                    "messages_found": len(messages),
                    "messages": messages[:10],
                    "source": "t.me public web preview",
                    "access": "PUBLIC",
                }
                result.quality_score = 1.0 if messages else 0.0
            return result
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 2. TELEGRAM BOT API — Full bot API (needs bot token)
class TelegramBotConnector(BaseConnector):
    """Telegram Bot API for authorized channel/group access.
    Requires bot token from @BotFather.
    Can: getChat, getChatMember, getChatAdministrators, forwardMessage
    """
    provider_id = "telegram-bot"
    provider = "Telegram Bot API"
    source_class = "SOCIAL_MESSAGING"
    auth_method = "BOT_TOKEN"
    credential_type = "telegram_bot_token"
    api_url = "https://api.telegram.org"
    documentation = "https://core.telegram.org/bots/api"
    
    def query(self, chat_id: str = "", action: str = "getChat", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — Telegram bot token required from @BotFather",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        token = self.credentials["telegram_bot_token"]
        url = f"{self.api_url}/bot{token}/{action}?chat_id={urllib.parse.quote(str(chat_id))}"
        try:
            return self._make_request(url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 3. REDDIT — Free API (no auth for basic search)
class RedditConnector(BaseConnector):
    """Reddit search API. Free for basic use.
    Search posts, comments, user history, subreddit content.
    Useful for: scam reports, fraud complaints, reputation research.
    """
    provider_id = "reddit"
    provider = "Reddit"
    source_class = "SOCIAL_MESSAGING"
    jurisdiction = "Global"
    auth_method = "OAUTH_REQUIRED"
    credential_type = "reddit_token"
    rate_limit = "60 req/min"
    api_url = "https://www.reddit.com"
    documentation = "https://www.reddit.com/dev/api"
    license = "Free (public data)"
    
    def query(self, search_term: str = "", subreddit: str = "", username: str = "", **kwargs) -> ConnectorResult:
        headers = {"User-Agent": "GFIN/1.0 Research Bot"}
        if username:
            url = f"{self.api_url}/user/{urllib.parse.quote(username)}/public.json?limit=25"
        elif subreddit:
            url = f"{self.api_url}/r/{urllib.parse.quote(subreddit)}/search.json?q={urllib.parse.quote(search_term)}&restrict_sr=1&limit=25&sort=relevance"
        else:
            url = f"{self.api_url}/search.json?q={urllib.parse.quote(search_term)}&limit=25&sort=relevance"
        try:
            result = self._make_request(url, headers)
            if result.success and isinstance(result.data, dict):
                posts = result.data.get("data", {}).get("children", [])
                extracted = []
                for post in posts[:20]:
                    d = post.get("data", {})
                    extracted.append({
                        "title": d.get("title", ""),
                        "author": d.get("author", ""),
                        "subreddit": d.get("subreddit", ""),
                        "score": d.get("score", 0),
                        "url": d.get("url", ""),
                        "created_utc": d.get("created_utc", 0),
                        "selftext": d.get("selftext", "")[:500],
                        "num_comments": d.get("num_comments", 0),
                    })
                result.data = {
                    "posts_found": len(extracted),
                    "posts": extracted,
                    "search_term": search_term,
                    "source": "reddit.com",
                }
                result.quality_score = 1.0 if extracted else 0.0
            return result
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 4. MASTODON — Free, no auth (federated social network)
class MastodonConnector(BaseConnector):
    """Mastodon search API. Completely free, no auth.
    Search across federated instances for posts, accounts, hashtags.
    """
    provider_id = "mastodon"
    provider = "Mastodon (Federated)"
    source_class = "SOCIAL_MESSAGING"
    jurisdiction = "Global"
    auth_method = "API_KEY"
    credential_type = "NONE"
    rate_limit = "Varies by instance"
    api_url = "https://mastodon.social"
    documentation = "https://docs.joinmastodon.org/api/"
    license = "Free (AGPLv3)"
    
    def query(self, search_term: str = "", instance: str = "", **kwargs) -> ConnectorResult:
        base = f"https://{instance}" if instance else self.api_url
        url = f"{base}/api/v2/search?q={urllib.parse.quote(search_term)}&type=accounts&limit=10"
        headers = {"User-Agent": "GFIN/1.0"}
        try:
            result = self._make_request(url, headers)
            if result.success and isinstance(result.data, dict):
                accounts = result.data.get("accounts", [])
                extracted = []
                for acc in accounts[:10]:
                    extracted.append({
                        "id": acc.get("id", ""),
                        "username": acc.get("username", ""),
                        "acct": acc.get("acct", ""),
                        "display_name": acc.get("display_name", ""),
                        "url": acc.get("url", ""),
                        "followers_count": acc.get("followers_count", 0),
                        "following_count": acc.get("following_count", 0),
                        "statuses_count": acc.get("statuses_count", 0),
                        "note": acc.get("note", "")[:200],
                        "created_at": acc.get("created_at", ""),
                    })
                result.data = {
                    "accounts_found": len(extracted),
                    "accounts": extracted,
                    "search_term": search_term,
                    "instance": base,
                }
                result.quality_score = 1.0 if extracted else 0.0
            return result
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 5. VKONTAKTE — Russian social network (free API, needs app)
class VKConnector(BaseConnector):
    """VKontakte API. Free with app registration.
    Critical for investigations involving Russian/Eastern European actors.
    Search users, groups, posts, photos.
    """
    provider_id = "vk"
    provider = "VKontakte (VK)"
    source_class = "SOCIAL_MESSAGING"
    jurisdiction = "Russia, CIS"
    auth_method = "API_KEY"
    credential_type = "vk_access_token"
    rate_limit = "3 req/sec (free)"
    api_url = "https://api.vk.com/method"
    documentation = "https://dev.vk.com/method"
    
    def query(self, search_term: str = "", method: str = "users.search", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — VK access token required (free at dev.vk.com)",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        token = self.credentials["vk_access_token"]
        url = f"{self.api_url}/{method}?q={urllib.parse.quote(search_term)}&access_token={token}&v=5.199&count=10"
        try:
            return self._make_request(url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 6. DISCORD — Public server search (needs bot token for API)
class DiscordConnector(BaseConnector):
    """Discord API. Free bot token.
    Can search public servers, get user profiles, channel messages.
    """
    provider_id = "discord"
    provider = "Discord"
    source_class = "SOCIAL_MESSAGING"
    auth_method = "BOT_TOKEN"
    credential_type = "discord_bot_token"
    api_url = "https://discord.com/api/v10"
    documentation = "https://discord.com/developers/docs"
    
    def query(self, user_id: str = "", guild_id: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — Discord bot token required",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        token = self.credentials["discord_bot_token"]
        headers = {"Authorization": f"Bot {token}"}
        if user_id:
            url = f"{self.api_url}/users/{user_id}"
        elif guild_id:
            url = f"{self.api_url}/guilds/{guild_id}"
        else:
            return ConnectorResult(success=False, error="user_id or guild_id required", provider=self.provider, source_class=self.source_class)
        try:
            return self._make_request(url, headers)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 7. HAVEIBEENPWNED — Breach data (free API, needs key now)
class HaveIBeenPwnedConnector(BaseConnector):
    """HaveIBeenPwned API. Check if email/phone appeared in data breaches.
    Critical for: credential exposure, identity theft, account takeover.
    """
    provider_id = "hibp"
    provider = "Have I Been Pwned"
    source_class = "BREACH_INTELLIGENCE"
    auth_method = "API_KEY"
    credential_type = "hibp_api_key"
    api_url = "https://haveibeenpwned.com/api/v3"
    documentation = "https://haveibeenpwned.com/API/v3"
    
    def query(self, email: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — HIBP API key required (get at haveibeenpwned.com)",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        url = f"{self.api_url}/breachedaccount/{urllib.parse.quote(email)}"
        headers = {"hibp-api-key": self.credentials["hibp_api_key"], "User-Agent": "GFIN/1.0"}
        try:
            return self._make_request(url, headers)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # 404 means NOT breached — this is a success
                return ConnectorResult(
                    success=True, data={"email": email, "breaches": [], "found": False},
                    provider=self.provider, source_class=self.source_class,
                    quality_score=1.0, provenance=url
                )
            return ConnectorResult(success=False, error=f"HTTP {e.code}", provider=self.provider, source_class=self.source_class)

# 8. URLSCAN.IO — URL scanning (free tier)
class URLScanConnector(BaseConnector):
    """URLscan.io API. Scan URLs, get screenshots, network data, DOM.
    Critical for: phishing investigation, malicious infrastructure mapping.
    """
    provider_id = "urlscan"
    provider = "urlscan.io"
    source_class = "THREAT_INTERNET_INFRASTRUCTURE"
    auth_method = "API_KEY (optional for search)"
    credential_type = "urlscan_api_key"
    api_url = "https://urlscan.io/api/v1"
    documentation = "https://urlscan.io/docs/api/"
    
    def query(self, domain: str = "", url: str = "", **kwargs) -> ConnectorResult:
        # Search is free without API key
        search_url = f"{self.api_url}/search/?q=domain:{urllib.parse.quote(domain)}"
        headers = {"User-Agent": "GFIN/1.0"}
        if self._check_credential():
            headers["API-Key"] = self.credentials["urlscan_api_key"]
        try:
            result = self._make_request(search_url, headers)
            if result.success and isinstance(result.data, dict):
                results_list = result.data.get("results", [])
                extracted = []
                for r in results_list[:10]:
                    page = r.get("page", {})
                    extracted.append({
                        "url": page.get("url", ""),
                        "domain": page.get("domain", ""),
                        "ip": page.get("ip", ""),
                        "status": r.get("status", ""),
                        "screenshot": f"https://urlscan.io/screenshots/{r.get('_id','')}.png",
                        "scan_time": r.get("task", {}).get("time", ""),
                    })
                result.data = {
                    "scans_found": len(extracted),
                    "scans": extracted,
                    "domain": domain,
                }
                result.quality_score = 1.0 if extracted else 0.0
            return result
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 9. THREATFOX (abuse.ch) — Free IOC database (no auth)
class ThreatFoxConnector(BaseConnector):
    """ThreatFox by abuse.ch. Free IOC database.
    Search malware IOCs: IPs, domains, URLs, hashes.
    No authentication required.
    """
    provider_id = "threatfox"
    provider = "ThreatFox (abuse.ch)"
    source_class = "THREAT_INTERNET_INFRASTRUCTURE"
    auth_method = "API_KEY"
    credential_type = "NONE"
    api_url = "https://threatfox-api.abuse.ch/api/v1"
    documentation = "https://threatfox.abuse.ch/api/"
    license = "Free (CC0)"
    
    def query(self, search_term: str = "", ioc_type: str = "domain", **kwargs) -> ConnectorResult:
        # POST request with search query
        data = urllib.parse.urlencode({"query": "search_ioc", "search_term": search_term}).encode()
        headers = {"User-Agent": "GFIN/1.0", "Content-Type": "application/x-www-form-urlencoded"}
        req = urllib.request.Request(self.api_url, data=data, headers=headers)
        try:
            resp = urllib.request.urlopen(req, timeout=15, context=self.ssl_ctx)
            raw = resp.read()
            result = ConnectorResult(
                success=True, provider=self.provider, source_class=self.source_class,
                provenance=self.api_url, content_hash=hashlib.sha256(raw).hexdigest(),
                timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                raw_response_size=len(raw),
            )
            parsed = json.loads(raw)
            iocs = parsed.get("data", []) if parsed.get("query_status") == "ok" else []
            result.data = {
                "ioc": search_term,
                "ioc_type": ioc_type,
                "found": len(iocs) > 0,
                "iocs": iocs[:10] if iocs else [],
                "query_status": parsed.get("query_status", ""),
            }
            result.quality_score = 1.0 if iocs else 0.0
            return result
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 10. URLHAUS (abuse.ch) — Malicious URL database (free, no auth)
class URLHausConnector(BaseConnector):
    """URLHaus by abuse.ch. Free malicious URL database.
    Search for malicious URLs by domain.
    """
    provider_id = "urlhaus"
    provider = "URLHaus (abuse.ch)"
    source_class = "THREAT_INTERNET_INFRASTRUCTURE"
    auth_method = "API_KEY"
    credential_type = "NONE"
    api_url = "https://urlhaus-api.abuse.ch/v1"
    documentation = "https://urlhaus.abuse.ch/api/"
    license = "Free (CC0)"
    
    def query(self, domain: str = "", **kwargs) -> ConnectorResult:
        data = urllib.parse.urlencode({"host": domain}).encode()
        headers = {"User-Agent": "GFIN/1.0", "Content-Type": "application/x-www-form-urlencoded"}
        req = urllib.request.Request(f"{self.api_url}/host/", data=data, headers=headers)
        try:
            resp = urllib.request.urlopen(req, timeout=15, context=self.ssl_ctx)
            raw = resp.read()
            result = ConnectorResult(
                success=True, provider=self.provider, source_class=self.source_class,
                provenance=self.api_url, content_hash=hashlib.sha256(raw).hexdigest(),
                timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                raw_response_size=len(raw),
            )
            parsed = json.loads(raw)
            urls = parsed.get("urls", [])
            result.data = {
                "domain": domain,
                "malicious_urls_found": len(urls),
                "urls": urls[:10] if urls else [],
                "query_status": parsed.get("query_status", ""),
            }
            result.quality_score = 1.0 if urls else 0.0
            return result
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 11. PULSEDIVE — Threat intelligence (free API)
class PulsediveConnector(BaseConnector):
    """Pulsedive API. Free threat intelligence.
    Search IPs, domains, URLs for threat indicators.
    """
    provider_id = "pulsedive"
    provider = "Pulsedive"
    source_class = "THREAT_INTERNET_INFRASTRUCTURE"
    auth_method = "API_KEY (optional for basic)"
    credential_type = "pulsedive_api_key"
    api_url = "https://pulsedive.com/api"
    documentation = "https://pulsedive.com/api/"
    
    def query(self, indicator: str = "", **kwargs) -> ConnectorResult:
        if self._check_credential():
            key = self.credentials["pulsedive_api_key"]
            url = f"{self.api_url}/info.php?indicator={urllib.parse.quote(indicator)}&key={key}"
        else:
            url = f"{self.api_url}/explore.php?q={urllib.parse.quote(indicator)}&limit=10&pretty=1"
        headers = {"User-Agent": "GFIN/1.0"}
        try:
            return self._make_request(url, headers)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 12. WAYBACK MACHINE — Historical web (already exists but add social search)
class WaybackSocialConnector(BaseConnector):
    """Wayback Machine CDX — search for archived social media pages.
    Free, no auth. Critical for: deleted social media content recovery.
    """
    provider_id = "wayback-social"
    provider = "Internet Archive (Wayback Machine)"
    source_class = "HISTORICAL_INTELLIGENCE"
    auth_method = "API_KEY"
    credential_type = "NONE"
    api_url = "https://web.archive.org/cdx/search/cdx"
    documentation = "https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server"
    
    def query(self, url: str = "", **kwargs) -> ConnectorResult:
        cdx_url = f"{self.api_url}?url={urllib.parse.quote(url)}&output=json&limit=20&collapse=urlkey"
        try:
            result = self._make_request(cdx_url)
            if result.success and isinstance(result.data, list):
                captures = result.data[1:] if len(result.data) > 1 else []  # Skip header row
                extracted = []
                for cap in captures[:20]:
                    extracted.append({
                        "timestamp": cap[1] if len(cap) > 1 else "",
                        "original_url": cap[2] if len(cap) > 2 else "",
                        "status": cap[4] if len(cap) > 4 else "",
                        "archive_url": f"https://web.archive.org/web/{cap[1]}/{cap[2]}" if len(cap) > 2 else "",
                    })
                result.data = {
                    "url": url,
                    "captures_found": len(extracted),
                    "captures": extracted,
                }
                result.quality_score = 1.0 if extracted else 0.0
            return result
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 13. FACEBOOK GRAPH API (needs app review + token)
class FacebookConnector(BaseConnector):
    """Facebook Graph API. Public pages, posts, Ad Library.
    Requires app review + access token.
    """
    provider_id = "facebook"
    provider = "Facebook / Meta"
    source_class = "SOCIAL_MESSAGING"
    auth_method = "OAUTH"
    credential_type = "facebook_access_token"
    api_url = "https://graph.facebook.com/v18.0"
    documentation = "https://developers.facebook.com/docs/graph-api"
    
    def query(self, page_name: str = "", search_term: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — Facebook access token required (needs app review)",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        token = self.credentials["facebook_access_token"]
        if page_name:
            url = f"{self.api_url}/{page_name}?fields=name,about,website,emails,phones,link&access_token={token}"
        else:
            url = f"{self.api_url}/ads_archive?search_terms={urllib.parse.quote(search_term)}&access_token={token}"
        try:
            return self._make_request(url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 14. X/TWITTER — Paid API
class TwitterConnector(BaseConnector):
    """X (Twitter) API v2. Paid ($100/mo minimum for Basic).
    Search tweets, user profiles, timelines.
    """
    provider_id = "twitter-x"
    provider = "X (Twitter)"
    source_class = "SOCIAL_MESSAGING"
    auth_method = "BEARER_TOKEN"
    credential_type = "twitter_bearer_token"
    api_url = "https://api.twitter.com/2"
    documentation = "https://developer.x.com/en/docs/twitter-api"
    
    def query(self, search_term: str = "", username: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — X API bearer token required ($100/mo Basic tier)",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        headers = {"Authorization": f"Bearer {self.credentials['twitter_bearer_token']}"}
        if username:
            url = f"{self.api_url}/users/by/username/{username}"
        else:
            url = f"{self.api_url}/tweets/search/recent?query={urllib.parse.quote(search_term)}&max_results=10"
        try:
            return self._make_request(url, headers)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 15. WHATSAPP — Public link checker (no API, checks public invite links)
class WhatsAppConnector(BaseConnector):
    """WhatsApp public invite link checker.
    WhatsApp has NO public search API (end-to-end encrypted).
    Can only check if public invite links are valid.
    """
    provider_id = "whatsapp"
    provider = "WhatsApp"
    source_class = "SOCIAL_MESSAGING"
    auth_method = "API_KEY"
    credential_type = "NONE"
    api_url = "https://chat.whatsapp.com"
    documentation = "N/A — no public API"
    
    def query(self, invite_code: str = "", phone: str = "", **kwargs) -> ConnectorResult:
        if invite_code:
            # Check if a public WhatsApp group invite link is valid
            url = f"{self.api_url}/{invite_code}"
            try:
                result = self._make_request(url)
                if result.success:
                    text = result.data if isinstance(result.data, str) else json.dumps(result.data)
                    group_name = ""
                    title_match = re.search(r'og:title" content="([^"]+)"', text)
                    if title_match:
                        group_name = title_match.group(1)
                    result.data = {
                        "invite_code": invite_code,
                        "group_exists": bool(group_name),
                        "group_name": group_name,
                        "source": "chat.whatsapp.com public link",
                        "note": "WhatsApp has no public search API. Only public invite links can be checked.",
                    }
                    result.quality_score = 1.0 if group_name else 0.0
                return result
            except Exception as e:
                return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)
        else:
            return ConnectorResult(
                success=False,
                error="WhatsApp has no public search API. End-to-end encrypted. Only invite link verification available. For phone number presence, use WhatsApp Business API (requires Meta business verification).",
                provider=self.provider, source_class=self.source_class,
                authorization_status="LIMITED"
            )

# Registry
SOCIAL_INTEL_REGISTRY = {
    "telegram_public": TelegramPublicConnector,
    "telegram_bot": TelegramBotConnector,
    "reddit": RedditConnector,
    "mastodon": MastodonConnector,
    "vk": VKConnector,
    "discord": DiscordConnector,
    "hibp": HaveIBeenPwnedConnector,
    "urlscan": URLScanConnector,
    "threatfox": ThreatFoxConnector,
    "urlhaus": URLHausConnector,
    "pulsedive": PulsediveConnector,
    "wayback_social": WaybackSocialConnector,
    "facebook": FacebookConnector,
    "twitter_x": TwitterConnector,
    "whatsapp": WhatsAppConnector,
}
