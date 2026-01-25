# config.py
import os

class Config:
    """Configuration.

    Allows overriding the database with the environment variable DATABASE_URL.
    If DATABASE_URL is not set, falls back to the existing PostgreSQL connection.
    This makes it easy to point the app at a local sqlite DB for testing inside
    Docker without changing the code further.
    """
    DB_USER =  'airadbuser'
    DB_PASSWORD = 'Password123'
    DB_HOST = '10.134.44.228'     # host / IP address
    DB_PORT = 5432
    DB_NAME = 'pfasdb'

    # Base Postgres DSN
    default_pg = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    # Primary DB used for PFAS/BOM data. Prevent accidental SQLite usage
    # from an environment override which has been causing open-file errors.
    env_db = os.environ.get('DATABASE_URL')
    if env_db and env_db.startswith('postgresql'):
        SQLALCHEMY_DATABASE_URI = env_db
    else:
        SQLALCHEMY_DATABASE_URI = default_pg
    # Separate DB for supplier declarations (allows pointing declarations at a
    # different Postgres instance). If not set, falls back to the primary DB.
    SUPPLIER_DATABASE_URL = os.environ.get('SUPPLIER_DATABASE_URL', SQLALCHEMY_DATABASE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Bind supplier declarations to a separate database when provided
    SQLALCHEMY_BINDS = {
        'supplier': SUPPLIER_DATABASE_URL
    }
    # Engine options to limit number of DB connections from this app.
    # These values are conservative for local development; adjust if you run
    # multiple app instances or heavier load in production.
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 1800,
    }
