---
name: "stream-jsonl-to-postgres"
description: "Stream gzipped JSONL files directly into Postgres using asyncpg COPY with async batch processing. Use when importing large Open Food Facts or similar exports without pandas or full disk decompression."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use
When you need to import large gzipped JSONL exports (like Open Food Facts, OpenStreetMap data, or log files) directly into Postgres without:
- Full disk decompression
- Loading everything into memory
- Using pandas
- Writing intermediate CSV files

## Procedure

### 1. Set up async connection and COPY target
```python
import asyncio
import gzip
import json
import asyncpg

async def setup_pool(database_url: str):
    return await asyncpg.create_pool(database_url, min_size=5, max_size=10)

async def prepare_copy(conn, table: str, columns: list[str]):
    # asyncpg COPY requires parameterized table/column specification
    cols = ", ".join(columns)
    return await conn.copy(f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT CSV)")
```

### 2. Stream and process line-by-line
```python
async def stream_jsonl_gz(filepath: str, batch_size: int = 1000):
    """Generator yielding batches of parsed JSON records."""
    batch = []
    with gzip.open(filepath, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                batch.append(record)
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
    if batch:
        yield batch
```

### 3. Filter and transform fields
```python
def extract_fields(record: dict, field_mapping: dict[str, str]) -> list:
    """Extract only needed fields, return as list for COPY format."""
    row = []
    for json_path, pg_col in field_mapping.items():
        # Handle nested paths like "nutrition.calories"
        parts = json_path.split(".")
        value = record
        for part in parts:
            value = value.get(part, None) if isinstance(value, dict) else None
            if value is None:
                break
        row.append(value)
    return row
```

### 4. Write batches via async COPY
```python
async def copy_batch(copy_stream, records: list[list]):
    """Write a batch to Postgres via COPY."""
    for record in records:
        # COPY expects CSV format: values separated by tabs, \N for NULL
        line = "\t".join(
            str(v).replace("\t", " ").replace("\n", " ") if v is not None else "\\N"
            for v in record
        )
        await copy_stream.write(f"{line}\n")
    await copy_stream.flush()
```

### 5. Complete import pipeline
```python
async def import_jsonl_to_postgres(
    filepath: str,
    table: str,
    field_mapping: dict,
    database_url: str,
    batch_size: int = 1000
):
    pool = await setup_pool(database_url)
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            copy_stream = await conn.copy(
                f"COPY {table} ({', '.join(field_mapping.values())}) FROM STDIN"
            )
            
            async for batch in stream_jsonl_gz(filepath, batch_size):
                rows = [extract_fields(r, field_mapping) for r in batch]
                await copy_batch(copy_stream, rows)
            
            await copy_stream.finish()
    
    await pool.close()
```

## Pitfalls

1. **Memory**: Don't accumulate all records - yield batches immediately
2. **Encoding**: Explicitly specify UTF-8 when opening gzipped files
3. **NULL handling**: Use `\N` for NULL values in COPY format
4. **Transactions**: Wrap COPY in transaction for atomicity
5. **Connection pooling**: Use pool.acquire() to avoid connection storms
6. **CSV escaping**: Escape tabs and newlines in string values

## Verification
- Compare source line count to destination row count
- Check that NULL values are properly handled (`\\N` in COPY, not empty string)
- Verify no duplicate primary keys if using INSERT ... ON CONFLICT