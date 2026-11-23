import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

SOURCES = {
    'amazon': 'Amazon Sale Report.csv', 'inventory': 'Sale Report.csv',
    'international': 'International sale Report.csv', 'price_may_2022': 'May-2022.csv',
    'price_march_2021': 'P  L March 2021.csv', 'expense_iigf': 'Expense IIGF.csv',
    'warehouse_comparison': 'Cloud Warehouse Compersion Chart.csv',
}

def main():
    root = Path('/output') / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    root.mkdir(parents=True, exist_ok=False)
    raw = root / 'raw'
    raw.mkdir()
    os.environ['LAKEHOUSE_RUN_DIR'] = str(root)
    os.environ['DBT_TARGET_PATH'] = str(root / 'dbt-target')
    os.environ['DBT_LOG_PATH'] = str(root / 'dbt-logs')
    os.environ['DBT_SEND_ANONYMOUS_USAGE_STATS'] = 'false'
    db = duckdb.connect(str(root / 'retail.duckdb'))
    inventory = []
    try:
        for code, filename in SOURCES.items():
            path = Path('/input') / filename
            digest = hashlib.sha256()
            with path.open('rb') as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(chunk)
            with path.open(encoding='utf-8-sig', newline='') as source:
                reader = csv.DictReader(source)
                if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                    raise ValueError(f'Invalid or duplicate column names: {code}')
                names = reader.fieldnames
                schema = pa.schema([pa.field(name, pa.string()) for name in names] + [pa.field('_source_row', pa.int64())])
                records, count = [], 0
                with pq.ParquetWriter(raw / f'{code}.parquet', schema, compression='zstd') as writer:
                    for row in reader:
                        if None in row or any(v is None for v in row.values()):
                            raise ValueError(f'Malformed CSV record in {code}, record {count + 1}')
                        row['_source_row'] = count + 1
                        records.append(row)
                        count += 1
                        if len(records) == 10000:
                            writer.write_table(pa.Table.from_pylist(records, schema=schema)); records.clear()
                    if records:
                        writer.write_table(pa.Table.from_pylist(records, schema=schema))
            parquet = str(raw / f'{code}.parquet')
            db.execute(f'CREATE TABLE raw_{code} AS SELECT * FROM read_parquet(?)', [parquet])
            actual = db.execute(f'SELECT count(*) FROM raw_{code}').fetchone()[0]
            if actual != count:
                raise ValueError(f'Raw count mismatch: {code}')
            inventory.append({'source_code': code, 'file_name': filename, 'sha256': digest.hexdigest(), 'row_count': count})
        # A persistent DuckDB registry allocates increasing product IDs. It is separate
        # from the per-run database and must be retained between runs.
        registry = duckdb.connect('/output/product-registry.duckdb')
        try:
            registry.execute('CREATE SEQUENCE IF NOT EXISTS product_id_seq START 1')
            registry.execute("CREATE TABLE IF NOT EXISTS products (product_id BIGINT PRIMARY KEY DEFAULT nextval('product_id_seq'), sku VARCHAR UNIQUE NOT NULL)")
            candidates = db.execute("SELECT DISTINCT sku FROM (SELECT upper(trim(\"SKU\")) sku FROM raw_amazon UNION ALL SELECT upper(trim(\"SKU Code\")) FROM raw_inventory UNION ALL SELECT upper(trim(\"SKU\")) FROM raw_international UNION ALL SELECT upper(trim(\"Sku\")) FROM raw_price_may_2022 UNION ALL SELECT upper(trim(\"Sku\")) FROM raw_price_march_2021) WHERE sku <> '' ORDER BY sku").fetchall()
            registry.register('new_skus', pa.table({'sku': [row[0] for row in candidates]}))
            registry.execute('INSERT INTO products(sku) SELECT sku FROM new_skus WHERE sku NOT IN (SELECT sku FROM products) ORDER BY sku')
            products = registry.execute('SELECT product_id, sku FROM products').fetchall()
        finally:
            registry.close()
        db.execute('CREATE TABLE raw_product_registry (product_id BIGINT, sku VARCHAR)')
        if products:
            db.register('registry_rows', pa.table({'product_id': [row[0] for row in products], 'sku': [row[1] for row in products]}))
            db.execute('INSERT INTO raw_product_registry SELECT * FROM registry_rows')
        db.execute('CREATE TABLE raw_source_manifest (source_code VARCHAR, file_name VARCHAR, sha256 VARCHAR, row_count BIGINT)')
        db.executemany('INSERT INTO raw_source_manifest VALUES (?, ?, ?, ?)', [(r['source_code'], r['file_name'], r['sha256'], r['row_count']) for r in inventory])
        # Source-row identities are stable for an unchanged source-file hash.
        registry = duckdb.connect('/output/entity-registry.duckdb')
        try:
            registry.execute('CREATE SEQUENCE IF NOT EXISTS entity_id_seq START 1')
            registry.execute("CREATE TABLE IF NOT EXISTS ids (entity_id BIGINT PRIMARY KEY DEFAULT nextval('entity_id_seq'), entity VARCHAR NOT NULL, natural_id VARCHAR NOT NULL, UNIQUE(entity,natural_id))")
            parts = []
            for item in inventory:
                code = item['source_code']
                parts.append(db.execute(f"SELECT '{code}' AS entity, '{item['sha256']}:' || CAST(_source_row AS VARCHAR) AS natural_id FROM raw_{code}").arrow())
            candidates = pa.concat_tables(parts)
            registry.register('incoming_ids', candidates)
            registry.execute('INSERT INTO ids(entity,natural_id) SELECT i.entity,i.natural_id FROM incoming_ids i WHERE NOT EXISTS (SELECT 1 FROM ids r WHERE r.entity=i.entity AND r.natural_id=i.natural_id) ORDER BY i.entity,i.natural_id')
            ids = registry.execute('SELECT entity_id,entity,natural_id FROM ids').arrow()
        finally:
            registry.close()
        db.register('id_rows', ids)
        db.execute('CREATE TABLE raw_entity_registry AS SELECT * FROM id_rows')
        db.execute("CREATE TABLE raw_entity_current AS SELECT r.entity_id, r.entity, try_cast(split_part(r.natural_id, ':', 2) AS BIGINT) AS source_row FROM raw_entity_registry r JOIN raw_source_manifest m ON r.entity = m.source_code AND split_part(r.natural_id, ':', 1) = m.sha256")
        common = ['MRP Old', 'Final MRP Old', 'Ajio MRP', 'Amazon MRP', 'Amazon FBA MRP', 'Flipkart MRP', 'Limeroad MRP', 'Myntra MRP', 'Paytm MRP', 'Snapdeal MRP']
        price_rows = db.execute("SELECT entity_id, entity FROM raw_entity_current WHERE entity IN ('price_may_2022','price_march_2021')").fetchall()
        quote_keys = [f'{row_id}:{metric}' for row_id, entity in price_rows for metric in ((['TP'] if entity == 'price_may_2022' else ['TP 1','TP 2']) + common)]
        registry = duckdb.connect('/output/entity-registry.duckdb')
        try:
            registry.register('incoming_quotes', pa.table({'natural_id': quote_keys}))
            registry.execute("INSERT INTO ids(entity,natural_id) SELECT 'price_quote', i.natural_id FROM incoming_quotes i WHERE NOT EXISTS (SELECT 1 FROM ids r WHERE r.entity='price_quote' AND r.natural_id=i.natural_id) ORDER BY i.natural_id")
            quotes = registry.execute("SELECT entity_id, natural_id FROM ids WHERE entity='price_quote'").arrow()
        finally:
            registry.close()
        db.register('quote_rows', quotes)
        db.execute("CREATE TABLE raw_quote_registry AS SELECT entity_id, try_cast(split_part(natural_id, ':', 1) AS BIGINT) AS price_sheet_row_id, split_part(natural_id, ':', 2) AS metric FROM quote_rows")
    finally:
        db.close()
    subprocess.run(['dbt', 'build', '--project-dir', '/app', '--profiles-dir', '/app', '--no-use-colors'], check=True)
    db = duckdb.connect(str(root / 'retail.duckdb'))
    try:
        reporting = root / 'reporting'; reporting.mkdir()
        for name in ('stg_sales_lines', 'stg_inventory', 'mart_fulfillment_category', 'mart_inventory_category', 'mart_source_quality', 'stg_international_sales', 'stg_price_sheet', 'fact_price_quote', 'stg_expense_rows', 'stg_warehouse_rows', 'dim_product'):
            result = db.execute(f'SELECT * FROM "{name}"')
            with (reporting / f'{name}.csv').open('w', encoding='utf-8', newline='') as stream:
                writer = csv.writer(stream); writer.writerow([c[0] for c in result.description])
                while rows := result.fetchmany(10000): writer.writerows(rows)
            dest = str(reporting / f'{name}.parquet').replace("'", "''")
            db.execute(f'COPY (SELECT * FROM "{name}") TO \'{dest}\' (FORMAT PARQUET, COMPRESSION ZSTD)')
        summary = {'run_id_utc': root.name, 'sources': inventory, 'status': 'passed',
                   'id_scope': 'product IDs persist by normalized SKU; source-row IDs persist by source hash and row position'}
        (root / 'run-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(summary, indent=2))
    finally:
        db.close()

if __name__ == '__main__': main()
