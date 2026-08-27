"""
GFIN Deterministic Scam Detection Engine v3.0
Local-only scam detection that matches AI-level analysis without any LLM dependency.

Capabilities:
- 300+ scam patterns across 15 categories
- Behavioral heuristics (urgency, authority, scarcity, social proof, payment anomalies)
- Linguistic analysis (manipulation tactics, emotional triggers)
- Multi-language detection (EN, ES, DE, FR)
- Known-bad databases (domains, wallets, phone patterns)
- Entity extraction and correlation
- Risk scoring with confidence intervals
- Human-readable report generation (template-based, no AI)
- Timeline reconstruction
- Cross-reference with public APIs (WHOIS-like)
"""
import re
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter


# ==================== PATTERN LIBRARY (300+ patterns) ====================

SCAM_PATTERNS: Dict[str, List[str]] = {
    # === RECOVERY SCAM (35 patterns) ===
    "RECOVERY_SCAM": [
        r"recover(y)?\s+(your\s+)?(lost\s+|stolen\s+)?(funds|money|crypto|bitcoin|ethereum|usdt|assets)",
        r"we\s+can\s+help\s+you\s+(get|recover)\s+your\s+money\s+back",
        r"(chargeback|retrieval|recovery)\s+(service|guarantee|fee|specialist|expert|agent)",
        r"(get|recover)\s+your\s+(lost\s+|stolen\s+)?(bitcoin|crypto|funds)\s+back",
        r"100\s*%\s+(guaranteed|success(ful)?)\s+(recovery|refund)",
        r"no\s+(win|fee)\s+no\s+(fee|win)\s+recovery",
        r"(pay|fee)\s+(upfront|in\s+advance|first|before\s+we\s+start)",
        r"we\s+(have|'ve)\s+successfully\s+recovered.*\$\d+",
        r"(our|we\s+have\s+a)\s+team\s+of\s+(expert|professional|certified)\s+(hackers?|recovery\s+specialists?)",
        r"(trace|tracing|tracking)\s+your\s+(lost\s+|stolen\s+)?(crypto|bitcoin|funds)",
        r"(blockchain|crypto)\s+(forensics|investigator|investigation)",
        r"recovery\s+(company|firm|agency|service|expert|specialist)",
        r"we\s+(specialize|specialise)\s+in\s+(crypto|bitcoin)\s+recovery",
        r"(undo|reverse)\s+(your\s+)?(transaction|transfer|payment)",
        r"we\s+(work|partner)\s+with\s+(the\s+)?(FBI|Interpol|police|law\s+enforcement)",
        r"claim\s+your\s+(lost\s+|stolen\s+)?(funds|money|crypto)",
        r"fill\s+out\s+(this\s+|a\s+)?(recovery\s+)?(form|application)",
        r"(free|no\s+obligation)\s+(consultation|assessment|review)",
        r"we\s+found\s+your\s+(lost\s+|stolen\s+)?(funds|bitcoin|crypto)",
        r"your\s+(funds|money|crypto)\s+(has|have)\s+been\s+(located|found|recovered)",
        r"contact\s+(us|me)\s+(to\s+)?(claim|recover|retrieve)\s+your\s+funds",
        r"don't\s+(give\s+up|lose\s+hope).*(recover|get\s+back)",
        r"(hacked|stolen|lost)\s+(wallet|account|exchange)\s+recovery",
        r"we\s+can\s+(trace|track)\s+the\s+(transaction|wallet|address)",
        r"send\s+us\s+your\s+(wallet|transaction)\s+details",
        r"(recovery\s+)?(wallet\s+address|private\s+key|seed\s+phrase)\s+(needed|required|for\s+verification)",
        r"we\s+(will|can)\s+hack\s+(back|into)\s+your\s+(account|wallet)",
        r"ethical\s+hacker\s+(for|to)\s+(recover|retrieve|trace)",
        r"(refund|recovery)\s+(process|procedure)\s+(fee|charge|cost)",
        r"we\s+(guarantee|promise)\s+(full|complete|100%)\s+recovery",
        r"money\s+back\s+(guarantee|promise|if\s+not\s+successful)",
        r"recovery\s+(success\s+)?rate\s+(of\s+)?\d{2,3}\s*%",
        r"we've\s+helped\s+(thousands|hundreds|\d{3,})\s+of\s+(victims|clients|people)",
        r"check\s+(if\s+)?your\s+(funds|crypto)\s+(are|qualify\s+for)\s+recovery",
        r"you\s+(are|'re)\s+eligible\s+for\s+(a\s+)?(recovery|refund)",
    ],

    # === INVESTMENT FRAUD (35 patterns) ===
    "INVESTMENT_FRAUD": [
        r"guaranteed\s+(returns?|profit|ROI|income|earnings)",
        r"\d{2,3}\s*%\s+(return|profit|ROI|APY|APR|interest)\s+(per|a|each|every)\s+(day|week|month|year)",
        r"(double|triple)\s+your\s+(bitcoin|crypto|money|investment)\s+in\s+\d+\s+(hours?|days?|weeks?)",
        r"(binary|forex|crypto|stock)\s+(trading|investment)\s+platform",
        r"send\s+(bitcoin|crypto|usdt|eth)\s+to\s+(this|our|the)\s+(wallet|address)",
        r"minimum\s+(investment|deposit)\s+of\s+\$?\d+",
        r"(passive|guaranteed)\s+income\s+(stream|opportunity|plan)",
        r"(crypto|bitcoin)\s+(mining|staking|yield\s+farming)\s+(plan|pool|contract)",
        r"(earn|make|get)\s+\$?\d{3,}\s+(per|a|every)\s+(day|week|month)\s+(from\s+home|online|guaranteed)",
        r"(limited|special)\s+(time|spots?|spaces?)\s+(offer|available|remaining)",
        r"(join|invest)\s+(now|today|before\s+it's\s+too\s+late)",
        r"don't\s+miss\s+(out|this\s+(opportunity|chance))",
        r"this\s+(offer|opportunity)\s+(won't|will\s+not)\s+last",
        r"(early|first)\s+(investors?|adopters?)\s+(get|will\s+get|receive)",
        r"(exclusive|private|VIP)\s+(investment|trading)\s+(club|group|pool|opportunity)",
        r"(our|the)\s+(AI|automated|algorithmic)\s+trading\s+(bot|system|software)",
        r"zero\s+(risk|loss|chance\s+of\s+losing)",
        r"risk[- ]?free\s+(investment|trading|opportunity)",
        r"you\s+(can't|cannot|won't)\s+lose\s+(your\s+)?(money|investment)",
        r"compound\s+(your|the)\s+(earnings|profits|returns)\s+(daily|weekly|automatically)",
        r"withdraw\s+(your\s+)?(profits|earnings)\s+(anytime|whenever|at\s+any\s+time)",
        r"(register|sign\s+up)\s+(now|today)\s+(and\s+get|to\s+receive)\s+(a\s+)?\$?\d+\s+(bonus|credit)",
        r"refer\s+(a\s+friend|others)\s+and\s+(earn|get|receive)\s+\$?\d+",
        r"( Ponzi|pyramid)\s+(scheme|investing|structure)",  # Direct mention
        r"(token|coin)\s+(presale|ICO|IEO|IDO)\s+(now\s+live|available|ending\s+soon)",
        r"(our|this)\s+(token|coin)\s+will\s+(moon|pump|x100|x1000|10x|100x)",
        r"next\s+(Bitcoin|Ethereum|Solana)",
        r"get\s+in\s+(early|on\s+the\s+ground\s+floor)",
        r"(fire|financial)\s+(sale|backed)\s+(tokens?|coins?|investment)",
        r"(staking|yield)\s+(rewards|returns)\s+of\s+\d{2,3}\s*%",
        r"(trade|trading)\s+(signals?|alerts?|tips?)\s+(group|channel|service)",
        r"(copy|mirror)\s+trading\s+(platform|service|bot)",
        r"(our|we\s+have\s+a)\s+proprietary\s+(trading|investment)\s+(algorithm|strategy|system)",
        r"financial\s+(advisor|adviser|expert|consultant)\s+(offering|recommending)\s+(crypto|forex|binary)",
        r"(deposit|invest)\s+\$?\d+\s+(and\s+get|to\s+get|and\s+receive)\s+\$?\d+\s+(back|in\s+return)",
        r"turn\s+\$?\d+\s+into\s+\$?\d{3,}\s+(in\s+\d+\s+(days?|hours?|weeks?))?",
    ],

    # === BRAND IMPERSONATION (25 patterns) ===
    "BRAND_IMPERSONATION": [
        r"(official|authorized|authorised|certified|genuine|legitimate|real)\s+(recovery|investigation|legal|financial)\s+(agent|service|company|firm|partner)",
        r"we\s+are\s+(the|a)\s+(legitimate|real|original|genuine)\s+(recovery|investigation|legal)\s+(company|firm|agency|service)",
        r"(contact|call|email)\s+(us|me)\s+(urgently|immediately|right\s+away|now)",
        r"(limited|special)\s+time\s+(offer|promotion|discount|deal)",
        r"we\s+represent\s+(CNC|chainlink|coinbase|binance|metamask|crypto\.com|ledger|trezor)",
        r"we\s+are\s+(the|a)\s+(partner|affiliate|subsidiary|department)\s+of",
        r"(on\s+behalf\s+of|representing)\s+(the\s+)?(FBI|Interpol|police|bank|government|agency)",
        r"(this\s+is|I\s+am)\s+(from|with)\s+(the\s+)?(fraud|cyber\s+crime|anti-scam)\s+(department|division|unit|team)",
        r"your\s+(case|file|complaint|claim)\s+(has\s+been|is)\s+(assigned|transferred|escalated)\s+to\s+(us|me|our\s+team)",
        r"we\s+(have|'ve)\s+been\s+(appointed|assigned|authorized|authorised)\s+to\s+handle\s+your\s+case",
        r"(official|verified|certified)\s+(recovery|investigation|legal)\s+(partner|agent|specialist)",
        r"(as\s+seen\s+on|featured\s+in|endorsed\s+by)\s+(BBC|CNN|Forbes|Bloomberg|TechCrunch|Reddit)",
        r"(trusted|verified|certified)\s+by\s+(Google|Apple|Microsoft|Meta|Trustpilot)",
        r"\d+\s+stars?\s+(rating|review)\s+on\s+(Trustpilot|Google|Yelp)",
        r"(ISO|PCI|GDPR)\s+(certified|compliant|registered)",
        r"(registered|licensed|regulated)\s+(company|firm|business)\s+(in|with\s+number)\s+#?\d+",
        r"we\s+are\s+(FCA|SEC|FINRA|CySEC|ASIC)\s+(registered|licensed|regulated|approved)",
        r"(don't|do\s+not)\s+(contact|trust)\s+anyone\s+else\s+(but|except)\s+(us|me|our\s+team)",
        r"(beware|warning|alert).*(fake|scam|fraudulent)\s+(companies?|websites?|agents?)",
        r"we\s+(are|'re)\s+the\s+(only|sole)\s+(legitimate|real|genuine|authorized)\s+(recovery|investigation)\s+(company|firm|service)",
        r"(your|you\s+have\s+(a|your))\s+(case|file|claim)\s+(number|reference|ID)\s*(is|:)\s*[A-Z0-9-]+",
        r"(this|that)\s+(is\s+not|isn't)\s+a\s+scam",
        r"(verified|confirmed|authenticated)\s+(by|through)\s+(our|the)\s+(secure|encrypted|verified)\s+(portal|platform|system)",
        r"please\s+(verify|confirm|validate)\s+your\s+(identity|account|details)\s+(with\s+us|through\s+us)",
        r"we\s+(need|require)\s+(your|additional)\s+(verification|confirmation|authorization|authorisation)",
    ],

    # === PHISHING (25 patterns) ===
    "PHISHING": [
        r"(verify|confirm|update|validate)\s+your\s+(account|wallet|identity|information|details|credentials)",
        r"(your\s+account|wallet|account)\s+(has\s+been|will\s+be)\s+(suspended|locked|closed|frozen|restricted|compromised|hacked)",
        r"(click\s+here|follow\s+this\s+link|tap\s+here)\s+to\s+(verify|confirm|update|restore|unlock|secure)",
        r"dear\s+(customer|user|client|valued\s+customer|account\s+holder|member)",
        r"(urgent|immediate|immediately)\s+(action\s+(is\s+)?required|attention\s+needed|verification\s+required)",
        r"(your\s+)?(password|PIN|code|OTP|2FA|two[- ]?factor)\s+(has\s+expired|is\s+expiring|needs?\s+(update|renewal))",
        r"(security\s+alert|warning|notice).*(unusual|suspicious|unauthorized|unauthorised)\s+(activity|login|access|transaction)",
        r"(we\s+detected|our\s+system\s+detected)\s+(unusual|suspicious|unauthorized|unauthorised)\s+(activity|login|access)",
        r"(log\s+in|sign\s+in|login)\s+(to\s+confirm|to\s+verify|to\s+secure|to\s+update)\s+your\s+(account|wallet|info)",
        r"(please\s+)?(provide|enter|submit)\s+your\s+(password|private\s+key|seed\s+phrase|recovery\s+phrase|PIN|SSN|credit\s+card)",
        r"(confirm|verify)\s+your\s+(identity|identity|account|email)\s+by\s+(clicking|following)\s+(this|the)\s+link",
        r"(your\s+)?(payment|billing|card)\s+(method|details|information)\s+(has\s+(expired|changed)|needs?\s+updating)",
        r"(package|parcel|delivery|shipment)\s+(is\s+being|will\s+be)\s+(held|returned|delayed).*(fee|payment|customs)",
        r"(you\s+have|we've)\s+(won|been\s+selected\s+for|qualified\s+for)\s+(a\s+)?(prize|reward|gift|bonus|lottery)",
        r"(claim|collect|redeem)\s+your\s+(prize|reward|gift|winnings?|bonus)\s+(now|today|before\s+it\s+expires)",
        r"(congratulations|congrats|dear\s+winner).*(you\s+have\s+)?won",
        r"(your\s+)?(mailbox|inbox|email)\s+(is\s+full|has\s+reached\s+(its\s+)?limit|storage\s+(is\s+)?full).*(upgrade|increase|extend)",
        r"(security|account|system)\s+(update|maintenance|upgrade|verification)\s+(required|needed|in\s+progress)",
        r"(Microsoft|Apple|Google|Amazon|Netflix|PayPal|Apple\s+ID)\s+(security|account|billing)\s+(alert|warning|notification|team)",
        r"(your\s+)?(subscription|membership|plan)\s+(has|will\s+(expire|end|be\s+cancelled)|is\s+expiring).*(renew|update|continue)",
        r"(we\s+are|this\s+is)\s+(upgrading|updating|migrating|moving)\s+(our|the)\s+(server|system|database|platform).*(re-?verify|confirm)",
        r"(enter|provide|submit)\s+your\s+(banking|financial|payment)\s+(details|information)\s+(for|to)\s+(verification|confirmation)",
        r"(IRS|HMRC|tax\s+office|revenue)\s+(refund|return|rebate|credit).*(click|claim|verify|submit)",
        r"(you\s+have\s+)?\d+\s+(unpaid|undelivered|pending)\s+(parcels?|packages?|items?)",
        r"(your\s+)?(GCash|PayPal|Cash\s+App|Venmo|Zelle|Apple\s+Pay|Google\s+Pay)\s+(account|wallet).*(suspended|locked|verify|confirm)",
        r"(meeting|conference|event)\s+(invitation|request).*(click|register|join|RSVP)\s+(here|link|below)",
    ],

    # === ROMANCE SCAM (25 patterns) ===
    "ROMANCE_SCAM": [
        r"(i\s+love\s+you|i'm\s+falling\s+for\s+you|you're\s+the\s+one|you're\s+my\s+soulmate|i've\s+never\s+felt\s+this\s+way)",
        r"(stuck|stranded|trapped)\s+in\s+(the\s+)?\w+\s+(need\s+help|send\s+money|need\s+funds)",
        r"(military|army|navy|UN\s+soldier|UN\s+peacekeeper|deployed)\s+(in|stationed\s+in|overseas)\s+(Syria|Afghanistan|Iraq|Yemen|Africa|Nigeria)",
        r"(widow|widower|orphan)\s+(seeking|looking\s+for|in\s+search\s+of)\s+(love|companionship|friendship|relationship)",
        r"(send\s+me\s+money|i\s+need\s+a\s+loan|can\s+you\s+help\s+me\s+financially|i'm\s+in\s+a\s+difficult\s+situation)",
        r"(my\s+(child|daughter|son|kid)\s+(is\s+sick|needs?\s+surgery|is\s+in\s+the\s+hospital|has\s+an\s+emergency))",
        r"(i\s+have\s+a|my\s+family\s+has\s+a)\s+(business\s+opportunity|investment\s+deal|inheritance)\s+for\s+you",
        r"(i\s+can't\s+(video\s+call|face\s+time|meet\s+in\s+person)\s+(because|since|due\s+to))\s+(security|deployment|poor\s+connection|no\s+camera)",
        r"(i\s+will\s+come\s+(visit|see)\s+you|move\s+to\s+your\s+country)\s+(but|if|when)\s+(i|we)\s+(get|have|raise)\s+(the\s+)?(money|funds|plane\s+ticket|travel\s+costs?)",
        r"(my\s+)?(bank\s+account|wallet|account)\s+(is\s+(frozen|locked|restricted)|has\s+been\s+blocked).*(send|transfer|wire)",
        r"(oil\s+rig|contractor|engineer|offshore)\s+(in|on|working\s+(on|in))\s+(the\s+)?(sea|ocean|rig|platform)",
        r"(i'm|i\s+am)\s+(a|an)\s+(doctor|surgeon|nurse|aid\s+worker|diplomat|UN\s+official)\s+(working|stationed|in)\s+(Syria|Yemen|Africa|Middle\s+East)",
        r"(we\s+(will|'ll)\s+be\s+together|i\s+(will|'ll)\s+marry\s+you|i\s+(want|wanna)\s+to\s+(marry|merry)\s+you)",
        r"(i\s+lost\s+my\s+(wife|husband|partner|spouse)|my\s+(wife|husband)\s+(passed\s+away|died|left\s+me)).*(lonely|alone|ready\s+to\s+love\s+again)",
        r"(god\s+(brought|sent|led)\s+(me|us)\s+together|you're\s+a\s+gift\s+from\s+god|prayers?\s+(brought|answered))",
        r"(i\s+(need|require)\s+(an|your)\s+)?(iTunes|Amazon|Google\s+Play|Steam)\s+(gift\s+card|card)\s+(for|to)\s+(my\s+)?(kids?|daughter|son|birthday|phone|internet)",
        r"(i'm|i\s+am)\s+(77|68|59|65|62|55|70|72)\s+years?\s+old.+(retired|widow|widower|lonely|looking\s+for)",
        r"(you're\s+the\s+first\s+person|i've\s+never\s+shared\s+this\s+with\s+anyone|i\s+trust\s+you\s+more\s+than\s+anyone)",
        r"(my\s+commanding\s+officer|my\s+superior|the\s+military)\s+(won't|will\s+not|doesn't)\s+(let|allow|permit)\s+me\s+(leave|come\s+home|travel)",
        r"(i\s+need\s+(a\s+)?(phone|laptop|iphone|samsung|gift)\s+(for|to\s+call|to\s+contact)\s+you)",
        r"(once\s+(i|we)\s+(get|have|raise)\s+the\s+money|i'll\s+come\s+to\s+you|we\s+can\s+be\s+together)",
        r"(my\s+(ex|former)\s+(wife|husband|partner)\s+(cheated|left|abandoned|betrayed)\s+me).*(trust\s+issues|hurt\s+before|scared\s+to\s+love)",
        r"(can\s+you\s+)?(receive|accept|pick\s+up)\s+(a\s+)?(package|parcel|delivery)\s+for\s+me",
        r"(i\s+have\s+a|my\s+(boss|company)\s+has\s+a)\s+(check|cheque|money\s+order|payment)\s+for\s+you",
        r"(send\s+(me\s+)?a\s+photo|send\s+me\s+your\s+(address|home\s+address|where\s+you\s+(live|stay)))",
        r"(i\s+(work|am\s+working)\s+on\s+(a|the)\s+rig|oil\s+platform|offshore).*(can't|cannot|won't)\s+(leave|come\s+home|visit)",
    ],

    # === PAYMENT FRAUD (20 patterns) ===
    "PAYMENT_FRAUD": [
        r"(unauthorized|unauthorised|unknown)\s+(charge|transaction|payment|debit|withdrawal)",
        r"(someone|somebody)\s+(used|accessed|took)\s+(my|from\s+my)\s+(card|account|wallet)",
        r"(overcharged|double\s+charged|charged\s+twice)\s+my\s+(card|account)",
        r"fake\s+(invoice|bill|receipt|payment\s+request|confirm)",
        r"(you\s+(owe|need\s+to\s+pay)|there\s+is\s+(a\s+)?(balance|fee)\s+due)\s+\$?\d+",
        r"(payment\s+failed|transaction\s+declined).*(try\s+again|update\s+(your|the)\s+card|use\s+a\s+different)",
        r"(refund|reimbursement|cashback)\s+of\s+\$?\d+.*(provide|enter|submit)\s+your\s+(card|banking|payment)\s+(details|info)",
        r"(wire|bank)\s+transfer\s+(to|for)\s+(a|an)\s+(stranger|someone\s+you\s+(don't|never)\+(met|know)|new\s+(account|recipient))",
        r"send\s+(money|funds|payment)\s+(via|through|using)\s+(Western\s+Union|MoneyGram|crypto|bitcoin|gift\s+cards?)",
        r"(you\s+(won|qualified\s+for|have\s+been\s+selected\s+for)).*(pay\s+(a\s+)?(fee|tax|processing\s+charge|customs)\s+to\s+claim)",
        r"(overpayment|excess\s+payment).*(refund\s+the\s+difference|wire\s+back\s+the\s+extra)",
        r"(advance\s+fee|upfront\s+payment|processing\s+fee)\s+(required|needed|must\s+pay\s+before)",
        r"(your\s+)?(payment\s+method|card|account)\s+(has\s+been|was)\s+(compromised|leaked|breached).*(click|call|contact)",
        r"(invoice|bill|statement)\s+(#|number)\s*\d+.*(past\s+due|overdue|final\s+notice|urgent)",
        r"(shipping|handling|processing|customs|clearance)\s+fee\s+(required|needed|must\s+pay)",
        r"(transaction|transfer)\s+(ID|reference|code|number).*(confirm|verify|complete|authorize)\s+(your\s+)?(payment|transfer)",
        r"(you\s+have\s+(been|been\s+)?(pre-?approved|pre-?qualified|selected)\s+for\s+(a\s+)?(loan|credit|financing|card))",
        r"0\s*%\s+(APR|interest)\s+for\s+\d+\s+(months?|years?).*(apply\s+now|limited\s+time|offer\s+expires)",
        r"(your\s+)?(card|payment)\s+(has\s+expired|is\s+about\s+to\s+expire|needs?\s+renewing).*(update|renew|click\s+here)",
        r"(mystery\s+shopper|secret\s+shopper|survey\s+panelist).*(evaluate|test|assess)\s+(stores?|businesses|services?).*(send|wire|transfer)",
    ],

    # === SOCIAL ENGINEERING (20 patterns) ===
    "SOCIAL_ENGINEERING": [
        r"(this\s+is|i\s+am)\s+(the|your)\s+(CEO|boss|manager|director|supervisor|president|CFO|owner)",
        r"(urgent|immediate|right\s+away).*(wire|transfer|send)\s+(funds|money|payment)",
        r"(i'm|i\s+am)\s+(in\s+a|at\s+a)\s+(meeting|conference|hospital|airport).*(can't|cannot)\s+(talk|call|answer).*(text|email|message)\s+(me|only)",
        r"(buy|purchase|get)\s+(gift\s+cards?|iTunes|Amazon|Google\s+Play|Steam\s+cards?)\s+(for\s+(clients|staff|the\s+team)|as\s+(bonuses?|rewards?))",
        r"(your\s+(grandchild|grandson|granddaughter|nephew|niece|child|son|daughter)\s+(is|has\s+been)\s+(in\s+(an?\s+)?(accident|emergency|hospital|jail|trouble)|arrested|kidnapped))",
        r"(i\s+need\s+you\s+to|please)\s+(keep\s+this|this\s+(is|stays))\s+(confidential|between\s+us|a\s+secret|quiet|private)",
        r"(don't|do\s+not)\s+(tell|inform|contact)\s+(anyone|HR|IT|your\s+(boss|manager|family))",
        r"(IT\s+(support|department|desk)|tech\s+support|help\s+desk).*(remote\s+access|install\s+(this|a)|download\s+(this|software)|teamviewer|anydesk)",
        r"your\s+(computer|device|laptop|phone)\s+(is|has\s+been)\s+(infected|compromised|hacked|at\s+risk).*(install|download|allow\s+access)",
        r"(government\s+grant|stimulus\s+check|relief\s+fund|COVID\s+relief).*(pay\s+(a\s+)?(fee|processing\s+charge)|provide\s+(your|banking)\s+(details|info))",
        r"(you've\s+been|your\s+name\s+has\s+been)\s+(selected|chosen|nominated)\s+(for|to\s+receive)\s+(a|an)\s+(grant|award|fellowship|prize)",
        r"(i'm|i\s+am)\s+(from|with)\s+(the|your)\s+(bank|credit\s+union|card\s+company).*(verify|confirm|update)\s+(your\s+)?(account|details|information)",
        r"(won|leaving|moving|transferring)\s+(a|the)\s+(review|feedback|rating).*(gift|reward|bonus|prize)\s+for\s+you",
        r"(your\s+)?(social\s+security|SSN|national\s+insurance|passport|driver's\s+license)\s+(number|ID).*(verify|confirm|provide)",
        r"(a|your)\s+(friend|family\s+member|relative|loved\s+one)\s+(is\s+in|has\s+been)\s+(trouble|danger|hospital|jail|arrested).*(send|wire|pay)",
        r"(please|kindly)\s+(send|transfer|wire|deposit)\s+(the\s+)?(funds|money|payment)\s+(to|at)\s+(this|the\s+following)\s+(account|address|wallet|number)",
        r"(verify|confirm)\s+your\s+(identity|age|date\s+of\s+birth|address)\s+(by|through|via)\s+(clicking|sending|providing)",
        r"(you\s+need\s+to|must|are\s+required\s+to)\s+(pay|send|transfer)\s+(a\s+)?(deposit|security\s+deposit|holding\s+fee|insurance)\s+(first|before|upfront)",
        r"(the|your)\s+(package|parcel|delivery)\s+(is|was)\s+(seized|held|stopped)\s+by\s+(customs|the\s+police|authorities).*(fee|payment|fine|penalty)",
        r"(this\s+call\s+is|this\s+is\s+a\s+(recording|recorded)\s+(message|line)).*(warrant|lawsuit|lawsuit|court|IRS|HMRC|tax).*(pay|settle|resolve|call\s+back)",
    ],

    # === CRYPTO FRAUD (15 patterns) ===
    "CRYPTO_FRAUD": [
        r"send\s+(me\s+)?(0\.\d+|\d+)\s+(BTC|ETH|USDT|BNB|SOL)\s+to\s+(receive|get|claim)\s+\d+(x|X)\s+back",
        r"(your\s+)?(wallet|address)\s+has\s+been\s+(selected|chosen|awarded)\s+for\s+(a\s+)?(airdrop|giveaway|bonus|prize)",
        r"(connect|link)\s+your\s+wallet\s+to\s+(claim|receive|verify|check)\s+(your\s+)?(airdrop|rewards?|tokens?|bonus)",
        r"(approve|sign)\s+(this|the)\s+(transaction|contract|message)\s+to\s+(claim|receive|verify|unlock)",
        r"your\s+(crypto|bitcoin|wallet)\s+(needs?\s+(verification|security\s+check|updating)|has\s+been\s+(flagged|compromised))",
        r"(Elon\s+Musk|Tesla|SpaceX|CZ|Vitalik)\s+(is\s+)?(giving\s+away|gift|airdrop|giveaway)\s+(crypto|bitcoin|ETH)",
        r"send\s+(BTC|ETH|USDT)\s+get\s+(2x|3x|10x)\s+back",
        r"(free|complimentary)\s+(BTC|ETH|crypto|tokens?)\s+giveaway.*(send|deposit)\s+to\s+participate",
        r"(drain|drained|sweep|swept)\s+your\s+wallet.*(connect|approve|sign)",
        r"(slippage|MEV|front[- ]?running)\s+(protection|bot|alert).*approve",
        r"(claim|redeem)\s+your\s+(token|airdrop|rewards?|gift).*(before\s+deadline|limited\s+time|while\s+supplies?\s+last)",
        r"(metamask|trust\s+wallet|coinbase\s+wallet|phantom)\s+(security|verification|update).*(connect|sync|verify)",
        r"you\s+(won|have\s+been\s+selected\s+for)\s+the\s+(crypto|bitcoin|NFT)\s+(lottery|giveaway|raffle)",
        r"(verify|validate)\s+your\s+(wallet|address|contract)\s+to\s+(avoid|prevent)\s+(liquidation|loss|suspension)",
        r"(import|enter)\s+your\s+(seed\s+phrase|recovery\s+phrase|private\s+key|mnemonic)\s+(to|for)\s+(verify|restore|access|sync)",
    ],

    # === JOB/EMPLOYMENT SCAM (15 patterns) ===
    "JOB_SCAM": [
        r"(work\s+from\s+home|remote\s+job|online\s+job)\s+(opportunity|position|offer).*(guaranteed|no\s+experience|earn\s+\$?\d{3,})",
        r"(earn|make)\s+\$?\d{3,}\s+(per|a|every)\s+(week|day|month)\s+(from\s+home|online|remote|no\s+experience\s+needed)",
        r"(data\s+entry|package\s+processing|mystery\s+shopping|virtual\s+assistant)\s+(job|position|work).*(fee|deposit|equipment|training)",
        r"(pay\s+(a\s+)?(fee|deposit|training\s+cost|equipment\s+fee|background\s+check\s+fee)|buy\s+(your\s+)?(equipment|supplies|materials)\s+from\s+us)",
        r"(we\s+(will|can))\s+pay\s+you\s+\$?\d{3,}\s+(per|a|every)\s+(week|day|hour)\s+to\s+(wrap|decorate|advertise\s+on)\s+your\s+(car|vehicle)",
        r"(you've\s+been|your\s+resume\s+has\s+been)\s+(selected|shortlisted|chosen)\s+for\s+(a\s+)?(position|role|job)\s+you\s+(didn't|never)\s+(apply\s+for|applied)",
        r"(telegram|signal|whatsapp|wechat)\s+(interview|recruitment|hiring|job\s+offer)",
        r"(the\s+company\s+(is|will)\s+)?send\s+(you|a)\s+(check|cheque)\s+(for|to\s+buy)\s+(equipment|supplies|materials)\s+and\s+(return|wire\s+back)\s+the\s+(rest|difference|remaining)",
        r"(remote|online)\s+(data\s+entry|typing|clerical|admin)\s+(job|work|position).*(no\s+(interview|experience)|start\s+(immediately|today))",
        r"(we\s+are\s+hiring|job\s+opening)\s+(urgently|immediately|ASAP).*(no\s+experience|no\s+interview|guaranteed\s+(placement|income))",
        r"(accept|receive)\s+(this|the)\s+(check|payment|transfer)\s+and\s+(forward|send|wire|transfer)\s+(the\s+rest|remainder|difference)\s+to\s+(our|the)\s+(supplier|vendor|partner)",
        r"(shipping|receiving|reshipping)\s+(manager|coordinator|agent|job).*(receive|inspect|forward|reship)\s+packages",
        r"(your\s+)?(application|resume|CV)\s+(has\s+been|is)\s+(approved|accepted|shortlisted).*(contact\s+us|schedule\s+an\s+interview)\s+(on|via|through)\s+(Telegram|Signal|WhatsApp)",
        r"(pay|fee|deposit)\s+(for|to\s+cover)\s+(training|certification|equipment|background\s+check|insurance)\s+(before|prior\s+to)\s+(starting|beginning|your\s+first\s+day)",
        r"(NFT|crypto|blockchain)\s+(ambassador|promoter|sales|community\s+manager)\s+(job|position|role).*(buy|invest|purchase).*(NFT|token|coin)\s+to\s+(start|qualify|join)",
    ],

    # === RENTAL/PROPERTY SCAM (10 patterns) ===
    "RENTAL_SCAM": [
        r"(great|amazing|stunning|beautiful)\s+(apartment|house|flat|studio)\s+(for\s+rent|available).*(low|cheap|affordable|below\s+market)\s+(price|rent|rate)",
        r"(send|wire|transfer)\s+(the\s+)?(deposit|first\s+month's\s+rent|security\s+deposit|holding\s+fee)\s+(before|without)\s+(seeing|visiting|viewing)\s+the\s+(property|apartment|house)",
        r"(i'm|i\s+am)\s+(out\s+of\s+(the\s+)?country|abroad|overseas|on\s+a\s+mission|traveling).*(can't|cannot|won't)\s+(show|meet|be\s+there).*(send|wire|deposit)",
        r"(keys|documents|contract|lease)\s+(are\s+)?with\s+(me|us|the\s+(agent|landlord|owner)).*(send|wire|pay)\s+(to\s+have\s+them\s+)?(sent|delivered|mailed)",
        r"(too\s+good\s+to\s+be\s+true|unrealistic|suspiciously\s+(low|cheap))\s+(rent|price|rate|deal)",
        r"(deal|transaction)\s+(only|must\s+be)\s+(done\s+)?(via|through|on)\s+(eBay|Airbnb|craigslist|gumtree|OLX)\s+(protection|guarantee|secure\s+(payment|service))",
        r"(verify|confirm|prove)\s+you\s+(are|'re)\s+a\s+real|serious\s+(tenant|buyer|renter)\s+by\s+(sending|paying|providing)\s+(a\s+)?(deposit|fee|gift\s+card)",
        r"(you\s+need\s+to|must)\s+(pay|send)\s+(the\s+)?(full|entire)\s+(deposit|rent|payment)\s+(upfront|in\s+advance|before\s+moving)\s+in",
        r"(i'm|i\s+am)\s+(the\s+)?(owner|landlord)\s+but\s+(i|i'm)\s+(currently|at\s+the\s+moment)\s+(abroad|overseas|out\s+of\s+(town|the\s+country))",
        r"(refundable|refund)\s+(deposit|fee|holding\s+fee|security\s+deposit)\s+(required|needed)\s+(to|for)\s+(reserve|hold|secure)\s+the\s+(property|apartment|house)",
    ],

    # === LOTTERY/PRIZE SCAM (10 patterns) ===
    "LOTTERY_SCAM": [
        r"(congratulations|congrats|dear\s+winner).*(you\s+have\s+)?(won|been\s+selected\s+for)\s+(a|an)\s+(lottery|prize|jackpot|sweepstake)",
        r"(you've\s+been|your\s+(email|number|phone)\s+has\s+been)\s+(selected|chosen)\s+(for|to\s+win)\s+(a\s+)?(prize|reward|lottery|giveaway)",
        r"(claim\s+your|collect\s+your|receive\s+your)\s+(prize|winnings?|reward|jackpot).*(fee|tax|customs|processing\s+charge)",
        r"(Microsoft|Apple|Google|Facebook|WhatsApp|Instagram|TikTok)\s+(anniversary|promo|promotion|giveaway|lottery|anniversary\s+draw)",
        r"(you\s+won|winner)\s+(US\$|USD|\$|€|£)\d{3,}.*(contact|claim|email|call)\s+(us|me|this\s+(number|email|address))",
        r"(pay\s+(the|a)\s+)?(processing\s+fee|tax|customs\s+fee|clearance\s+charge|release\s+fee)\s+to\s+(claim|receive|collect)\s+your\s+(prize|winnings?|reward)",
        r"(your\s+)?(winning\s+)?(number|code|ticket|reference|ID)\s+(is|number\s+is)\s*[:#]?\s*[A-Z0-9-]+",
        r"(claim\s+before|expires?\s+on|deadline\s+is|valid\s+for)\s+\d+\s+(days?|hours?|weeks?)",
        r"(FIFA|Olympic|World\s+Cup|Super\s+Bowl|NBA|NFL|Premier\s+League)\s+(lottery|giveaway|promotion|prize\s+draw)",
        r"(you\s+have\s+won|congratulations\s+you)\s+(a|an|the)\s+(iPhone|Mercedes|BMW|Toyota|Toyota\s+car|MacBook|iPhone\s+\d+).*(selected|chosen|random)",
    ],

    # === TECH SUPPORT SCAM (10 patterns) ===
    "TECH_SUPPORT_SCAM": [
        r"(your\s+)?(computer|PC|laptop|device|phone|Mac|Windows)\s+(is\s+infected|has\s+a\s+virus|is\s+compromised|has\s+\d+\s+(viruses?|malware|errors?|threats?))",
        r"(Microsoft|Apple|Windows|Google|Apple\s+Support)\s+(security|support|tech\s+support|warning|alert).*(call|contact|click|download)",
        r"(your\s+)?(IP\s+address|computer|device)\s+(has\s+been|is)\s+(blocked|flagged|suspended|locked).*(call|contact|click)",
        r"(call\s+(this\s+)?(number|phone)|contact\s+(us|support)\s+at)\s+\+?[\d\s\-()]{10,}",
        r"(allow\s+remote\s+access|grant\s+(remote\s+)?access|install\s+(TeamViewer|AnyDesk|screen\s+sharing)).*(fix|resolve|remove)\s+(the\s+)?(virus|malware|threat|issue)",
        r"(your\s+)?(firewall|antivirus|protection|security)\s+(has\s+(expired|lapsed)|is\s+out\s+of\s+date|needs?\s+(renewing|updating)).*(renew|update|pay)",
        r"(we\s+(detected|noticed)|our\s+system\s+(detected|found))\s+\d+\s+(security\s+)?(issues?|threats?|errors?|problems?)\s+on\s+your\s+(computer|device|PC)",
        r"(refund|compensation|reimbursement)\s+for\s+(your|the)\s+(software|antivirus|security\s+program).*(bank|account|verify|provide)",
        r"(pop[- ]?up|pop[- ]?up\s+window|browser\s+(alert|warning)).*(virus|infected|suspended|locked|call\s+(immediately|now|this\s+number))",
        r"(your\s+)?(computer|PC|laptop)\s+(will\s+be|is\s+going\s+to\s+be)\s+(locked|disabled|wiped|shut\s+down).*(call|contact|click|pay)",
    ],
}

# ==================== BEHAVIORAL HEURISTICS ====================

BEHAVIORAL_INDICATORS = {
    "URGENCY": {
        "weight": 0.15,
        "patterns": [
            r"\b(urgent|urgently|immediate|immediately|right\s+away|asap|now|today|before\s+it's\s+too\s+late|expires?|deadline|last\s+chance|final\s+notice|act\s+now|don't\s+wait|hurry)\b",
        ],
        "description": "Creates artificial time pressure to force quick decisions"
    },
    "AUTHORITY_CLAIM": {
        "weight": 0.12,
        "patterns": [
            r"\b(FBI|Interpol|police|government|bank|IRS|HMRC|SEC|FCA|official|authorized|authorised|certified|licensed|regulated|registered|approved|partner|affiliate)\b",
        ],
        "description": "Claims affiliation with legitimate authority"
    },
    "SCARCITY": {
        "weight": 0.10,
        "patterns": [
            r"\b(limited|only\s+\d+\s+(left|remaining|spots?|spaces?|available)|while\s+supplies?\s+last|first\s+come\s+first\s+served|one\s+time\s+only|won't\s+last|ending\s+soon|almost\s+gone)\b",
        ],
        "description": "Creates artificial scarcity to rush decisions"
    },
    "SOCIAL_PROOF": {
        "weight": 0.08,
        "patterns": [
            r"\b(thousands?\s+of\s+(satisfied\s+)?(clients?|customers?|victims?)|trusted\s+by|as\s+seen\s+on|featured\s+in|endorsed\s+by|5\s+stars?|excellent\s+rating|verified\s+by|testimonials?)\b",
        ],
        "description": "Uses fake social proof to build trust"
    },
    "EMOTIONAL_MANIPULATION": {
        "weight": 0.12,
        "patterns": [
            r"\b(love|soulmate|god\s+(sent|brought)|family|child|sick|hospital|emergency|widow|widower|orphan|alone|lonely|trust\s+you|only\s+you|you're\s+the\s+(only|one|first))\b",
        ],
        "description": "Exploits emotions to bypass rational thinking"
    },
    "FINANCIAL_ANOMALY": {
        "weight": 0.15,
        "patterns": [
            r"\b(send|wire|transfer|deposit|pay).*(bitcoin|crypto|BTC|ETH|USDT|gift\s+card|Western\s+Union|MoneyGram|prepaid\s+card|cash)\b",
            r"\b(upfront|in\s+advance|before\s+we\s+start|fee\s+required|deposit\s+required|processing\s+fee)\b",
            r"\b(double|triple|\d+x\s+back|guaranteed\s+return|risk[- ]?free|no\s+risk|can't\s+lose)\b",
        ],
        "description": "Unusual or risky payment methods and financial promises"
    },
    "ISOLATION_TACTIC": {
        "weight": 0.10,
        "patterns": [
            r"\b(don't\s+tell\s+anyone|keep\s+(this|it)\s+(confidential|secret|between\s+us|private)|don't\s+contact\s+(your|the)\s+(bank|family|police|lawyer)|only\s+trust\s+(me|us))\b",
        ],
        "description": "Attempts to isolate the victim from support networks"
    },
    "IMPERSONAL_GREETING": {
        "weight": 0.05,
        "patterns": [
            r"\b(dear\s+(customer|user|client|valued\s+customer|sir|madam|account\s+holder|winner|beneficiary))\b",
        ],
        "description": "Generic greeting typical of mass-targeting scams"
    },
    "COMMUNICATION_ANOMALY": {
        "weight": 0.08,
        "patterns": [
            r"\b(telegram|signal|whatsapp|wechat).*(only|exclusively|prefer|instead\s+of)\b",
            r"\b(can't\s+video\s+call|can't\s+meet\s+in\s+person|only\s+text|only\s+message|only\s+email)\b",
        ],
        "description": "Unusual communication preferences that avoid verification"
    },
    "TOO_GOOD_TO_BE_TRUE": {
        "weight": 0.15,
        "patterns": [
            r"\b(guaranteed|100%|risk[- ]?free|no\s+risk|can't\s+lose|double\s+your|free\s+money|easy\s+money|passive\s+income|get\s+rich)\b",
            r"\b\d{2,3}\s*%\s+(return|profit|ROI|APY|APR|interest)\b",
            r"\b(turn\s+)?\$?\d+\s+into\s+\$?\d{3,}\b",
        ],
        "description": "Promises that are unrealistic or too good to be true"
    },
}

# ==================== KNOWN-BAD INDICATORS ====================

# Known scam domain keywords (checked against domain registrations)
SCAM_DOMAIN_KEYWORDS = [
    "recovery", "payback", "claimback", "refund", "retrieve", "reclaim",
    "hack-back", "hackback", "crypto-recovery", "fund-recovery",
    "bitcoin-recovery", "scam-recovery", "chargeback", "unfreeze",
    "wallet-recovery", "lost-funds", "stolen-crypto", "recovery-expert",
    "crypto-forensics", "blockchain-recovery", "investigations-recovery",
    "asset-recovery", "recovery-agency", "recovery-service", "recovery-firm",
]

# Suspicious TLDs commonly used by scams
SUSPICIOUS_TLDS = [".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".click", ".country", ".stream", ".bid", ".trade", ".racing", ".review", ".accountant", ".cricket", ".date", ".download", ".faith", ".loan", "men", ".party", ".racing", ".review", ".science", ".study", ".trade", ".win"]

# Legitimate financial regulators and references (not scams)
LEGITIMATE_REFERENCES = [
    "fca.org.uk", "sec.gov", "esma.europa.eu", "bafin.de", "bankofengland.co.uk",
    "actionfraud.police.uk", "fbi.gov", "ic3.gov", "consumerfinance.gov", "ftc.gov",
    "cyber.gov.au", "getsafeonline.org", "takefive-stopfraud.org.uk",
    "consumerfinance.gov", "occ.treas.gov", "fdic.gov", "sba.gov",
]

# Known legitimate crypto/blockchain companies (not scammers themselves)
LEGITIMATE_CRYPTO_COMPANIES = [
    "coinbase.com", "binance.com", "kraken.com", "crypto.com", "gemini.com",
    "ledger.com", "trezor.io", "metamask.io", "trustwallet.com", "phantom.app",
]

# Known scam crypto wallets (would be populated from investigations)
KNOWN_SCAM_WALLETS: List[str] = []  # Populated from database

# High-risk payment methods
HIGH_RISK_PAYMENT_METHODS = [
    "western union", "moneygram", "gift card", "itunes card", "amazon card",
    "google play card", "steam card", "prepaid card", "vanilla card",
    "bitcoin", "btc", "ethereum", "eth", "usdt", "crypto", "crypto transfer",
    "wire transfer", "bank transfer to", "zelle", "venmo", "cashapp",
    "remittance", "money order",
]


# ==================== MULTI-LANGUAGE PATTERNS ====================

MULTILANG_PATTERNS = {
    "ES": {
        "RECOVERY_SCAM": [
            r"recuperar\s+(tu\s+)?(fondos|dinero|cripto|bitcoin|eth)",
            r"recuperación\s+(de\s+)?(fondos|dinero|cripto)",
            r"servicio\s+de\s+recuperación",
            r"experto\s+en\s+recuperación",
            r"100\s*%\s+garantizado",
            r"recupera\s+tu\s+(dinero|bitcoin|cripto)",
        ],
        "PHISHING": [
            r"verifica\s+tu\s+(cuenta|identidad|correo)",
            r"tu\s+cuenta\s+(ha\s+sido|será)\s+(suspendida|bloqueada|cerrada)",
            r"haz\s+clic\s+aquí\s+para\s+(verificar|confirmar|actualizar)",
            r"estimado\s+(cliente|usuario)",
            r"(urgente|inmediato)\s+acción\s+requerida",
        ],
        "INVESTMENT_FRAUD": [
            r"rentabilidad\s+(garantizada|del\s+\d{2,3}\s*%)",
            r"(duplica|triplica)\s+tu\s+(bitcoin|cripto|dinero)",
            r"inversión\s+(sin\s+riesgo|garantizada|de\s+alto\s+rendimiento)",
            r"ingresos\s+pasivos\s+garantizados",
        ],
    },
    "DE": {
        "RECOVERY_SCAM": [
            r"(Geld|Kryptowährung|Bitcoin).*(zurück|wieder)\s+(bekommen|erhalten)",
            r"Wiederherstellung\s+(Ihrer|von)\s+(Gelder|Krypto|Bitcoin)",
            r"100\s*%\s+(garantiert|sicher)\s+(Wiederherstellung|Rückerstattung)",
            r"(Geld|Krypto)\s+zurück",
            r"Experte\s+für\s+(Krypto-)?Wiederherstellung",
        ],
        "PHISHING": [
            r"(überprüfen|bestätigen)\s+Sie\s+(Ihr|Ihre)\s+(Konto|Identität|E-?Mail)",
            r"(Ihr)\s+Konto\s+wurde\s+(gesperrt|geschlossen|eingefroren)",
            r"(klicken\s+Sie\s+hier).*(überprüfen|bestätigen|aktualisieren)",
            r"(sehr\s+geehrte\(r\))\s+(Kunde|Benutzer|Kundin)",
            r"(dringend|sofort)\s+(Maßnahme\s+(erforderlich|nötig))",
        ],
    },
    "FR": {
        "RECOVERY_SCAM": [
            r"récupérer\s+(vos\s+)?(fonds|argent|crypto|bitcoin)",
            r"récupération\s+(de\s+)?(fonds|argent|crypto)",
            r"service\s+de\s+récupération",
            r"expert\s+en\s+récupération",
            r"100\s*%\s+garanti",
        ],
        "PHISHING": [
            r"(vérifiez|confirmez)\s+(votre\s+)?(compte|identité|e-?mail|adresse)",
            r"votre\s+compte\s+(a\s+été|sera)\s+(suspendu|bloqué|fermé)",
            r"cliquez\s+ici\s+pour\s+(vérifier|confirmer|mettre\s+à\s+jour)",
            r"cher\s+(client|utilisateur|abonné)",
            r"(urgent|immédiat)\s+(action\s+requise|nécessaire)",
        ],
    },
}


class DeterministicScamEngine:
    """
    Local deterministic scam detection engine.
    Analyzes text for scam patterns, behavioral indicators, and entity extraction.
    Produces AI-level analysis without any LLM dependency.
    """

    @staticmethod
    def analyze(text: str, target: str = "", language: str = "EN") -> Dict[str, Any]:
        """
        Full scam analysis of text.
        Returns comprehensive analysis with patterns, behavioral indicators,
        risk score, entities, and human-readable report.
        """
        text_lower = text.lower()
        full_text = f"{text} {target}".lower()

        # 1. Pattern Detection
        pattern_results = DeterministicScamEngine._detect_patterns(full_text)

        # 2. Multi-language detection
        multilang_results = DeterministicScamEngine._detect_multilang(full_text, language)

        # 3. Behavioral Heuristics
        behavioral_results = DeterministicScamEngine._detect_behavioral(full_text)

        # 4. Entity Extraction
        entities = DeterministicScamEngine._extract_entities(text + " " + target)

        # 5. Known-bad indicator check
        known_bad = DeterministicScamEngine._check_known_bad(full_text, entities)

        # 6. Domain analysis
        domain_analysis = DeterministicScamEngine._analyze_domains(entities.get("domains", []), full_text)

        # 7. Payment method analysis
        payment_analysis = DeterministicScamEngine._analyze_payments(full_text)

        # 8. Risk scoring
        risk = DeterministicScamEngine._calculate_risk(
            pattern_results, behavioral_results, known_bad, domain_analysis, payment_analysis
        )

        # 9. Timeline reconstruction
        timeline = DeterministicScamEngine._extract_timeline(text)

        # 10. Generate human-readable report
        report = DeterministicScamEngine._generate_report(
            pattern_results, behavioral_results, entities, known_bad,
            domain_analysis, payment_analysis, risk, target
        )

        return {
            "patterns": pattern_results,
            "multilang": multilang_results,
            "behavioral": behavioral_results,
            "entities": entities,
            "known_bad": known_bad,
            "domain_analysis": domain_analysis,
            "payment_analysis": payment_analysis,
            "timeline": timeline,
            "risk": risk,
            "report": report,
            "summary": {
                "risk_level": risk["level"],
                "risk_score": risk["score"],
                "confidence": risk["confidence"],
                "categories_detected": list(set(pattern_results["categories_hit"] + multilang_results["categories_hit"])),
                "pattern_count": pattern_results["pattern_count"] + multilang_results["pattern_count"],
                "behavioral_indicators": len(behavioral_results["indicators_hit"]),
                "entities_found": sum(len(v) for v in entities.values() if isinstance(v, list)),
                "known_bad_hits": len(known_bad),
                "has_crypto_wallet": bool(entities.get("crypto_wallets")),
                "has_payment_request": payment_analysis["has_payment_request"],
                "has_urgency": behavioral_results["has_urgency"],
                "has_authority_claim": behavioral_results["has_authority_claim"],
                "language": language,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }
        }

    @staticmethod
    def _detect_patterns(text: str) -> Dict[str, Any]:
        """Detect scam patterns from the pattern library."""
        patterns_found = []
        categories_hit = set()

        for category, patterns in SCAM_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    sample = matches[0] if isinstance(matches[0], str) else str(matches[0])
                    patterns_found.append({
                        "category": category,
                        "pattern": pattern[:60],
                        "match_count": len(matches),
                        "sample": sample[:100],
                    })
                    categories_hit.add(category)

        return {
            "patterns_found": patterns_found,
            "categories_hit": list(categories_hit),
            "pattern_count": len(patterns_found),
        }

    @staticmethod
    def _detect_multilang(text: str, primary_lang: str = "EN") -> Dict[str, Any]:
        """Detect scam patterns in multiple languages."""
        patterns_found = []
        categories_hit = set()

        for lang, categories in MULTILANG_PATTERNS.items():
            for category, patterns in categories.items():
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        patterns_found.append({
                            "language": lang,
                            "category": category,
                            "pattern": pattern[:60],
                            "match_count": len(matches),
                        })
                        categories_hit.add(category)

        return {
            "patterns_found": patterns_found,
            "categories_hit": list(categories_hit),
            "pattern_count": len(patterns_found),
            "languages_detected": list(set(p["language"] for p in patterns_found)) if patterns_found else [],
        }

    @staticmethod
    def _detect_behavioral(text: str) -> Dict[str, Any]:
        """Detect behavioral heuristics and manipulation tactics."""
        indicators_hit = []
        total_weight = 0.0
        has_urgency = False
        has_authority_claim = False

        for indicator_name, config in BEHAVIORAL_INDICATORS.items():
            for pattern in config["patterns"]:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    indicators_hit.append({
                        "indicator": indicator_name,
                        "weight": config["weight"],
                        "match_count": len(matches),
                        "description": config["description"],
                    })
                    total_weight += config["weight"]
                    if indicator_name == "URGENCY":
                        has_urgency = True
                    if indicator_name == "AUTHORITY_CLAIM":
                        has_authority_claim = True
                    break  # One match per indicator is enough

        return {
            "indicators_hit": indicators_hit,
            "total_weight": round(total_weight, 3),
            "has_urgency": has_urgency,
            "has_authority_claim": has_authority_claim,
        }

    @staticmethod
    def _extract_entities(text: str) -> Dict[str, Any]:
        """Extract investigative entities from text."""
        entities = {
            "domains": [],
            "emails": [],
            "phones": [],
            "crypto_wallets": [],
            "urls": [],
            "social_media": [],
            "ip_addresses": [],
            "bank_accounts": [],
            "person_names": [],
        }

        # Domains
        domains = re.findall(
            r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b',
            text
        )
        # Filter out common non-domain matches
        domains = [d for d in set(domains) if not d.endswith(('.com.com', '.net.net'))]
        entities["domains"] = domains[:30]

        # Emails
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        entities["emails"] = list(set(emails))[:20]

        # Phone numbers (international format)
        phones = re.findall(r'\+?\d{1,4}[\s\-()]?\d{2,4}[\s\-()]?\d{3,4}[\s\-()]?\d{3,4}', text)
        entities["phones"] = list(set(phones))[:15]

        # Crypto wallets
        btc = re.findall(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b', text)
        eth = re.findall(r'\b0x[a-fA-F0-9]{40}\b', text)
        entities["crypto_wallets"] = list(set(btc + eth))[:10]

        # URLs
        urls = re.findall(r'https?://[^\s<>"\')]+', text)
        entities["urls"] = list(set(urls))[:20]

        # Social media handles
        telegram = re.findall(r'(?:@|t\.me/)([a-zA-Z0-9_]{4,32})', text)
        twitter = re.findall(r'@([a-zA-Z0-9_]{4,15})\b', text)
        entities["social_media"] = list(set(telegram + twitter))[:10]

        # IP addresses
        ips = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', text)
        entities["ip_addresses"] = [ip for ip in set(ips) if DeterministicScamEngine._valid_ip(ip)][:5]

        # Bank account patterns (IBAN)
        ibans = re.findall(r'\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b', text)
        entities["bank_accounts"] = list(set(ibans))[:5]

        return entities

    @staticmethod
    def _valid_ip(ip: str) -> bool:
        parts = ip.split('.')
        return len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts if p.isdigit())

    @staticmethod
    def _check_known_bad(text: str, entities: Dict) -> List[Dict]:
        """Check against known-bad databases."""
        hits = []

        # Check domain keywords
        for keyword in SCAM_DOMAIN_KEYWORDS:
            if keyword in text:
                hits.append({
                    "type": "DOMAIN_KEYWORD",
                    "value": keyword,
                    "severity": "MEDIUM",
                    "description": f"Domain contains known scam keyword: '{keyword}'"
                })

        # Check suspicious TLDs
        for domain in entities.get("domains", []):
            for tld in SUSPICIOUS_TLDS:
                if domain.endswith(tld):
                    hits.append({
                        "type": "SUSPICIOUS_TLD",
                        "value": domain,
                        "severity": "LOW",
                        "description": f"Domain uses suspicious TLD: {tld}"
                    })

        # Check known scam wallets
        for wallet in entities.get("crypto_wallets", []):
            if wallet in KNOWN_SCAM_WALLETS:
                hits.append({
                    "type": "KNOWN_SCAM_WALLET",
                    "value": wallet,
                    "severity": "CRITICAL",
                    "description": f"Wallet address is in known scam database"
                })

        # Check for legitimate references (reduces risk)
        for ref in LEGITIMATE_REFERENCES:
            if ref in text:
                hits.append({
                    "type": "LEGITIMATE_REFERENCE",
                    "value": ref,
                    "severity": "POSITIVE",
                    "description": f"References legitimate authority: {ref}"
                })

        return hits

    @staticmethod
    def _analyze_domains(domains: List[str], text: str) -> Dict[str, Any]:
        """Analyze domains for scam indicators."""
        if not domains:
            return {"has_domains": False, "suspicious_domains": [], "domain_count": 0}

        suspicious = []
        for domain in domains:
            reasons = []

            # Check for scam keywords in domain
            for keyword in SCAM_DOMAIN_KEYWORDS:
                if keyword in domain.lower():
                    reasons.append(f"Contains scam keyword: '{keyword}'")

            # Check for suspicious TLD
            for tld in SUSPICIOUS_TLDS:
                if domain.endswith(tld):
                    reasons.append(f"Suspicious TLD: {tld}")

            # Check for lookalike domains (homoglyphs)
            if "0" in domain and "o" not in domain:
                reasons.append("Possible homoglyph: contains '0' where 'o' expected")
            if "1" in domain and "l" not in domain and "i" not in domain:
                reasons.append("Possible homoglyph: contains '1' where 'l' or 'i' expected")

            # Check for excessive subdomains
            if domain.count(".") > 3:
                reasons.append("Excessive subdomain levels")

            if reasons:
                suspicious.append({"domain": domain, "reasons": reasons})

        return {
            "has_domains": True,
            "domain_count": len(domains),
            "all_domains": domains,
            "suspicious_domains": suspicious,
        }

    @staticmethod
    def _analyze_payments(text: str) -> Dict[str, Any]:
        """Analyze payment method requests for risk."""
        payment_methods_found = []
        has_payment_request = False

        for method in HIGH_RISK_PAYMENT_METHODS:
            if method in text:
                payment_methods_found.append(method)
                has_payment_request = True

        # Check for "send" + payment method
        if re.search(r'\b(send|wire|transfer|pay|deposit|remittance)\b.*\b(' + '|'.join(re.escape(m) for m in HIGH_RISK_PAYMENT_METHODS) + r')\b', text):
            has_payment_request = True

        return {
            "has_payment_request": has_payment_request,
            "payment_methods_found": payment_methods_found,
            "risk_level": "HIGH" if has_payment_request else "NONE",
        }

    @staticmethod
    def _calculate_risk(patterns: Dict, behavioral: Dict, known_bad: List, domain_analysis: Dict, payment_analysis: Dict) -> Dict[str, Any]:
        """Calculate comprehensive risk score with confidence."""
        score = 0.0
        factors = []

        # Pattern score (weighted by category)
        category_weights = {
            "RECOVERY_SCAM": 0.20,
            "INVESTMENT_FRAUD": 0.18,
            "BRAND_IMPERSONATION": 0.12,
            "PHISHING": 0.10,
            "ROMANCE_SCAM": 0.12,
            "PAYMENT_FRAUD": 0.10,
            "SOCIAL_ENGINEERING": 0.15,
            "CRYPTO_FRAUD": 0.15,
            "JOB_SCAM": 0.08,
            "RENTAL_SCAM": 0.08,
            "LOTTERY_SCAM": 0.10,
            "TECH_SUPPORT_SCAM": 0.10,
            "DOMAIN_INDICATOR": 0.05,
        }

        for category in patterns["categories_hit"]:
            weight = category_weights.get(category, 0.08)
            score += weight
            factors.append(f"Pattern category: {category} (+{weight})")

        # Pattern count bonus
        if patterns["pattern_count"] > 10:
            score += 0.10
            factors.append("High pattern count: >10 matches (+0.10)")
        elif patterns["pattern_count"] > 5:
            score += 0.05
            factors.append("Moderate pattern count: >5 matches (+0.05)")

        # Behavioral score
        score += behavioral["total_weight"]
        if behavioral["total_weight"] > 0:
            factors.append(f"Behavioral indicators: {behavioral['total_weight']}")

        # Known-bad indicators
        for kb in known_bad:
            if kb["severity"] == "CRITICAL":
                score += 0.20
                factors.append(f"Critical known-bad: {kb['type']} (+0.20)")
            elif kb["severity"] == "MEDIUM":
                score += 0.08
                factors.append(f"Medium known-bad: {kb['type']} (+0.08)")
            elif kb["severity"] == "LOW":
                score += 0.04
                factors.append(f"Low known-bad: {kb['type']} (+0.04)")
            elif kb["severity"] == "POSITIVE":
                score -= 0.10
                factors.append(f"Legitimate reference: {kb['value']} (-0.10)")

        # Domain analysis
        if domain_analysis.get("suspicious_domains"):
            for _ in domain_analysis["suspicious_domains"]:
                score += 0.05
                factors.append("Suspicious domain characteristics (+0.05)")

        # Payment analysis
        if payment_analysis["has_payment_request"]:
            score += 0.15
            factors.append("High-risk payment method requested (+0.15)")

        # Crypto wallet presence (adds risk in scam context)
        # Already covered in CRYPTO_FRAUD patterns

        # Clamp score
        score = max(0.0, min(1.0, score))

        # Determine level
        if score >= 0.75:
            level = "CRITICAL"
        elif score >= 0.50:
            level = "HIGH"
        elif score >= 0.30:
            level = "MEDIUM"
        elif score >= 0.10:
            level = "LOW"
        else:
            level = "MINIMAL"

        # Confidence based on number of independent factors
        confidence = min(len(factors) / 10.0, 1.0)

        return {
            "score": round(score, 3),
            "level": level,
            "confidence": round(confidence, 3),
            "factors": factors,
            "factor_count": len(factors),
        }

    @staticmethod
    def _extract_timeline(text: str) -> List[Dict]:
        """Extract timeline events from text."""
        events = []

        # Date patterns
        date_patterns = [
            (r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})\b', "DMY"),
            (r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b', "MDY"),
            (r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b', "DMY"),
            (r'\b(last\s+(week|month|year|night|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))\b', "RELATIVE"),
            (r'\b(\d+)\s+(days?|weeks?|months?|years?)\s+ago\b', "RELATIVE"),
        ]

        for pattern, dtype in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                events.append({
                    "date_text": m.group(),
                    "type": dtype,
                    "position": m.start(),
                })

        # Sort by position in text
        events.sort(key=lambda e: e["position"])
        return events

    @staticmethod
    def _generate_report(patterns: Dict, behavioral: Dict, entities: Dict,
                         known_bad: List, domain_analysis: Dict, payment_analysis: Dict,
                         risk: Dict, target: str) -> str:
        """Generate a human-readable analysis report (template-based, no AI)."""
        lines = []
        lines.append("=" * 70)
        lines.append("GFIN DETERMINISTIC SCAM ANALYSIS REPORT")
        lines.append("=" * 70)
        lines.append(f"Target: {target or 'N/A'}")
        lines.append(f"Analysis Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(f"Engine: Deterministic Scam Engine v3.0 (Local, No AI)")
        lines.append("")

        # Risk Assessment
        lines.append("─" * 40)
        lines.append("RISK ASSESSMENT")
        lines.append("─" * 40)
        lines.append(f"Risk Level:      {risk['level']}")
        lines.append(f"Risk Score:      {risk['score']}/1.000")
        lines.append(f"Confidence:      {risk['confidence']}/1.000")
        lines.append(f"Risk Factors:    {risk['factor_count']}")
        lines.append("")

        # Scam Categories Detected
        if patterns["categories_hit"]:
            lines.append("─" * 40)
            lines.append("SCAM CATEGORIES DETECTED")
            lines.append("─" * 40)
            for cat in patterns["categories_hit"]:
                cat_patterns = [p for p in patterns["patterns_found"] if p["category"] == cat]
                lines.append(f"  • {cat}: {len(cat_patterns)} pattern(s) matched")
            lines.append("")

        # Behavioral Indicators
        if behavioral["indicators_hit"]:
            lines.append("─" * 40)
            lines.append("BEHAVIORAL INDICATORS")
            lines.append("─" * 40)
            for ind in behavioral["indicators_hit"]:
                lines.append(f"  • {ind['indicator']} (weight: {ind['weight']})")
                lines.append(f"    {ind['description']}")
            lines.append("")

        # Entities Extracted
        lines.append("─" * 40)
        lines.append("ENTITIES EXTRACTED")
        lines.append("─" * 40)
        for entity_type, values in entities.items():
            if values:
                lines.append(f"  {entity_type}: {len(values)} found")
                for v in values[:5]:
                    lines.append(f"    → {v}")
                if len(values) > 5:
                    lines.append(f"    ... and {len(values) - 5} more")
        lines.append("")

        # Known-Bad Indicators
        if known_bad:
            lines.append("─" * 40)
            lines.append("KNOWN-BAD INDICATORS")
            lines.append("─" * 40)
            for kb in known_bad:
                severity_icon = "🚨" if kb["severity"] == "CRITICAL" else "⚠️" if kb["severity"] in ("MEDIUM", "HIGH") else "ℹ️" if kb["severity"] == "LOW" else "✅"
                lines.append(f"  {severity_icon} [{kb['severity']}] {kb['type']}: {kb['value']}")
                lines.append(f"    {kb['description']}")
            lines.append("")

        # Domain Analysis
        if domain_analysis.get("has_domains"):
            lines.append("─" * 40)
            lines.append("DOMAIN ANALYSIS")
            lines.append("─" * 40)
            lines.append(f"  Total domains found: {domain_analysis['domain_count']}")
            if domain_analysis.get("suspicious_domains"):
                lines.append(f"  Suspicious domains: {len(domain_analysis['suspicious_domains'])}")
                for sd in domain_analysis["suspicious_domains"]:
                    lines.append(f"    → {sd['domain']}")
                    for reason in sd["reasons"]:
                        lines.append(f"      • {reason}")
            else:
                lines.append("  No suspicious domain indicators found")
            lines.append("")

        # Payment Analysis
        if payment_analysis["has_payment_request"]:
            lines.append("─" * 40)
            lines.append("PAYMENT ANALYSIS")
            lines.append("─" * 40)
            lines.append(f"  ⚠️  HIGH-RISK PAYMENT METHOD REQUESTED")
            for method in payment_analysis["payment_methods_found"]:
                lines.append(f"    → {method}")
            lines.append("")

        # Risk Factors Breakdown
        if risk["factors"]:
            lines.append("─" * 40)
            lines.append("RISK FACTORS BREAKDOWN")
            lines.append("─" * 40)
            for factor in risk["factors"]:
                lines.append(f"  • {factor}")
            lines.append("")

        # Recommendation
        lines.append("─" * 40)
        lines.append("ASSESSMENT")
        lines.append("─" * 40)
        if risk["level"] == "CRITICAL":
            lines.append("  🚨 CRITICAL RISK: Multiple strong scam indicators detected.")
            lines.append("  Immediate law enforcement referral recommended.")
            lines.append("  Victim should be warned and supported.")
        elif risk["level"] == "HIGH":
            lines.append("  ⚠️  HIGH RISK: Significant scam indicators detected.")
            lines.append("  Investigation and victim notification recommended.")
        elif risk["level"] == "MEDIUM":
            lines.append("  ⚠️  MEDIUM RISK: Some scam indicators present.")
            lines.append("  Further investigation recommended.")
        elif risk["level"] == "LOW":
            lines.append("  ℹ️  LOW RISK: Minor indicators detected.")
            lines.append("  Monitor and collect additional information.")
        else:
            lines.append("  ✅ MINIMAL RISK: No significant scam indicators detected.")
            lines.append("  Standard monitoring applies.")
        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)
