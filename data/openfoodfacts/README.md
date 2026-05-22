# Open Food Facts Data

This directory is for raw Open Food Facts exports and generated local lookup
data. Keep the large source files out of git.

Do not load the full Open Food Facts Parquet file with `pandas.read_parquet`.
The raw export is too large and nested, and pandas can inflate it into far more
memory than the server has available.

Current raw source:

- `openfoodfacts-products.jsonl.gz` from the Open Food Facts JSONL export.

Safe import path:

```bash
cd /root/t1d
source venv/bin/activate
python3 scripts/import_openfoodfacts_jsonl.py \
  --ensure-schema \
  --replace \
  --database-url postgresql://postgres:postgres@localhost:5432/t1d_companion
```

The importer streams the compressed JSONL line by line and writes only the
T1D-focused nutrition lookup fields to Postgres.
