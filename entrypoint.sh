#!/bin/bash
set -e

echo "========================================"
echo "Football Data Warehouse Pipeline"
echo "========================================"

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
until PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\q' 2>/dev/null; do
    sleep 2
done
echo "PostgreSQL is ready."

# Initialize database (schemas, tables, materialized views)
echo ""
echo "--- Setting up database ---"
for sql_file in sql/01_init_schemas.sql sql/02_raw_tables.sql sql/03_silver_tables.sql sql/04_gold.sql; do
    echo "Running $sql_file..."
    PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$sql_file"
done

# Run pipeline
echo ""
echo "--- Running pipeline ---"
python main.py

echo ""
echo "========================================"
echo "Pipeline completed successfully!"
echo "========================================"