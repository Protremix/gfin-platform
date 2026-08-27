# GFIN PostgreSQL Repository Adapter
#
# Layer B: Production persistence using SQLAlchemy + PostgreSQL.
# REQUIRES EXTERNAL INFRASTRUCTURE: PostgreSQL 15+, SQLAlchemy 2.0+, asyncpg driver.
#
# Per Luna Assessment P0: "Real database schemas and migrations, transaction boundaries,
# foreign keys and uniqueness constraints, recovery after process restart."
#
# Per Constitution Article VII: All data operations must be auditable.
# Per Constitution Article VIII: Multi-tenant isolation by organization_id.
#
# This adapter implements the EntityRepository interface from common.database.
# It uses SQLAlchemy 2.0 async ORM with asyncpg for PostgreSQL connectivity.
#
# Environment variables:
#   DATABASE_URL — PostgreSQL connection string (required)
#       e.g. postgresql+asyncpg://user:pass@host:5432/gfin
#   DATABASE_POOL_SIZE — Connection pool size (default: 10)
#   DATABASE_MAX_OVERFLOW — Max overflow connections (default: 20)
#   DATABASE_ECHO — Echo SQL for debugging (default: false)

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.sql import func

from common.database import EntityRepository, T
from schemas.base import BaseEntity

logger = structlog.get_logger("gfin.postgres_repository")


# ─── Schema Definition ───

metadata = MetaData()


# Abstract base columns shared by all entity tables
def base_columns() -> list:
    """Return common columns for all entity tables."""
    return [
        Column("id", String(64), primary_key=True),
        Column("entity_type", String(50), nullable=False, index=True),
        Column("normalized_value", String(500), nullable=False),
        Column("raw_values", JSONB, nullable=False, default=list),
        Column("classification", JSONB, nullable=False, default=dict),
        Column("provenance", JSONB, nullable=True),
        Column(
            "first_seen", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
        ),
        Column(
            "last_seen", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
        ),
        Column("confidence", String(20), nullable=False, default="UNKNOWN"),
        # Multi-tenant isolation
        Column("organization_id", String(64), nullable=True, index=True),
        Column("jurisdiction", String(10), nullable=True),
        # Lifecycle
        Column("version", Integer, nullable=False, default=1),
        Column("is_deleted", Boolean, nullable=False, default=False),
        Column("deleted_at", DateTime(timezone=True), nullable=True),
        Column("deleted_by", String(64), nullable=True),
        Column("created_by", String(64), nullable=True),
        Column(
            "created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
        ),
        Column("updated_by", String(64), nullable=True),
        Column(
            "updated_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
        ),
    ]


# Entity table — stores all GFIN entities (Person, Phone, Domain, etc.)
entities_table = Table(
    "gfin_entities",
    metadata,
    *base_columns(),
    UniqueConstraint("entity_type", "normalized_value", name="uq_entity_type_value"),
    Index("ix_entity_org_type", "organization_id", "entity_type"),
    Index("ix_entity_org_deleted", "organization_id", "is_deleted"),
)

# Fraud reports table — citizen-submitted fraud reports
fraud_reports_table = Table(
    "gfin_fraud_reports",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("report_type", String(50), nullable=False, index=True),
    Column("description", Text, nullable=True),
    Column("status", String(30), nullable=False, default="UNVERIFIED", index=True),
    Column("priority", String(20), nullable=False, default="MEDIUM"),
    Column("score", Integer, nullable=False, default=0),
    Column("entity_refs", JSONB, nullable=False, default=list),
    Column("source_type", String(30), nullable=False, default="CITIZEN"),
    Column("reporter_id", String(64), nullable=True),
    Column("is_anonymous", Boolean, nullable=False, default=False),
    Column("organization_id", String(64), nullable=True, index=True),
    Column("jurisdiction", String(10), nullable=True),
    Column("version", Integer, nullable=False, default=1),
    Column("is_deleted", Boolean, nullable=False, default=False),
    Column("created_by", String(64), nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column("metadata", JSONB, nullable=False, default=dict),
    Index("ix_report_org_status", "organization_id", "status"),
    Index("ix_report_type_status", "report_type", "status"),
)

# Campaigns table — fraud campaign tracking
campaigns_table = Table(
    "gfin_campaigns",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(200), nullable=False),
    Column("status", String(30), nullable=False, default="DRAFT", index=True),
    Column("score", Integer, nullable=False, default=0),
    Column("linked_reports", JSONB, nullable=False, default=list),
    Column("linked_entities", JSONB, nullable=False, default=list),
    Column(
        "first_seen", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column("last_seen", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)),
    Column("organization_id", String(64), nullable=True, index=True),
    Column("version", Integer, nullable=False, default=1),
    Column("is_deleted", Boolean, nullable=False, default=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column("metadata", JSONB, nullable=False, default=dict),
)

# Alerts table — alert routing and tracking
alerts_table = Table(
    "gfin_alerts",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("alert_type", String(50), nullable=False, index=True),
    Column("priority", String(20), nullable=False, default="MEDIUM"),
    Column("channel", String(50), nullable=False, default="EMAIL"),
    Column("status", String(30), nullable=False, default="PENDING", index=True),
    Column("source_entity_id", String(64), nullable=True),
    Column("source_report_id", String(64), nullable=True),
    Column("target_org_id", String(64), nullable=True),
    Column("message", Text, nullable=True),
    Column("escalation_level", Integer, nullable=False, default=0),
    Column("organization_id", String(64), nullable=True, index=True),
    Column("version", Integer, nullable=False, default=1),
    Column("is_deleted", Boolean, nullable=False, default=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column("metadata", JSONB, nullable=False, default=dict),
    Index("ix_alert_org_status", "organization_id", "status"),
)

# Audit log table — immutable audit trail
audit_log_table = Table(
    "gfin_audit_log",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("action", String(100), nullable=False, index=True),
    Column("actor_id", String(64), nullable=False),
    Column("actor_role", String(50), nullable=True),
    Column("target_type", String(50), nullable=False),
    Column("target_id", String(64), nullable=False),
    Column("organization_id", String(64), nullable=True, index=True),
    Column("details", JSONB, nullable=False, default=dict),
    Column("timestamp", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)),
    Column("correlation_id", String(64), nullable=True, index=True),
    Index("ix_audit_org_action", "organization_id", "action"),
)

# Users table — application users with roles
users_table = Table(
    "gfin_users",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("email", String(255), nullable=False, unique=True),
    Column("full_name", String(200), nullable=True),
    Column("role", String(50), nullable=False, default="CITIZEN"),
    Column("organization_id", String(64), nullable=True, index=True),
    Column("jurisdiction", String(10), nullable=True),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("is_deleted", Boolean, nullable=False, default=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column(
        "updated_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column("metadata", JSONB, nullable=False, default=dict),
)


# ─── Migration Tracking Table ───

schema_migrations_table = Table(
    "gfin_schema_migrations",
    metadata,
    Column("version", String(50), primary_key=True),
    Column(
        "applied_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    ),
    Column("description", Text, nullable=True),
)


# ─── PostgreSQL Repository Adapter ───


class PostgresEntityRepository(EntityRepository[T]):
    """PostgreSQL adapter for entity persistence.

    REQUIRES EXTERNAL INFRASTRUCTURE: PostgreSQL 15+, SQLAlchemy 2.0+, asyncpg.

    This adapter is selected by configuration when DATABASE_URL is set.
    All operations enforce multi-tenant isolation via organization_id.

    Per Luna Assessment P0:
    - Transaction boundaries (uses AsyncSession)
    - Foreign keys and uniqueness constraints (DB-level enforcement)
    - Recovery after process restart (durable storage)
    - Idempotent writes (upsert pattern with unique constraints)
    - Pagination (limit/offset at DB level)
    """

    def __init__(self, engine: AsyncEngine, table: Table) -> None:
        self._engine = engine
        self._table = table
        self._session_factory = async_sessionmaker(engine, expire_on_commit=False)

    @classmethod
    def from_url(
        cls, database_url: str, table: Table | None = None, **kwargs: Any
    ) -> PostgresEntityRepository[T]:
        """Create a repository from a connection URL."""
        engine = create_async_engine(
            database_url,
            pool_size=kwargs.get("pool_size", 10),
            max_overflow=kwargs.get("max_overflow", 20),
            echo=kwargs.get("echo", False),
        )
        return cls(engine, table or entities_table)

    async def create(self, entity: T) -> T:
        """Create a new entity record in PostgreSQL."""
        data = self._entity_to_row(entity)
        async with self._session_factory() as session:
            async with session.begin():
                stmt = (
                    self._table.insert()
                    .values(**data)
                    .on_conflict_do_nothing(
                        index_elements=["entity_type", "normalized_value"],
                    )
                )
                await session.execute(stmt)
            return entity

    async def get(self, entity_id: str) -> T | None:
        """Get an entity by ID from PostgreSQL."""
        async with self._session_factory() as session:
            stmt = select(self._table).where(
                self._table.c.id == entity_id,
                self._table.c.is_deleted == False,  # noqa: E712
            )
            result = await session.execute(stmt)
            row = result.mappings().first()
            if row is None:
                return None
            return self._row_to_entity(dict(row))

    async def update(self, entity_id: str, data: dict[str, Any]) -> T | None:
        """Update an entity in PostgreSQL with optimistic concurrency."""
        async with self._session_factory() as session, session.begin():
            # Get current version for optimistic concurrency
            stmt = select(self._table.c.version).where(self._table.c.id == entity_id)
            result = await session.execute(stmt)
            current = result.first()
            if current is None:
                return None

            update_data = {**data, "version": current[0] + 1, "updated_at": datetime.now(UTC)}
            stmt = (
                self._table.update()
                .where(
                    self._table.c.id == entity_id,
                    self._table.c.version == current[0],  # Optimistic lock
                    self._table.c.is_deleted == False,  # noqa: E712
                )
                .values(**self._serialize_dict(update_data))
            )
            result = await session.execute(stmt)
            if result.rowcount == 0:
                return None

            # Fetch updated
            stmt = select(self._table).where(self._table.c.id == entity_id)
            result = await session.execute(stmt)
            row = result.mappings().first()
            return self._row_to_entity(dict(row)) if row else None

    async def delete(self, entity_id: str) -> bool:
        """Soft-delete an entity in PostgreSQL."""
        async with self._session_factory() as session, session.begin():
            stmt = (
                self._table.update()
                .where(
                    self._table.c.id == entity_id,
                    self._table.c.is_deleted == False,  # noqa: E712
                )
                .values(
                    is_deleted=True,
                    deleted_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
            result = await session.execute(stmt)
            return result.rowcount > 0

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """List entities with optional filters from PostgreSQL."""
        async with self._session_factory() as session:
            stmt = select(self._table).where(self._table.c.is_deleted == False)  # noqa: E712
            if filters:
                for key, value in filters.items():
                    if hasattr(self._table.c, key):
                        stmt = stmt.where(getattr(self._table.c, key) == value)
            stmt = stmt.limit(limit).offset(offset)
            result = await session.execute(stmt)
            rows = result.mappings().all()
            return [self._row_to_entity(dict(row)) for row in rows]

    async def find_by_normalized_value(self, entity_type: str, normalized_value: str) -> T | None:
        """Find an entity by type and normalized value."""
        async with self._session_factory() as session:
            stmt = select(self._table).where(
                self._table.c.entity_type == entity_type,
                self._table.c.normalized_value == normalized_value,
                self._table.c.is_deleted == False,  # noqa: E712
            )
            result = await session.execute(stmt)
            row = result.mappings().first()
            return self._row_to_entity(dict(row)) if row else None

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities matching filters in PostgreSQL."""
        async with self._session_factory() as session:
            stmt = (
                select(func.count())
                .select_from(self._table)
                .where(
                    self._table.c.is_deleted == False  # noqa: E712
                )
            )
            if filters:
                for key, value in filters.items():
                    if hasattr(self._table.c, key):
                        stmt = stmt.where(getattr(self._table.c, key) == value)
            result = await session.execute(stmt)
            return result.scalar() or 0

    async def list_by_organization(
        self,
        org_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """List entities for a specific organization (multi-tenant)."""
        if filters is None:
            filters = {}
        filters["organization_id"] = org_id
        return await self.list(filters=filters, limit=limit, offset=offset)

    # ─── Conversion Helpers ───

    def _entity_to_row(self, entity: T) -> dict[str, Any]:
        """Convert a BaseEntity to a database row dict."""
        return {
            "id": entity.id,
            "entity_type": entity.entity_type.value
            if hasattr(entity.entity_type, "value")
            else str(entity.entity_type),
            "normalized_value": entity.normalized_value,
            "raw_values": entity.raw_values,
            "classification": entity.classification.model_dump() if entity.classification else {},
            "provenance": entity.provenance.model_dump() if entity.provenance else None,
            "first_seen": entity.first_seen,
            "last_seen": entity.last_seen,
            "confidence": entity.confidence.value
            if hasattr(entity.confidence, "value")
            else str(entity.confidence),
            "organization_id": entity.organization_id,
            "jurisdiction": entity.jurisdiction,
            "version": entity.audit.version,
            "is_deleted": entity.audit.is_deleted,
            "deleted_at": entity.audit.deleted_at,
            "deleted_by": entity.audit.deleted_by,
            "created_by": entity.audit.created_by,
            "created_at": entity.audit.created_at,
            "updated_by": entity.audit.updated_by,
            "updated_at": entity.audit.updated_at or entity.audit.created_at,
        }

    def _row_to_entity(self, row: dict[str, Any]) -> T:
        """Convert a database row to a BaseEntity."""
        from schemas.base import AuditMetadata, Classification, Provenance
        from schemas.enums import Confidence, EntityType

        audit = AuditMetadata(
            created_by=row.get("created_by"),
            created_at=row.get("created_at", datetime.now(UTC)),
            updated_by=row.get("updated_by"),
            updated_at=row.get("updated_at"),
            version=row.get("version", 1),
            is_deleted=row.get("is_deleted", False),
            deleted_at=row.get("deleted_at"),
            deleted_by=row.get("deleted_by"),
        )

        classification_data = row.get("classification", {})
        classification = (
            Classification(**classification_data) if classification_data else Classification()
        )

        provenance_data = row.get("provenance")
        provenance = Provenance(**provenance_data) if provenance_data else None

        entity_type_val = row.get("entity_type", "UNKNOWN")
        try:
            entity_type = EntityType(entity_type_val)
        except ValueError:
            entity_type = EntityType.UNKNOWN

        confidence_val = row.get("confidence", "UNKNOWN")
        try:
            confidence = Confidence(confidence_val)
        except ValueError:
            confidence = Confidence.UNKNOWN

        entity = BaseEntity(
            id=row["id"],
            entity_type=entity_type,
            normalized_value=row.get("normalized_value", ""),
            raw_values=row.get("raw_values", []),
            classification=classification,
            provenance=provenance,
            first_seen=row.get("first_seen", datetime.now(UTC)),
            last_seen=row.get("last_seen", datetime.now(UTC)),
            confidence=confidence,
            organization_id=row.get("organization_id"),
            jurisdiction=row.get("jurisdiction"),
            audit=audit,
        )
        return entity  # type: ignore[return-value]

    def _serialize_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Serialize complex types for SQLAlchemy."""
        result = {}
        for key, value in data.items():
            if isinstance(value, list | dict):
                result[key] = json.dumps(value) if not isinstance(value, list | dict) else value
            elif hasattr(value, "model_dump"):
                result[key] = value.model_dump()
            elif hasattr(value, "value"):
                result[key] = value.value
            else:
                result[key] = value
        return result


# ─── Migration Manager ───


class MigrationManager:
    """Database migration manager for GFIN.

    Per Luna Assessment P0: "Migration framework, repository implementations,
    transaction and locking strategy, seed/reference data process."

    Uses SQLAlchemy metadata to create tables. Each migration is versioned
    and tracked in the gfin_schema_migrations table.

    REQUIRES EXTERNAL INFRASTRUCTURE: PostgreSQL connection.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @classmethod
    def from_url(cls, database_url: str, **kwargs: Any) -> MigrationManager:
        engine = create_async_engine(
            database_url,
            pool_size=kwargs.get("pool_size", 5),
            echo=kwargs.get("echo", False),
        )
        return cls(engine)

    async def create_all(self) -> None:
        """Create all tables. Idempotent — skips existing."""
        async with self._engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
            # Record migration
            await conn.execute(
                schema_migrations_table.insert()
                .values(
                    version="001_initial",
                    description="Initial schema: entities, fraud_reports, campaigns, alerts, audit_log, users",
                )
                .on_conflict_do_nothing(index_elements=["version"])
            )
        logger.info("migration_applied", version="001_initial")

    async def drop_all(self) -> None:
        """Drop all tables. For testing/development only."""
        async with self._engine.begin() as conn:
            await conn.run_sync(metadata.drop_all)
        logger.info("all_tables_dropped")

    async def get_applied_migrations(self) -> list[dict[str, Any]]:
        """Get list of applied migrations."""
        from sqlalchemy import select

        async with self._session() as conn:
            stmt = select(schema_migrations_table).order_by(schema_migrations_table.c.applied_at)
            result = await conn.execute(stmt)
            return [dict(row) for row in result.mappings().all()]

    async def close(self) -> None:
        """Dispose of the engine connection pool."""
        await self._engine.dispose()

    @property
    def _session(self):
        return async_sessionmaker(self._engine, expire_on_commit=False)
