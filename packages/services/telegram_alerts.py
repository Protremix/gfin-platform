#!/usr/bin/env python3
"""
GFIN Public Telegram Alert Bot
- Citizens subscribe via /start
- When a complaint is filed, broadcasts ANONYMIZED alert to all subscribers
- NO names, NO personal data — only scam type, target indicator, risk level
- Bot commands: /start, /help, /latest, /stats, /unsubscribe
"""
import json, ssl, urllib.request, urllib.parse, os, time, hashlib
from typing import Optional, List

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# SSL context for Telegram API calls
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

ALERT_EMOJI = {
    "CRITICAL": "🔴",
    "HIGH": "🟠",
    "MEDIUM": "🟡",
    "LOW": "🟢",
    "MINIMAL": "⚪",
}

SCAM_EMOJI = {
    "RECOVERY_SCAM": "💸",
    "ROMANCE_SCAM": "❤️",
    "INVESTMENT_FRAUD": "📈",
    "PHISHING": "🎣",
    "IMPERSONATION": "🎭",
    "LOTTERY_SCAM": "🎰",
    "TECH_SUPPORT": "💻",
    "ADVANCE_FEE": "💰",
    "CRYPTO_FRAUD": "₿",
    "WIRE_FRAUD": "🏦",
    "DEFAULT": "🚨",
}


class GFINAlertBot:
    """Public scam alert bot — broadcasts anonymized alerts to subscribers."""

    def __init__(self, bot_token: str = ""):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"

    def _api_call(self, method: str, params: dict) -> dict:
        """Call a Telegram API method."""
        url = f"{self.api_base}/{method}"
        data = urllib.parse.urlencode(params).encode()
        try:
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            resp = urllib.request.urlopen(req, timeout=15, context=_ssl_ctx)
            return json.loads(resp.read().decode())
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML",
                      reply_markup: dict = None) -> bool:
        """Send a message to a chat."""
        params = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": "true",
        }
        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)
        result = self._api_call("sendMessage", params)
        return result.get("ok", False)

    def get_updates(self, offset: int = 0) -> list:
        """Get pending updates (messages from users)."""
        result = self._api_call("getUpdates", {"offset": offset, "timeout": 0})
        return result.get("result", []) if result.get("ok") else []

    def set_webhook(self, url: str = "") -> bool:
        """Set or clear webhook."""
        params = {"url": url} if url else {"url": ""}
        result = self._api_call("setWebhook", params)
        return result.get("ok", False)

    def get_bot_info(self) -> dict:
        """Get bot info."""
        return self._api_call("getMe", {})

    # ==================== ANONYMIZED ALERT BROADCAST ====================

    def broadcast_alert(self, subscribers: List[str], scam_type: str,
                        risk_level: str, target_indicator: str,
                        target_type: str = "domain", region: str = "",
                        complaint_ref: str = "") -> int:
        """
        Broadcast anonymized scam alert to all subscribers.
        NO names, NO personal data — only scam type and target indicator.
        
        Args:
            subscribers: List of chat IDs to send to
            scam_type: Type of scam (e.g. RECOVERY_SCAM)
            risk_level: CRITICAL/HIGH/MEDIUM/LOW
            target_indicator: Domain, phone pattern, wallet address (public indicator only)
            target_type: domain/phone/wallet/email
            region: General region (e.g. "Europe", "Global") — not specific country
            complaint_ref: Complaint reference (for tracking, not personal)
        """
        emoji = ALERT_EMOJI.get(risk_level.upper(), "🚨")
        scam_icon = SCAM_EMOJI.get(scam_type.upper(), SCAM_EMOJI["DEFAULT"])

        # Format target indicator based on type
        target_label = {
            "domain": "🌐 Website",
            "phone": "📞 Phone Number",
            "wallet": "₿ Crypto Wallet",
            "email": "✉️ Email",
            "social": "👤 Social Media",
            "unknown": "🎯 Target",
        }.get(target_type.lower(), "🎯 Target")

        region_text = f"\n🌍 <b>Region:</b> {region}" if region else ""

        message = f"""{emoji} <b>GFIN SCAM ALERT</b> {scam_icon}

<b>A new scam complaint has been reported.</b>

<b>Scam Type:</b> {scam_type.replace('_', ' ').title()}
<b>Risk Level:</b> {risk_level}
<b>Target:</b> {target_label}
<code>{target_indicator}</code>{region_text}

⚠️ <b>Stay vigilant.</b> Do not send money or personal information to this target.
If you have been affected by this scam, file a report at:
🔗 gfin-system.com/victim

<b>Reference:</b> {complaint_ref}

<i>— GFIN Global Fraud Intelligence Network</i>
<i>No personal data is shared in alerts. Only public scam indicators are broadcast.</i>"""

        sent_count = 0
        for chat_id in subscribers:
            if self.send_message(chat_id, message):
                sent_count += 1
            time.sleep(0.05)  # Avoid hitting Telegram rate limits (30 msg/sec)

        return sent_count

    # ==================== BOT COMMAND RESPONSES ====================

    def handle_welcome(self, chat_id: str, subscriber_name: str = "") -> bool:
        """Send welcome message when someone /starts the bot."""
        name_part = f"Welcome, {subscriber_name}! 👋\n\n" if subscriber_name else "Welcome! 👋\n\n"

        message = f"""🛡️ <b>GFIN Scam Alert Bot</b>

{name_part}You are now subscribed to receive <b>real-time scam alerts</b> from the Global Fraud Intelligence Network.

<b>What you'll receive:</b>
{ALERT_EMOJI['CRITICAL']} Critical scam warnings (new threats)
{ALERT_EMOJI['HIGH']} High-risk scam alerts
{ALERT_EMOJI['MEDIUM']} Medium-risk scam notifications

<b>What is NOT shared:</b>
❌ Victim names or personal data
❌ Your personal information
✅ Only public scam indicators (domains, wallets, phone numbers)

<b>Commands:</b>
/start — Subscribe to alerts
/help — Show all commands
/latest — Show recent scam alerts
/stats — Show scam statistics
/unsubscribe — Stop receiving alerts

🔗 <b>Report a scam:</b> gfin-system.com/victim
🔗 <b>Police portal:</b> gfin-system.com

🔍 <b>Check a website:</b> Send /check example.com
📋 <b>List scam sites:</b> Send /list

<i>You will receive alerts automatically when new scams are reported.</i>"""

        return self.send_message(chat_id, message)

    def handle_help(self, chat_id: str) -> bool:
        """Send help message."""
        message = """🛡️ <b>GFIN Scam Alert Bot — Commands</b>

/start — Subscribe to scam alerts
/help — Show this help message
/latest — View recent scam alerts
/stats — View scam statistics
/unsubscribe — Stop receiving alerts
/about — About GFIN

<b>Report a scam:</b> gfin-system.com/victim
<i>GFIN — Global Fraud Intelligence Network</i>"""
        return self.send_message(chat_id, message)

    def handle_about(self, chat_id: str) -> bool:
        """Send about message."""
        message = """🛡️ <b>About GFIN</b>

The <b>Global Fraud Intelligence Network (GFIN)</b> is a platform for collecting, analyzing, and routing fraud intelligence to law enforcement worldwide.

<b>This bot</b> sends anonymized public alerts when scams are reported. It helps citizens stay informed about active scam threats.

✅ <b>Privacy protected:</b> No personal data is shared in alerts
✅ <b>Evidence-based:</b> All alerts are generated from verified complaints
✅ <b>Global coverage:</b> Alerts cover scams from all countries

🔍 <b>Check a website:</b> /check example.com
📋 <b>List scam sites:</b> /list

🔗 <b>Scam website database:</b> gfin-system.com/scam-sites
<i>GFIN — Making the internet safer, one alert at a time.</i>"""
        return self.send_message(chat_id, message)

    def handle_unsubscribe(self, chat_id: str) -> bool:
        """Send unsubscribe confirmation."""
        message = """✅ <b>You have been unsubscribed</b>

You will no longer receive GFIN scam alerts.

If you want to re-subscribe, just send /start.

🔗 <b>Report a scam:</b> gfin-system.com/victim
<i>GFIN — Global Fraud Intelligence Network</i>"""
        return self.send_message(chat_id, message)

    def handle_stats(self, chat_id: str, total_alerts: int = 0,
                     total_subscribers: int = 0, active_threats: int = 0) -> bool:
        """Send statistics."""
        message = f"""📊 <b>GFIN Statistics</b>

📨 <b>Total Alerts Sent:</b> {total_alerts}
👥 <b>Subscribers:</b> {total_subscribers}
🚨 <b>Active Threats:</b> {active_threats}

🔗 <b>Full dashboard:</b> gfin-system.com
<i>GFIN — Global Fraud Intelligence Network</i>"""
        return self.send_message(chat_id, message)


# ==================== SUBSCRIBER MANAGEMENT ====================

# Subscriber storage — in production, use PostgreSQL
# For now, store in a JSON file on the server
SUBSCRIBER_FILE = "/gfin/telegram_subscribers.json"

def load_subscribers() -> List[str]:
    """Load subscriber chat IDs from file."""
    try:
        with open(SUBSCRIBER_FILE, "r") as f:
            data = json.load(f)
            return data.get("subscribers", [])
    except:
        return []


def save_subscribers(subscribers: List[str]):
    """Save subscriber chat IDs to file."""
    with open(SUBSCRIBER_FILE, "w") as f:
        json.dump({"subscribers": subscribers, "updated": time.time()}, f)


def add_subscriber(chat_id: str) -> bool:
    """Add a subscriber. Returns True if new."""
    subscribers = load_subscribers()
    if chat_id not in subscribers:
        subscribers.append(chat_id)
        save_subscribers(subscribers)
        return True
    return False


def remove_subscriber(chat_id: str) -> bool:
    """Remove a subscriber. Returns True if existed."""
    subscribers = load_subscribers()
    if chat_id in subscribers:
        subscribers.remove(chat_id)
        save_subscribers(subscribers)
        return True
    return False


# ==================== PUBLIC API ====================

_bot_instance = None

def get_bot() -> Optional[GFINAlertBot]:
    """Get or create the global bot instance."""
    global _bot_instance
    if _bot_instance is None:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if token:
            _bot_instance = GFINAlertBot(token)
    return _bot_instance


def broadcast_scam_alert(scam_type: str, risk_level: str, target_indicator: str,
                         target_type: str = "domain", region: str = "",
                         complaint_ref: str = "") -> int:
    """
    Broadcast anonymized scam alert to all subscribers.
    Returns number of alerts sent.
    """
    bot = get_bot()
    if not bot:
        return 0

    subscribers = load_subscribers()
    if not subscribers:
        return 0

    return bot.broadcast_alert(
        subscribers=subscribers,
        scam_type=scam_type,
        risk_level=risk_level,
        target_indicator=target_indicator,
        target_type=target_type,
        region=region,
        complaint_ref=complaint_ref,
    )


def process_bot_updates():
    """
    Process incoming Telegram messages (bot commands from users).
    Call this periodically (e.g. every 30 seconds) from the monitor loop.
    """
    bot = get_bot()
    if not bot:
        return

    # Use offset from last processed update
    offset_file = "/gfin/telegram_offset.txt"
    try:
        with open(offset_file, "r") as f:
            offset = int(f.read().strip()) + 1
    except:
        offset = 0

    updates = bot.get_updates(offset=offset)
    for update in updates:
        update_id = update.get("update_id", 0)
        message = update.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "").strip()
        user_name = message.get("from", {}).get("first_name", "")

        if not chat_id or not text:
            continue

        # Handle commands
        if text.startswith("/start"):
            is_new = add_subscriber(chat_id)
            bot.handle_welcome(chat_id, user_name if is_new else "")
        elif text.startswith("/help"):
            bot.handle_help(chat_id)
        elif text.startswith("/about"):
            bot.handle_about(chat_id)
        elif text.startswith("/unsubscribe") or text.startswith("/stop"):
            remove_subscriber(chat_id)
            bot.handle_unsubscribe(chat_id)
        elif text.startswith("/stats"):
            subs = load_subscribers()
            bot.handle_stats(chat_id, total_subscribers=len(subs))
        elif text.startswith("/latest"):
            bot.send_message(chat_id,
                "📋 Recent scam alerts are available at gfin-system.com\n\n"
                "Use /subscribe to receive real-time alerts.")
        else:
            # Unknown command — show help
            bot.handle_help(chat_id)

        # Update offset
        with open(offset_file, "w") as f:
            f.write(str(update_id))
