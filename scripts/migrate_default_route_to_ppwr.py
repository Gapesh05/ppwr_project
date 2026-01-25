#!/usr/bin/env python3
"""
Migration script to change default route from 'pfas' to 'ppwr'.

This script:
1. Updates all NULL route values to 'ppwr'
2. Updates all existing 'pfas' routes to 'ppwr' (optional - commented out by default)
3. Changes the database column default to 'ppwr'

Usage:
    python scripts/migrate_default_route_to_ppwr.py

Environment:
    DATABASE_URL - Optional. Defaults to the standard PFAS database connection.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'frontend'))

try:
    import psycopg2
    from config import Config
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("Make sure psycopg2 is installed: pip install psycopg2-binary")
    sys.exit(1)


def main():
    # Get database URL from environment or config
    database_url = os.environ.get('DATABASE_URL', Config.SQLALCHEMY_DATABASE_URI)
    
    print(f"🔗 Connecting to database...")
    print(f"   {database_url.split('@')[-1] if '@' in database_url else database_url}")
    
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("\n📊 Checking current route distribution...")
        cur.execute("SELECT route, COUNT(*) FROM route GROUP BY route ORDER BY route NULLS FIRST;")
        before_stats = cur.fetchall()
        print("   Current routes:")
        for route_val, count in before_stats:
            route_display = 'NULL' if route_val is None else route_val
            print(f"     {route_display}: {count}")
        
        # Step 1: Update NULL routes to 'ppwr'
        print("\n✅ Step 1: Updating NULL routes to 'ppwr'...")
        cur.execute("UPDATE route SET route = 'ppwr' WHERE route IS NULL;")
        null_updated = cur.rowcount
        print(f"   Updated {null_updated} NULL route(s) to 'ppwr'")
        
        # Step 2: (Optional) Convert all 'pfas' routes to 'ppwr'
        # Uncomment the following lines if you want to convert ALL existing PFAS routes to PPWR:
        # print("\n✅ Step 2: Converting all 'pfas' routes to 'ppwr'...")
        # cur.execute("UPDATE route SET route = 'ppwr' WHERE route = 'pfas';")
        # pfas_updated = cur.rowcount
        # print(f"   Converted {pfas_updated} 'pfas' route(s) to 'ppwr'")
        
        # Step 3: Change database column default
        print("\n✅ Step 3: Changing database column default to 'ppwr'...")
        cur.execute("ALTER TABLE route ALTER COLUMN route SET DEFAULT 'ppwr';")
        print("   Database column default updated to 'ppwr'")
        
        # Show final distribution
        print("\n📊 Final route distribution:")
        cur.execute("SELECT route, COUNT(*) FROM route GROUP BY route ORDER BY route;")
        after_stats = cur.fetchall()
        for route_val, count in after_stats:
            print(f"     {route_val}: {count}")
        
        cur.close()
        conn.close()
        
        print("\n✨ Migration completed successfully!")
        print("\n📝 Next steps:")
        print("   1. Test BOM upload without selecting assessment checkbox")
        print("   2. Verify new products default to PPWR tab")
        print("   3. Check dashboard displays PPWR badges for new products")
        
        return 0
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    print("=" * 60)
    print("   PFAS → PPWR Default Route Migration")
    print("=" * 60)
    sys.exit(main())
