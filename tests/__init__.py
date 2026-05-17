"""Test package — patches PostgreSQL types for SQLite compatibility.

These patches are needed when running tests with the default SQLite
in-memory database. They make SQLite understand PostgreSQL-specific
types like JSONB, ENUM, and BIGINT so that ``Base.metadata.create_all``
(and selective table creation) works without a real Postgres instance.

When running against a real PostgreSQL database (set
``TEST_DATABASE_URL=postgresql+asyncpg://...``), these patches are
harmless but unnecessary.

Notes:
- JSONB → treated as JSON (sqldialect compat)
- ENUM → treated as VARCHAR
- BIGINT → treated as INTEGER (SQLite requires INTEGER for auto-increment)
"""

# CRITICAL: Patch JSONB and ENUM before any model imports
import sqlalchemy.dialects.postgresql.json as pg_json
from sqlalchemy import types as sa_types


class JSONBCompat(sa_types.JSON):
    __visit_name__ = "JSONB"


pg_json.JSONB = JSONBCompat
sa_types.JSONB = JSONBCompat

# Patch ENUM for SQLite
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler


def _visit_jsonb(self, type_, **kw):
    return self.visit_JSON(type_, **kw)


SQLiteTypeCompiler.visit_JSONB = _visit_jsonb


def _visit_enum(self, type_, **kw):
    return self.visit_VARCHAR(type_, **kw)


SQLiteTypeCompiler.visit_enum = _visit_enum

# BigInteger → INTEGER for SQLite auto-increment support
# SQLite only auto-increments INTEGER PRIMARY KEY; BIGINT PRIMARY KEY does NOT.
def _visit_bigint(self, type_, **kw):
    return "INTEGER"


SQLiteTypeCompiler.visit_BIGINT = _visit_bigint
# Also patch the generic compiler so all paths are covered
from sqlalchemy.sql.compiler import GenericTypeCompiler

GenericTypeCompiler.visit_BIGINT = _visit_bigint