import psycopg2
conn = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!", port=5432)
cur = conn.cursor()
for t in ["telegram_intelligence", "telegram_groups", "telegram_wallets", "telegram_domains"]:
    cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    print(f"Dropped {t}")
conn.commit()

# Create with correct schema
cur.execute("""
    CREATE TABLE telegram_intelligence (
        id SERIAL PRIMARY KEY,
        message_id BIGINT,
        group_id BIGINT,
        group_name TEXT,
        sender_id BIGINT,
        sender_name TEXT,
        sender_username TEXT,
        message_text TEXT,
        wallets JSONB DEFAULT '[]',
        domains JSONB DEFAULT '[]',
        phones JSONB DEFAULT '[]',
        ips JSONB DEFAULT '[]',
        usernames JSONB DEFAULT '[]',
        is_victim BOOLEAN DEFAULT FALSE,
        victim_patterns JSONB DEFAULT '[]',
        scam_type TEXT,
        scam_indicators JSONB DEFAULT '[]',
        risk_level TEXT DEFAULT 'LOW',
        processed BOOLEAN DEFAULT FALSE,
        investigated BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW()
    )
""")
cur.execute("""
    CREATE TABLE telegram_groups (
        id SERIAL PRIMARY KEY,
        group_id BIGINT UNIQUE,
        group_name TEXT,
        group_username TEXT,
        member_count INTEGER DEFAULT 0,
        is_monitored BOOLEAN DEFAULT TRUE,
        first_seen TIMESTAMP DEFAULT NOW(),
        last_activity TIMESTAMP
    )
""")
cur.execute("""
    CREATE TABLE telegram_wallets (
        id SERIAL PRIMARY KEY,
        wallet_address TEXT UNIQUE,
        wallet_type TEXT,
        first_seen_group TEXT,
        first_seen_sender TEXT,
        mention_count INTEGER DEFAULT 1,
        last_seen TIMESTAMP DEFAULT NOW(),
        investigated BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW()
    )
""")
cur.execute("""
    CREATE TABLE telegram_domains (
        id SERIAL PRIMARY KEY,
        domain TEXT UNIQUE,
        first_seen_group TEXT,
        first_seen_sender TEXT,
        mention_count INTEGER DEFAULT 1,
        investigated BOOLEAN DEFAULT FALSE,
        scam_detected BOOLEAN DEFAULT FALSE,
        risk_level TEXT DEFAULT 'UNKNOWN',
        created_at TIMESTAMP DEFAULT NOW(),
        last_seen TIMESTAMP DEFAULT NOW()
    )
""")
conn.commit()
conn.close()
print("Tables created successfully")
