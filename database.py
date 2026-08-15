import os
import sqlite3


# ============================================================
# DATABASE PATH
# ============================================================

# Vercel filesystem is read-only except /tmp
if os.environ.get("VERCEL"):
    DATABASE_NAME = "/tmp/fraud_detection.db"
else:
    BASE_DIR = os.path.dirname(
        os.path.abspath(__file__)
    )

    DATABASE_NAME = os.path.join(
        BASE_DIR,
        "fraud_detection.db"
    )


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
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

    # --------------------------------------------------------
    # USERS TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # TRANSACTIONS TABLE
    # --------------------------------------------------------

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