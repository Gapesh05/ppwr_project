"""
Migration script to fix upload_timestamp_ms column overflow.
Changes column type from INTEGER to BIGINT to support millisecond timestamps.
"""
from app import app
from models import db
import sqlalchemy as sa

def run_migration():
    """Run the migration to alter upload_timestamp_ms column"""
    with app.app_context():
        try:
            # Use raw SQL to alter the column
            # PostgreSQL syntax to change column type
            alter_sql = """
            ALTER TABLE upload_audit_logs
            ALTER COLUMN upload_timestamp_ms TYPE BIGINT;
            """
            
            db.session.execute(sa.text(alter_sql))
            db.session.commit()
            
            print("✓ Migration successful: upload_timestamp_ms column changed to BIGINT")
            return True
        except Exception as e:
            print(f"✗ Migration failed: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = run_migration()
    exit(0 if success else 1)
