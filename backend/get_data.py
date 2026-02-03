import psycopg2
from backend.config import get_config_loader

# Initialize config loader
config_loader = get_config_loader()

def get_file_upload_by_material_id(number: int) -> dict | None:
    """
    Fetch a single record from file_uploads where:
        client = 'PFAS'
        alias = '{number}_PFAS'

    Returns:
        dict with keys: "client", "alias", "filename", "collection-name"
        or None if not found.
    """
    conn = None
    try:
        # Load PostgreSQL config
        pg_config = {
            "host": config_loader.get("storage", "postgresql", "host"),
            "port": config_loader.get("storage", "postgresql", "port"),
            "dbname": config_loader.get("storage", "postgresql", "dbname"),
            "user": config_loader.get("storage", "postgresql", "user"),
            "password": config_loader.get("storage", "postgresql", "password")
        }

        if not all(pg_config.values()):
            raise ValueError("Missing PostgreSQL configuration in config.py")

        # Connect
        conn = psycopg2.connect(**pg_config)
        cur = conn.cursor()

        # Construct alias
        alias_pattern = f"{number}_PFAS"

        # Query — select only needed columns
        query = """
        SELECT client, originalfilename, alias, collection
        FROM file_uploads
        WHERE client = %s AND alias = %s;
        """
        cur.execute(query, ("PFAS", alias_pattern))
        row = cur.fetchone()  # Only get one — assuming alias is unique

        cur.close()

        if not row:
            return None  # Not found

        # Map to desired dict structure
        result = {
            "client": row[0],
            "filename": row[1],          # originalfilename → filename
            "alias": row[2],
            "collection-name": row[3]     # collection → collection-name
        }

        return result

    except psycopg2.Error as e:
        raise RuntimeError(f"Database error: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {e}") from e
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    number = 5995
    result = get_file_upload_by_material_id(number)

    if result:
        print("✅ Found record:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        print(f"❌ No record found for number {number}")