"""
GFIN Database Configuration
Reads ALL credentials from environment variables ONLY.
No hardcoded passwords in source code.
"""
import os

def get_db_config():
    """Get database configuration from environment. No defaults for secrets."""
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "6432")),
        "dbname": os.getenv("DB_NAME", "gfin"),
        "user": os.getenv("DB_USER", "gfin"),
        "password": os.getenv("DB_PASSWORD")  # NO DEFAULT — must come from .env
    }

def get_db_url():
    """Get SQLAlchemy-style connection URL."""
    c = get_db_config()
    return f"postgresql://{c['user']}:{c['password']}@{c['host']}:{c['port']}/{c['dbname']}"
