#!/usr/bin/env python3
"""Generate embeddings for Open Food Facts products using sentence-transformers.

This script:
1. Loads products without embeddings from the database
2. Generates sentence-transformers embeddings for each product
3. Stores embeddings back to the database (both JSON and pgvector columns)

Usage:
    python scripts/generate_food_embeddings.py [--batch-size 100] [--limit 1000] [--model sentence-transformers/multi-qa-mpnet-base-dot-v1]
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Load environment
_env = REPO_ROOT / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


class SentenceTransformerEmbedder:
    """Lightweight wrapper around sentence-transformers for embedding generation."""
    
    def __init__(self, model_name: str = "sentence-transformers/multi-qa-mpnet-base-dot-v1"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            print(f"Loaded sentence-transformers model: {model_name} (dim={self.dimension})")
        except ImportError:
            print("Installing sentence-transformers...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers", "-q"])
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            print(f"Loaded sentence-transformers model: {model_name} (dim={self.dimension})")
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        return self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True).tolist()


async def generate_embeddings(
    batch_size: int = 100, 
    limit: int = None, 
    model_name: str = "sentence-transformers/multi-qa-mpnet-base-dot-v1"
):
    """Generate embeddings for products missing them using asyncpg directly."""
    from app.core.database import get_settings
    import asyncpg
    
    settings = get_settings()
    
    # Convert to asyncpg URL
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db_url)
    
    try:
        embedder = SentenceTransformerEmbedder(model_name)
        
        # Get products without embeddings
        total = await conn.fetchval("""
            SELECT COUNT(*) FROM openfoodfacts_products 
            WHERE embedding_vec IS NULL AND carbs_100g IS NOT NULL
        """)
        print(f"Found {total} products without embeddings")
        
        offset = 0
        processed = 0
        
        while True:
            # Fetch batch
            rows = await conn.fetch(f"""
                SELECT code, product_name, brands 
                FROM openfoodfacts_products 
                WHERE embedding_vec IS NULL AND carbs_100g IS NOT NULL
                ORDER BY code
                LIMIT {batch_size} OFFSET {offset}
            """)
            
            if not rows:
                break
            
            # Build texts and generate embeddings
            texts = []
            codes = []
            for row in rows:
                code = row['code']
                name = row['product_name']
                brands = row['brands']
                parts = []
                if brands:
                    parts.append(brands)
                if name:
                    parts.append(name)
                texts.append(" ".join(parts))
                codes.append(code)
            
            embeddings = embedder.embed(texts)
            
            # Update each product with both JSON and halfvec columns
            for code, embedding in zip(codes, embeddings):
                embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
                await conn.execute(
                    "UPDATE openfoodfacts_products SET embedding = $1, embedding_vec = $2::halfvec(768) WHERE code = $3",
                    json.dumps(embedding),
                    embedding_str,
                    code
                )
                processed += 1
            
            await conn.execute("COMMIT")
            print(f"Committed batch: {processed}/{total} products embedded")
            
            offset += batch_size
            if limit and processed >= limit:
                break
        
        print(f"Done! Embedded {processed} products")
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate embeddings for food products")
    parser.add_argument("--batch-size", type=int, default=100, help="Commit batch size")
    parser.add_argument("--limit", type=int, default=None, help="Max products to process")
    parser.add_argument("--model", type=str, default="sentence-transformers/multi-qa-mpnet-base-dot-v1",
                        help="Sentence-transformers model name")
    args = parser.parse_args()
    
    if args.limit:
        print(f"Processing up to {args.limit} products")
    
    asyncio.run(generate_embeddings(batch_size=args.batch_size, limit=args.limit, model_name=args.model))