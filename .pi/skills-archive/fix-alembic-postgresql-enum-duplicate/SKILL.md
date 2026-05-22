---
name: "fix-alembic-postgresql-enum-duplicate"
description: "Fix PostgreSQL ENUM type double-creation in Alembic migrations when both op.execute('CREATE TYPE...') and sa.Enum(...) (default create_type=True) try to create the same ENUM type, causing psycopg2.errors.DuplicateObject. Add create_type=False to resolve."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Fix PostgreSQL ENUM Type Double-Creation in Alembic Migrations

## When to Use

- Alembic migration fails with `psycopg2.errors.DuplicateObject: type "..." already exists`
- The error points to a PostgreSQL ENUM type creation in the migration
- The migration has BOTH an `op.execute("CREATE TYPE ...")` call AND a column definition using `sa.Enum(...)` or `postgresql.ENUM(...)` that references the same type name
- The ENUM type was already created by a previous migration, by SQLAlchemy's `Base.metadata.create_all()` at app startup, or by an earlier `op.execute("CREATE TYPE ...")` in the same migration

**Boundary**: This is about Alembic migration ENUM conflicts specifically. For general async/sync Alembic driver issues, use `fix-alembic-async-env-py`. For failing `docker build` due to missing LICENSE, use `fix-pyproject-license-docker-build`.

## Procedure

### 1. Confirm the error signature

Look for this exact error in migration output:

```
psycopg2.errors.DuplicateObject: type "graph_edge_type" already exists
```

The ENUM type name varies, but the error is consistently `DuplicateObject` from PostgreSQL when CREATE TYPE is called for an existing type.

### 2. Identify the migration causing the error

```bash
# Find the most recent failed migration
alembic history
```

Check the migration file that failed — it will contain either or both:
- An `op.execute("CREATE TYPE <name> AS ENUM (...)")` statement
- A column definition with `sa.Enum(...)` or `postgresql.ENUM(...)` using `name="<type_name>"`

### 3. Identify all sources creating the same ENUM

Common sources that can create the same ENUM type:

| Source | How it creates the type |
|--------|------------------------|
| `op.execute("CREATE TYPE x AS ENUM(...)")` | Explicit SQL |
| `sa.Column("col", sa.Enum(*values, name="x"))` | Implicit via `create_type=True` (default) |
| `sa.Column("col", postgresql.ENUM(*values, name="x"))` | Implicit via `create_type=True` (default) |
| Previous migration's column definition | Auto-created when migration ran |
| `Base.metadata.create_all()` at app startup | Creates tables + ENUMs before Alembic runs |
| `op.create_table(...)` with ENUM column | Creates type implicitly with the table |

### 4. Fix by adding `create_type=False`

In the migration, for any column-level ENUM that references a type already being created by another source, add `create_type=False`:

```python
# Before (causes DuplicateObject if type already exists):
sa.Column("edge_type", sa.Enum(*EDGE_TYPES, name="graph_edge_type"))

# After (references existing type, doesn't try to recreate):
sa.Column("edge_type", sa.Enum(*EDGE_TYPES, name="graph_edge_type", create_type=False))
```

For `postgresql.ENUM`:
```python
# Before:
sa.Column("edge_type", postgresql.ENUM(*EDGE_TYPES, name="graph_edge_type"))

# After:
sa.Column("edge_type", postgresql.ENUM(*EDGE_TYPES, name="graph_edge_type", create_type=False))
```

### 5. Handle the remaining CREATE TYPE

After adding `create_type=False` to column definitions, decide which single source should create the type:

- **Option A**: Let an explicit `op.execute("CREATE TYPE...")` remain as the single source of truth. This gives you full control.
- **Option B**: Remove the `op.execute("CREATE TYPE...")` and let the column's `sa.Enum(...)` (with `create_type=True`, the default) create it. Simpler.
- **Option C**: Wrap the `op.execute("CREATE TYPE...")` in a try/except to handle the case where the type already exists from a different source (e.g., `create_all()` at startup):

```python
from sqlalchemy.exc import ProgrammingError

try:
    op.execute("CREATE TYPE graph_edge_type AS ENUM ('value1', 'value2')")
except ProgrammingError as e:
    # Type already exists (from create_all() or prior migration)
    pass
```

**Prefer Option C** when the ENUM might be created by `Base.metadata.create_all()` at app startup (common in FastAPI apps). Without the try/except, a clean deployment (fresh DB, no existing objects) works fine, but restarting a running instance would fail.

### 6. Verify the fix

```bash
# For a fresh database (no existing ENUM):
alembic upgrade head

# For a database where the ENUM already exists:
alembic upgrade head +1  # downgrade then upgrade
```

The migration should complete without `DuplicateObject` errors.

## Pitfalls

- **`create_type` is inheritable via `inherit_schema=True`**: If your ENUM column uses `inherit_schema=True`, the `create_type` kwarg must be on the column definition itself, not just the base type.
- **Fresh vs existing DB**: A migration that works on a fresh DB (docker-compose down -v) may fail on an existing DB. Always test both paths.
- **ENUM type name collision across migrations**: If two different migrations define ENUM columns with the same type name, the second migration fails even if no `op.execute` is involved — the column's `sa.Enum()` auto-creates the type. Add `create_type=False` to the second migration's column.
- **`op.add_column` vs `op.create_table`**: Both auto-create ENUM types from column definitions. If you're adding a column to an existing table, `op.add_column(some_table, sa.Column(..., sa.Enum(..., name="x")))` will try to CREATE TYPE x. If x already exists, use `create_type=False`.
- **ENUM values must match exactly**: If `create_type=False` references an existing type but the Enum values differ between the column definition and the actual type, PostgreSQL raises an error at DDL time.
- **Alembic batch mode**: In batch mode (`with op.batch_alter_table(...)`), column ENUMs are handled differently — the migration context may not auto-create the type. Test with actual DB, not just --sql dry-run.
- **Not just Alembic**: The same issue occurs in raw SQLAlchemy `Table` definitions or raw SQL where both `CREATE TYPE` and a column with that type are present.

## Verification

1. `alembic upgrade head` completes without `DuplicateObject` error
2. `alembic history` shows the migration in the chain
3. The ENUM type exists in the database: `\dT+ <type_name>` in psql
4. The table column references the correct ENUM: `\d <table_name>` shows the column with the correct type
5. INSERT with valid ENUM values works: `INSERT INTO <table> (<enum_col>) VALUES ('valid_value')`
6. Both fresh-DB and existing-DB deployment paths work (verify against both scenarios if possible)