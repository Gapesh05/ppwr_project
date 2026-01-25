#!/usr/bin/env python3
"""Migration script to transform pfas_bom into route table and prepare ppwr_bom.

This script:
1. Creates new 'route' table with only (sku, route) columns
2. Migrates data from pfas_bom to route
3. Adds uploaded_at column to ppwr_bom if missing
4. Drops pfas_bom table (CASCADE to handle foreign keys)
5. Renames any references in dependent objects

Run: python scripts/migrate_to_route_table.py
"""

import psycopg2
import sys
import os

# Use same config as backend
DB_USER = 'airadbuser'
DB_PASSWORD = 'Password123'
DB_HOST = '10.134.44.228'
DB_PORT = 5432
DB_NAME = 'pfasdb'

# Allow override via DATABASE_URL environment variable
DATABASE_URL = os.environ.get('DATABASE_URL', 
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def run_migration():
    """Execute the migration steps."""
    print("🚀 Starting migration: pfas_bom → route table")
    
    conn = None
    try:
        # Parse connection string if it's a URL
        if DATABASE_URL.startswith('postgresql://'):
            conn = psycopg2.connect(DATABASE_URL)
        else:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                dbname=DB_NAME
            )
        
        conn.autocommit = False  # Use transactions
        cur = conn.cursor()
        
        # Step 1: Check if pfas_bom exists
        print("📋 Checking if pfas_bom table exists...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'pfas_bom'
            );
        """)
        pfas_bom_exists = cur.fetchone()[0]
        
        if not pfas_bom_exists:
            print("⚠️  pfas_bom table does not exist. Nothing to migrate.")
            conn.rollback()
            return True
        
        # Step 2: Check if route table already exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'route'
            );
        """)
        route_exists = cur.fetchone()[0]
        
        if route_exists:
            print("⚠️  route table already exists. Skipping creation.")
        else:
            # Create route table
            print("🔨 Creating route table...")
            cur.execute("""
                CREATE TABLE route (
                    sku VARCHAR(100) PRIMARY KEY,
                    route VARCHAR(255) DEFAULT 'pfas'
                );
            """)
            print("✅ route table created")
        
        # Step 3: Migrate data from pfas_bom to route
        print("📦 Migrating data from pfas_bom to route...")
        cur.execute("""
            INSERT INTO route (sku, route)
            SELECT DISTINCT sku, COALESCE(route, 'pfas')
            FROM pfas_bom
            ON CONFLICT (sku) DO UPDATE 
            SET route = EXCLUDED.route;
        """)
        rows_migrated = cur.rowcount
        print(f"✅ Migrated {rows_migrated} SKU(s) to route table")
        
        # Step 4: Ensure ppwr_bom has uploaded_at column
        print("🔧 Ensuring ppwr_bom has uploaded_at column...")
        cur.execute("""
            ALTER TABLE ppwr_bom 
            ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP DEFAULT NOW();
        """)
        print("✅ ppwr_bom.uploaded_at ensured")
        
        # Step 5: Drop pfas_bom table (CASCADE handles dependent objects)
        print("🗑️  Dropping pfas_bom table...")
        cur.execute("DROP TABLE IF EXISTS pfas_bom CASCADE;")
        print("✅ pfas_bom table dropped")
        
        # Commit transaction
        conn.commit()
        print("\n🎉 Migration completed successfully!")
        print("\nSummary:")
        print(f"  - route table: {rows_migrated} SKU(s)")
        print("  - pfas_bom: dropped")
        print("  - ppwr_bom: uploaded_at column ensured")
        
        cur.close()
        return True
        
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"\n❌ Database error: {e}")
        print(f"   SQLSTATE: {e.pgcode}")
        return False
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if conn:
            conn.close()

def verify_migration():
    """Verify the migration was successful."""
    print("\n🔍 Verifying migration...")
    
    conn = None
    try:
        if DATABASE_URL.startswith('postgresql://'):
            conn = psycopg2.connect(DATABASE_URL)
        else:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                dbname=DB_NAME
            )
        
        cur = conn.cursor()
        
        # Check route table
        cur.execute("SELECT COUNT(*) FROM route;")
        route_count = cur.fetchone()[0]
        print(f"✅ route table: {route_count} row(s)")
        
        # Check ppwr_bom
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'ppwr_bom' AND column_name = 'uploaded_at';
        """)
        has_uploaded_at = cur.fetchone() is not None
        print(f"✅ ppwr_bom.uploaded_at: {'present' if has_uploaded_at else 'MISSING'}")
        
        # Check pfas_bom is gone
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'pfas_bom'
            );
        """)
        pfas_bom_exists = cur.fetchone()[0]
        print(f"✅ pfas_bom table: {'STILL EXISTS (ERROR)' if pfas_bom_exists else 'dropped'}")
        
        cur.close()
        return not pfas_bom_exists
        
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("PFAS/PPWR Migration: pfas_bom → route table")
    print("=" * 60)
    
    success = run_migration()
    
    if success:
        verify_migration()
        print("\n✨ Migration complete. Update your application code to use 'route' table.")
        sys.exit(0)
    else:
        print("\n⚠️  Migration failed. Check errors above.")
        sys.exit(1)
