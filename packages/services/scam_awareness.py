#!/usr/bin/env python3
"""
GFIN Scam Awareness Broadcast System
Sends periodic educational alerts to all Telegram subscribers about different scam types.
Goal: make people more careful BEFORE they get scammed.
"""
import json, time, ssl, urllib.request, urllib.parse, os, random, hashlib
from datetime import datetime, timezone

# Import the bot
import sys
sys.path.insert(0, '/gfin/packages/services')
from telegram_alerts import (
    GFINAlertBot, load_subscribers, get_bot,
    ALERT_EMOJI, SCAM_EMOJI
)

# Awareness content — educational messages about different scam types
# Each entry is a self-contained educational alert
SCAM_AWARENESS_MESSAGES = [
    {
        "scam_type": "RECOVERY_SCAM",
        "emoji": "💸",
        "title": "Recovery Scams — The Second Trap",
        "body": """🚨 <b>SCAM AWARENESS: Recovery Scams</b> 💸

<b>Did you lose money to a scam? Someone says they can get it back?</b>

⚠️ <b>STOP. Think twice. It's probably a recovery scam.</b>

<b>How it works:</b>
1️⃣ Scammers contact victims who already lost money
2️⃣ They claim to be "recovery experts" or "hackers"
3️⃣ They promise to recover your lost funds — for a fee
4️⃣ They use fake reviews, fake testimonials, fake "successful recoveries"
5️⃣ Once you pay, they disappear — you've been scammed TWICE

🚩 <b>Red flags:</b>
• They found you after you posted about being scammed
• They ask for upfront payment before recovery
• They guarantee 100% success (nobody can guarantee this)
• They use Telegram, WhatsApp, or email to contact you
• They say they have "special access" or "insider connections"
• Their website looks professional but was recently created

✅ <b>How to protect yourself:</b>
• Report to your national police cybercrime unit
• File a complaint at gfin-system.com/victim
• Never pay anyone who promises to "recover" your funds
• Check if the "recovery service" is registered/regulated
• Real recovery happens through law enforcement, not private "hackers"

💡 <b>Remember:</b> If it sounds too good to be true, it is. You've already been scammed once — don't let it happen again.

🔗 <b>Report a scam:</b> gfin-system.com/victim
<i>— GFIN Global Fraud Intelligence Network</i>"""
    },
    {
        "scam_type": "ROMANCE_SCAM",
        "emoji": "❤️",
        "title": "Romance Scams — Love Used as a Weapon",
        "body": """🚨 <b>SCAM AWARENESS: Romance Scams</b> ❤️

<b>Someone you met online says they love you... but they need money?</b>

⚠️ <b>STOP. Real love doesn't ask for money.</b>

<b>How it works:</b>
1️⃣ Scammer creates a fake dating profile (attractive, often "working abroad")
2️⃣ They build an emotional connection over weeks or months
3️⃣ They avoid video calls or meeting in person (always an excuse)
4️⃣ They create an "emergency": medical bills, travel costs, customs fees
5️⃣ They ask for money transfers, gift cards, or crypto payments
6️⃣ The requests escalate — it never stops

🚩 <b>Red flags:</b>
• Profile picture looks like a model (reverse image search!)
• They declare love very quickly ("love bombing")
• They can never video call or meet
• They claim to be in the military, oil rig, or working overseas
• They ask for money for "visas," "medical emergencies," "customs"
• They want payment via crypto, gift cards, or wire transfer
• They isolate you from friends and family

✅ <b>How to protect yourself:</b>
• Never send money to someone you haven't met in person
• Do a reverse image search on their profile photo
• Ask for a video call — if they refuse, it's a scam
• Tell friends and family about the relationship
• Report to gfin-system.com/victim

💡 <b>Remember:</b> A real partner will never ask you for money. If they do, it's not love — it's a scam.

🔗 <b>Report a scam:</b> gfin-system.com/victim
<i>— GFIN Global Fraud Intelligence Network</i>"""
    },
    {
        "scam_type": "INVESTMENT_FRAUD",
        "emoji": "📈",
        "title": "Investment Fraud — Fake Returns, Real Losses",
        "body": """🚨 <b>SCAM AWARENESS: Investment Fraud</b> 📈

<b>"Guaranteed 5% daily returns. Risk-free. Join now."</b>

⚠️ <b>STOP. There's no such thing as risk-free high returns.</b>

<b>How it works:</b>
1️⃣ Scammer advertises on social media, Telegram, WhatsApp
2️⃣ They show fake profits, fake testimonials, fake trading screens
3️⃣ They let you "withdraw" a small amount first — to build trust
4️⃣ When you invest more, your "account" shows huge profits
5️⃣ But when you try to withdraw, there are "fees," "taxes," "penalties"
6️⃣ You pay the fees. They ask for more. You never get your money back

🚩 <b>Red flags:</b>
• Promises of guaranteed or "risk-free" returns
• High pressure: "limited time offer," "only 3 spots left"
• Unregulated platform — not registered with financial authorities
• They contact you via WhatsApp, Telegram, Instagram DMs
• "Account manager" handles everything for you
• You can see profits but can't withdraw them
• They ask for crypto deposits to "start trading"

✅ <b>How to protect yourself:</b>
• Check if the platform is registered with your country's financial regulator
• Search the company name + "scam" or "fraud" online
• Never invest money you can't afford to lose
• Never send crypto to an unknown wallet
• Verify the company's registration number
• Report suspicious platforms to gfin-system.com/victim

💡 <b>Remember:</b> If returns are guaranteed, it's a scam. Real investing has risk. Anyone who says otherwise is lying.

🔗 <b>Report a scam:</b> gfin-system.com/victim
<i>— GFIN Global Fraud Intelligence Network</i>"""
    },
    {
        "scam_type": "PHISHING",
        "emoji": "🎣",
        "title": "Phishing — Stealing Your Identity",
        "body": """🚨 <b>SCAM AWARENESS: Phishing</b> 🎣

<b>"Your account has been suspended. Click here to verify."</b>

⚠️ <b>STOP. Don't click that link.</b>

<b>How it works:</b>
1️⃣ You receive an email, SMS, or message that looks official
2️⃣ It says your account is suspended, payment failed, or you won a prize
3️⃣ It contains a link to a fake website that looks real
4️⃣ You enter your username, password, credit card, or OTP
5️⃣ Scammers capture your credentials and take over your accounts
6️⃣ They drain your bank, steal your identity, or sell your data

🚩 <b>Red flags:</b>
• Urgency: "Act now or your account will be closed!"
• Sender email doesn't match the official domain (check carefully!)
• Link URL is different from the real website
• Asks for your password, PIN, or full card number
• Spelling or grammar mistakes
• You didn't initiate the contact

✅ <b>How to protect yourself:</b>
• Never click links in suspicious emails or SMS
• Go directly to the official website by typing the URL
• Check the sender's email address carefully
• Enable two-factor authentication (2FA) on all accounts
• Use a password manager
• Report phishing to gfin-system.com/victim

💡 <b>Remember:</b> Banks never ask for your password or PIN by email or SMS. If they do, it's a scam.

🔗 <b>Report a scam:</b> gfin-system.com/victim
<i>— GFIN Global Fraud Intelligence Network</i>"""
    },
    {
        "scam_type": "IMPERSONATION",
        "emoji": "🎭",
        "title": "Impersonation Scams — They're Not Who They Say They Are",
        "body": """🚨 <b>SCAM AWARENESS: Impersonation Scams</b> 🎭

<b>"This is the police. There's a warrant for your arrest. Pay now."</b>

⚠️ <b>STOP. Real police don't ask for money over the phone.</b>

<b>How it works:</b>
1️⃣ Scammer calls or messages claiming to be police, government, bank, or tech support
2️⃣ They use fear: "You'll be arrested," "Your account will be frozen," "Your computer has a virus"
3️⃣ They create urgency — you must act NOW
4️⃣ They tell you to transfer money to a "safe account" or pay in gift cards
5️⃣ They keep you on the phone so you can't verify with anyone
6️⃣ By the time you realize, your money is gone

🚩 <b>Red flags:</b>
• Caller claims to be from police, government, or bank
• They demand immediate payment
• They want payment via gift cards, crypto, or wire transfer
• They threaten arrest, deportation, or account closure
• They tell you not to tell anyone
• They ask for remote access to your computer

✅ <b>How to protect yourself:</b>
• Hang up immediately — real authorities don't demand payment by phone
• Call the official number yourself (from their website, not the caller's)
• Never give remote access to your computer
• Never buy gift cards for someone who called you
• Talk to a friend or family member before acting
• Report to gfin-system.com/victim

💡 <b>Remember:</b> Fear is the scammer's weapon. If you feel rushed or scared, hang up. Real organizations give you time to verify.

🔗 <b>Report a scam:</b> gfin-system.com/victim
<i>— GFIN Global Fraud Intelligence Network</i>"""
    },
    {
        "scam_type": "CRYPTO_FRAUD",
        "emoji": "₿",
        "title": "Crypto Fraud — The New Wild West",
        "body": """🚨 <b>SCAM AWARENESS: Crypto Fraud</b> ₿

<b>"Send me 0.1 BTC, I'll send back 0.2 BTC. Limited time!"</b>

⚠️ <b>STOP. Nobody gives away free crypto.</b>

<b>How it works:</b>
1️⃣ Scammer posts on social media or Telegram about a "giveaway" or "airdrop"
2️⃣ "Send X, receive 2X back" — it sounds like free money
3️⃣ The first few "investors" actually get paid (using other victims' money)
4️⃣ Word spreads, more people send crypto
5️⃣ Suddenly the wallet goes silent — all funds drained
6️⃣ Crypto transactions cannot be reversed

🚩 <b>Red flags:</b>
• "Send crypto, receive more crypto back"
• Famous person "endorsing" a giveaway (deepfake or hacked account)
• Unverified Telegram groups promising returns
• "Act now, limited time" pressure
• Wallet address posted publicly for "deposits"
• No whitepaper, no team, no audit — just "trust us"

✅ <b>How to protect yourself:</b>
• Never send crypto to someone you don't know
• Verify on official channels, not Telegram groups
• Check wallet addresses on blockchain explorers
• If it's a "giveaway," it's a scam
• Never share your seed phrase with anyone
• Report to gfin-system.com/victim

💡 <b>Remember:</b> Crypto transactions are irreversible. Once it's sent, it's gone. Always verify the recipient and the offer through official channels.

🔗 <b>Report a scam:</b> gfin-system.com/victim
<i>— GFIN Global Fraud Intelligence Network</i>"""
    },
    {
        "scam_type": "TECH_SUPPORT",
        "emoji": "💻",
        "title": "Tech Support Scams — Your Computer is NOT Infected",
        "body": """🚨 <b>SCAM AWARENESS: Tech Support Scams</b> 💻

<b>"Your computer has a virus. Call this number now."</b>

⚠️ <b>STOP. That pop-up is the virus.</b>

<b>How it works:</b>
1️⃣ You see a pop-up: "Virus detected! Call Microsoft/Apple support now!"
2️⃣ Or someone calls you claiming to be from "tech support"
3️⃣ They ask for remote access to "fix" your computer
4️⃣ Once inside, they "find" more problems that cost money to fix
5️⃣ They steal your passwords, banking info, and personal files
6️⃣ They may install real malware or ransomware

🚩 <b>Red flags:</b>
• Pop-up with phone number to call
• Caller says they're from Microsoft, Apple, or your ISP
• They want remote access (AnyDesk, TeamViewer, etc.)
• They ask for payment via gift cards or crypto
• They show you "error logs" that look scary but are normal

✅ <b>How to protect yourself:</b>
• Microsoft/Apple NEVER call you about viruses
• Close the pop-up — don't call the number
• Never give remote access to your computer
• Run your own antivirus scan if worried
• Report to gfin-system.com/victim

💡 <b>Remember:</b> Real tech support doesn't cold-call people. If you didn't contact them, they're not helping you.

🔗 <b>Report a scam:</b> gfin-system.com/victim
<i>— GFIN Global Fraud Intelligence Network</i>"""
    },
    {
        "scam_type": "ADVANCE_FEE",
        "emoji": "💰",
        "title": "Advance Fee Scams — Pay First, Get Nothing",
        "body": """🚨 <b>SCAM AWARENESS: Advance Fee Scams</b> 💰

<b>"You've won $1,000,000! Just pay the $500 processing fee first."</b>

⚠️ <b>STOP. If you won money, you don't pay to receive it.</b>

<b>How it works:</b>
1️⃣ You get an email, letter, or call: "You've won a lottery/inheritance/grant"
2️⃣ But you never entered any lottery
3️⃣ To claim your "winnings," you must pay a "processing fee," "tax," or "legal fee"
4️⃣ You pay. There's another fee. Then another. Each one "required"
5️⃣ The fees never end and the winnings never arrive

🚩 <b>Red flags:</b>
• You won something you never entered
• You must pay a fee to receive your "prize"
• They use a free email (gmail, yahoo) for an "official" lottery
• Pressure to act quickly before the "offer expires"
• They ask for your bank details "to deposit your winnings"
• Poor grammar and spelling in "official" documents

✅ <b>How to protect yourself:</b>
• You can't win a lottery you didn't enter
• Never pay money to receive money
• Legitimate lotteries deduct taxes from winnings
• Don't share your bank details with unknown parties
• Report to gfin-system.com/victim

💡 <b>Remember:</b> If you have to pay money to get money, it's a scam. Real winnings come without upfront fees.

🔗 <b>Report a scam:</b> gfin-system.com/victim
<i>— GFIN Global Fraud Intelligence Network</i>"""
    },
    {
        "scam_type": "LOTTERY_SCAM",
        "emoji": "🎰",
        "title": "Lottery & Sweepstakes Scams",
        "body": """🚨 <b>SCAM AWARENESS: Lottery & Sweepstakes Scams</b> 🎰

<b>"Congratulations! Your email was randomly selected to win $500,000!"</b>

⚠️ <b>STOP. Random email selection = scam.</b>

<b>How it works:</b>
1️⃣ Email or SMS says you won a lottery or sweepstakes
2️⃣ It uses real lottery names (EuroMillions, Powerball, etc.)
3️⃣ You must pay "transfer fees," "insurance," or "taxes" upfront
4️⃣ They send fake certificates and documents to look official
5️⃣ They keep asking for more payments for various "clearance" steps
6️⃣ You never receive a cent

🚩 <b>Red flags:</b>
• You didn't buy a ticket
• They use a free email service
• They ask for personal info and bank details
• They demand confidentiality ("don't tell anyone")
• The "notification" has spelling errors

✅ <b>How to protect yourself:</b>
• You can't win a lottery you didn't enter
• Real lotteries don't email random people
• Never pay fees to claim "winnings"
• Block and report the sender
• File a report at gfin-system.com/victim

💡 <b>Remember:</b> If you didn't buy a ticket, you didn't win. Period.

🔗 <b>Report a scam:</b> gfin-system.com/victim
<i>— GFIN Global Fraud Intelligence Network</i>"""
    },
    {
        "scam_type": "WIRE_FRAUD",
        "emoji": "🏦",
        "title": "Wire Fraud — Your Bank is NOT Calling",
        "body": """🚨 <b>SCAM AWARENESS: Wire Fraud</b> 🏦

<b>"This is your bank. We detected suspicious activity. Transfer your money to a safe account."</b>

⚠️ <b>STOP. Your bank will never ask you to transfer to a "safe account."</b>

<b>How it works:</b>
1️⃣ Scammer calls pretending to be your bank
2️⃣ They say there's fraud on your account — you need to act NOW
3️⃣ They tell you to transfer your money to a "safe account" (theirs)
4️⃣ Or they ask you to approve a "test transaction"
5️⃣ They may already have some of your info (from a data breach)
6️⃣ Once you transfer, the money is gone

🚩 <b>Red flags:</b>
• Caller says they're from your bank and there's an "emergency"
• They ask you to transfer money to a different account
• They want you to stay on the phone during the transfer
• They ask for your online banking credentials
• They send you a "verification code" and ask you to read it back
• They tell you not to visit a branch or call the official number

✅ <b>How to protect yourself:</b>
• Hang up and call your bank directly (use the number on your card)
• Your bank will NEVER ask you to transfer to a "safe account"
• Never share your PIN, password, or one-time code
• If in doubt, visit a branch in person
• Report to gfin-system.com/victim

💡 <b>Remember:</b> Banks protect your money — they don't ask you to move it. If there's real fraud, the bank handles it, not you.

🔗 <b>Report a scam:</b> gfin-system.com/victim
<i>— GFIN Global Fraud Intelligence Network</i>"""
    },
    {
        "scam_type": "SOCIAL_MEDIA_HACK",
        "emoji": "👤",
        "title": "Social Media Account Takeover",
        "body": """🚨 <b>SCAM AWARENESS: Social Media Account Takeover</b> 👤

<b>"Your friend sent you a link on Instagram. Just click it!"</b>

⚠️ <b>STOP. Your friend's account may be hacked.</b>

<b>How it works:</b>
1️⃣ Scammer hijacks someone's social media account
2️⃣ They message the victim's friends: "Look at this!" or "Vote for me!"
3️⃣ The link leads to a fake login page
4️⃣ You enter your username and password
5️⃣ Now your account is hacked too
6️⃣ They use your account to scam YOUR friends and family

🚩 <b>Red flags:</b>
• A friend sends you a link with no context
• The link leads to a login page (Instagram, Facebook, etc.)
• The URL doesn't match the real site
• "I need you to vote for me" or "Check this out"
• Shortened URLs that hide the real destination

✅ <b>How to protect yourself:</b>
• Don't click links from friends that seem unusual
• If unsure, ask them in person or by phone
• Enable two-factor authentication (2FA) on all accounts
• Check the URL before entering any login details
• Report to gfin-system.com/victim

💡 <b>Remember:</b> If a friend's message seems off, verify through another channel. Your caution protects both you and your friends.

🔗 <b>Report a scam:</b> gfin-system.com/victim
<i>— GFIN Global Fraud Intelligence Network</i>"""
    },
    {
        "scam_type": "JOB_SCAM",
        "emoji": "💼",
        "title": "Job Scams — Pay to Work?",
        "body": """🚨 <b>SCAM AWARENESS: Job Scams</b> 💼

<b>"Earn $5,000/week from home. Pay $200 for training materials first."</b>

⚠️ <b>STOP. Real jobs pay YOU, not the other way around.</b>

<b>How it works:</b>
1️⃣ Scammer posts a job ad on social media or job sites
2️⃣ High pay, flexible hours, work from home — sounds perfect
3️⃣ They interview you via chat (no video call)
4️⃣ They hire you immediately — too easy
5️⃣ They ask for "training fees," "equipment deposit," or "background check fee"
6️⃣ Or they send you a fake check to buy equipment and ask for the difference back
7️⃣ You lose money, they steal your identity, or you become a money mule

🚩 <b>Red flags:</b>
• You must pay money to get the job
• The salary is unrealistically high
• Interview is only via text/chat
• They hire you without verifying qualifications
• They send you a check before you start working
• They ask for your bank info "for direct deposit" before hiring

✅ <b>How to protect yourself:</b>
• Real employers don't ask you to pay for a job
• Research the company — check their official website
• Verify the job posting on the company's career page
• Never pay for "training materials" or "equipment"
• Never accept a check and send money back
• Report to gfin-system.com/victim

💡 <b>Remember:</b> If you have to pay to work, it's not a job — it's a scam. Real employers pay you.

🔗 <b>Report a scam:</b> gfin-system.com/victim
<i>— GFIN Global Fraud Intelligence Network</i>"""
    },
]


# State file to track which messages have been sent
AWARENESS_STATE_FILE = "/gfin/telegram_awareness_state.json"


def load_awareness_state() -> dict:
    """Load awareness broadcast state."""
    try:
        with open(AWARENESS_STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"last_index": -1, "last_sent": 0, "sent_messages": []}


def save_awareness_state(state: dict):
    """Save awareness broadcast state."""
    state["updated"] = time.time()
    with open(AWARENESS_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_next_awareness_message() -> dict:
    """Get the next awareness message in rotation (cycles through all)."""
    state = load_awareness_state()
    last_index = state.get("last_index", -1)
    next_index = (last_index + 1) % len(SCAM_AWARENESS_MESSAGES)
    
    state["last_index"] = next_index
    state["last_sent"] = time.time()
    save_awareness_state(state)
    
    return SCAM_AWARENESS_MESSAGES[next_index]


def send_awareness_broadcast() -> int:
    """
    Send the next scam awareness message to all subscribers.
    Call this from the 24/7 monitor every few hours.
    Returns number of messages sent.
    """
    bot = get_bot()
    if not bot:
        return 0

    subscribers = load_subscribers()
    if not subscribers:
        return 0

    message_data = get_next_awareness_message()
    
    sent_count = 0
    for chat_id in subscribers:
        if bot.send_message(chat_id, message_data["body"]):
            sent_count += 1
        time.sleep(0.05)

    # Log the broadcast
    state = load_awareness_state()
    state["sent_messages"].append({
        "scam_type": message_data["scam_type"],
        "title": message_data["title"],
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "recipients": sent_count,
    })
    # Keep only last 100 entries
    state["sent_messages"] = state["sent_messages"][-100:]
    save_awareness_state(state)

    return sent_count


def send_custom_awareness(scam_type: str) -> int:
    """Send a specific awareness message by scam type."""
    bot = get_bot()
    if not bot:
        return 0

    subscribers = load_subscribers()
    if not subscribers:
        return 0

    for msg in SCAM_AWARENESS_MESSAGES:
        if msg["scam_type"] == scam_type:
            sent_count = 0
            for chat_id in subscribers:
                if bot.send_message(chat_id, msg["body"]):
                    sent_count += 1
                time.sleep(0.05)
            return sent_count
    
    return 0


def get_awareness_stats() -> dict:
    """Get awareness broadcast statistics."""
    state = load_awareness_state()
    return {
        "total_types": len(SCAM_AWARENESS_MESSAGES),
        "last_index": state.get("last_index", -1),
        "last_sent": state.get("last_sent", 0),
        "total_broadcasts": len(state.get("sent_messages", [])),
        "recent": state.get("sent_messages", [])[-10:],
        "scam_types_covered": [m["scam_type"] for m in SCAM_AWARENESS_MESSAGES],
    }


if __name__ == "__main__":
    # Test: send awareness to all subscribers
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        stats = get_awareness_stats()
        print(f"Awareness system: {stats['total_types']} scam types")
        print(f"Last sent index: {stats['last_index']}")
        print(f"Total broadcasts: {stats['total_broadcasts']}")
        print(f"Types: {', '.join(stats['scam_types_covered'])}")
        print(f"\nNext message preview:")
        msg = get_next_awareness_message()
        print(f"  Type: {msg['scam_type']}")
        print(f"  Title: {msg['title']}")
        print(f"  Length: {len(msg['body'])} chars")
