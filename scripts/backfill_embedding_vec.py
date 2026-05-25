#!/usr/bin/env python3
"""Backfill pgvector column from JSON embeddings using asyncpg directly.

This script:
1. Reads JSON embeddings from the `embedding` column
2. Converts them to halfvec format for the `embedding_vec` column
"""

import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.core.database import get_settings

async def backfill(limit: int = None):
    settings = get_settings()
    
    # Convert postgresql+asyncpg:// to postgresql:// for asyncpg driver
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Use asyncpg directly for array handling
    import asyncpg
    conn = await asyncpg.connect(db_url)
    
    try:
        # Get count of rows needing backfill
        total = await conn.fetchval("""
            SELECT COUNT(*) FROM openfoodfacts_products 
            WHERE embedding IS NOT NULL 
              AND embedding_vec IS NULL
        """)
        print(f"Found {total} rows to backfill")
        
        # Process in batches
        offset = 0
        batch_size = 100
        processed = 0
        
        while True:
            rows = await conn.fetch(f"""
                SELECT code, embedding 
                FROM openfoodfacts_products 
                WHERE embedding IS NOT NULL 
                  AND embedding_vec IS NULL
                ORDER BY code
                LIMIT {batch_size} OFFSET {offset}
            """)
            
            if not rows:
                break
            
            for row in rows:
                if limit and processed >= limit:
                    break
                code = row['code']
                embedding_json = row['embedding']
                try:
                    # Parse JSON embedding
                    embedding = json.loads(embedding_json)
                    
                    # Use pgvector's array-to-vector conversion function
                    # '[1,2,3]'::vector is the format we need
                    embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
                    
                    await conn.execute(
                        "UPDATE openfoodfacts_products SET embedding_vec = $1::halfvec(768) WHERE code = $2",
                        embedding_str,
                        code
                    )
                    processed += 1
                except Exception as e:
                    print(f"Error for code {code}: {e}")
            
            await conn.execute("COMMIT")
            print(f"Backfilled batch: {processed}/{total}")
            
            offset += batch_size
            if limit and processed >= limit:
                break
        
        print(f"Done! Backfilled {processed} rows")
    finally:
        await conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Backfill pgvector from JSON")
    parser.add_argument("--limit", type=int, default=None, help="Max rows to process")
    args = parser.parse_args()
    asyncio.run(backfill(limit=args.limit))