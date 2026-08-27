"""GFIN Database Migration Runner.

Per Luna Assessment P0: "Migration framework, repository implementations."
Runs database migrations against the configured PostgreSQL instance.

Usage:
    python -m packages.common.run_migrations

Environment:
    DATABASE_URL — PostgreSQL connection string (required)
"""

from __future__ import annotations

import asyncio
import os
import sys

import structlog

logger = structlog.get_logger("gfin.migrations")


async def run_migrations() -> int:
    """Run database migrations."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return 1

    from common.postgres_repository import MigrationManager

    manager = MigrationManager.from_url(database_url)

    try:
        await manager.create_all()

        applied = await manager.get_applied_migrations()
        for _m in applied:
            pass

        return 0
    except Exception as e:
        logger.error("migration_failed", error=str(e))
        return 1
    finally:
        await manager.close()


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    exit_code = asyncio.run(run_migrations())
    sys.exit(exit_code)
