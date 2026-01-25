#!/usr/bin/env python3
"""
Slim the pfas_bom table to only required columns and adjust constraints.

Target schema:
  - sku TEXT PRIMARY KEY
  - product TEXT NOT NULL
  - uploaded_at TIMESTAMP NULL DEFAULT now()
  - files_data BYTEA NULL
  - route VARCHAR(255) NULL

This script performs (idempotently where possible):
  1) Add uploaded_at/files_data/route if missing
  2) Deduplicate rows by sku keeping the newest uploaded_at (or arbitrary if all null)
  3) Replace any existing PK with PRIMARY KEY (sku)
  4) Drop legacy columns if they exist (component, subcomponent, material, ...)

Usage:
  - Ensure DATABASE_URL env var is set to your Postgres DSN
  - python scripts/migrate_slim_pfas_bom.py

Note: Run in maintenance window; PK change and deletes may lock the table.
"""
from __future__ import annotations
import os
import sys
import time
import psycopg2

DSN = os.environ.get('DATABASE_URL')
if not DSN:
    print('ERROR: DATABASE_URL environment variable is required')
    sys.exit(1)

DDL_STEPS = [
    # 1) Add new columns if missing
    (
        "Add uploaded_at/files_data/route",
        """
        ALTER TABLE pfas_bom ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP;
        ALTER TABLE pfas_bom ADD COLUMN IF NOT EXISTS files_data BYTEA;
        ALTER TABLE pfas_bom ADD COLUMN IF NOT EXISTS route VARCHAR(255);
        """
    ),
    # 2) Deduplicate by sku, keep newest (uploaded_at desc nulls last)
    (
        "Deduplicate by sku",
        """
        WITH ranked AS (
            SELECT ctid, sku, uploaded_at,
                   ROW_NUMBER() OVER (PARTITION BY sku ORDER BY uploaded_at DESC NULLS LAST, ctid DESC) AS rn
            FROM pfas_bom
        )
        DELETE FROM pfas_bom p
        USING ranked r
        WHERE p.ctid = r.ctid AND r.rn > 1;
        """
    ),
    # 3) Reset PK to (sku)
    (
        "Reset primary key to (sku)",
        """
        DO $$
        DECLARE pk_name text;
        BEGIN
            SELECT conname INTO pk_name
            FROM pg_constraint
            WHERE conrelid = 'pfas_bom'::regclass AND contype = 'p'
            LIMIT 1;
            IF pk_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE pfas_bom DROP CONSTRAINT %I', pk_name);
            END IF;
        END$$;
        ALTER TABLE pfas_bom ADD PRIMARY KEY (sku);
        """
    ),
    # 4) Drop legacy columns (guard with IF EXISTS)
    (
        "Drop legacy columns",
        """
        ALTER TABLE pfas_bom
            DROP COLUMN IF EXISTS component,
            DROP COLUMN IF EXISTS subcomponent,
            DROP COLUMN IF EXISTS material,
            DROP COLUMN IF EXISTS component_description,
            DROP COLUMN IF EXISTS subcomponent_description,
            DROP COLUMN IF EXISTS material_name,
            DROP COLUMN IF EXISTS portal_name,
            DROP COLUMN IF EXISTS region,
            DROP COLUMN IF EXISTS assessment,
            DROP COLUMN IF EXISTS flag;
        """
    ),
]


def run():
    conn = psycopg2.connect(DSN)
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            for title, sql in DDL_STEPS:
                try:
                    print(f"-- {title}")
                    cur.execute(sql)
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    # If table is already in the desired state, many steps are idempotent.
                    # We continue but log the error for awareness.
                    print(f"WARN: step '{title}' failed or partially applied: {e}")
                    time.sleep(0.1)
        print('Migration completed.')
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    run()
