import os
import sqlite3


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

# Vercel  -> Neon PostgreSQL
# Local   -> SQLite
#
# This keeps your existing local workflow unchanged.
# ============================================================

IS_VERCEL = bool(os.environ.get("VERCEL"))

DATABASE_URL = os.environ.get("DATABASE_URL")


# ============================================================
# POSTGRESQL CURSOR COMPATIBILITY
# ============================================================

class PostgresCursorWrapper:

    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, params=None):

        # Convert SQLite-style ? placeholders
        # into PostgreSQL-style %s placeholders.
        query = query.replace("?", "%s")

        if params is None:
            return self.cursor.execute(query)

        return self.cursor.execute(query, params)

    def executemany(self, query, params):
        query = query.replace("?", "%s")
        return self.cursor.executemany(query, params)

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchmany(self, size=None):

        if size is None:
            return self.cursor.fetchmany()

        return self.cursor.fetchmany(size)

    def __iter__(self):
        return iter(self.cursor)

    def __getattr__(self, name):
        return getattr(self.cursor, name)


# ============================================================
# POSTGRESQL CONNECTION WRAPPER
# ============================================================

class PostgresConnectionWrapper:

    def __init__(self, connection):
        self.connection = connection

    def cursor(self):
        from psycopg2.extras import RealDictCursor

        cursor = self.connection.cursor(
            cursor_factory=RealDictCursor
        )

        return PostgresCursorWrapper(cursor)

    def commit(self):
        return self.connection.commit()

    def rollback(self):
        return self.connection.rollback()

    def close(self):
        return self.connection.close()

    def __getattr__(self, name):
        return getattr(self.connection, name)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    # --------------------------------------------------------
    # VERCEL
    # --------------------------------------------------------

    if IS_VERCEL:

        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL environment variable is missing on Vercel."
            )

        try:

            import psycopg2

            connection = psycopg2.connect(
                DATABASE_URL,
                sslmode="require",
                connect_timeout=10
            )

            return PostgresConnectionWrapper(
                connection
            )

        except Exception as error:

            print(
                "Neon PostgreSQL Connection Error:",
                error
            )

            raise


    # --------------------------------------------------------
    # LOCAL DEVELOPMENT
    # --------------------------------------------------------

    BASE_DIR = os.path.dirname(
        os.path.abspath(__file__)
    )

    DATABASE_NAME = os.path.join(
        BASE_DIR,
        "fraud_detection.db"
    )

    connection = sqlite3.connect(
        DATABASE_NAME,
        timeout=30
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()


    # ========================================================
    # VERCEL / NEON
    # ========================================================

    if IS_VERCEL:

        # ----------------------------------------------------
        # USERS TABLE
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)


        # ----------------------------------------------------
        # TRANSACTIONS TABLE
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                transaction_id TEXT,
                customer_name TEXT,
                amount DOUBLE PRECISION,
                prediction TEXT,
                risk_level TEXT,
                fraud_probability DOUBLE PRECISION,
                status TEXT,
                transaction_data TEXT
            )
        """)


    # ========================================================
    # LOCAL SQLITE
    # ========================================================

    else:

        # ----------------------------------------------------
        # USERS TABLE
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)


        # ----------------------------------------------------
        # TRANSACTIONS TABLE
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT,
                customer_name TEXT,
                amount REAL,
                prediction TEXT,
                risk_level TEXT,
                fraud_probability REAL,
                status TEXT,
                transaction_data TEXT
            )
        """)


    connection.commit()
    connection.close()