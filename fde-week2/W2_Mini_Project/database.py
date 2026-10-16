import os
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


# Load environment variables from .env in the same directory.
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "fde_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "admin"),
}


def get_connection():
    """
    Establish and return a connection to the PostgreSQL database.
    """
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as error:
        print(f"Error connecting to the database: {error}")
        raise


def get_dict_connection():
    """
    Establish and return a connection that gives dictionary-like rows.
    Useful for FastAPI JSON responses.
    """
    try:
        return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    except Exception as error:
        print(f"Error connecting to the database: {error}")
        raise


def test_connection():
    """
    Test database connectivity and print project table diagnostics.
    """
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user, version();")
            db_name, db_user, version = cursor.fetchone()
            print("Successfully connected to PostgreSQL database!")
            print(f"  Database : {db_name}")
            print(f"  User     : {db_user}")
            print(f"  Version  : {version.split(',')[0]}")

            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_name = 'patient_encounters'
                );
                """
            )
            patient_table_exists = cursor.fetchone()[0]

            if patient_table_exists:
                cursor.execute("SELECT COUNT(*) FROM patient_encounters;")
                count = cursor.fetchone()[0]
                print(f"  Found {count} records in 'patient_encounters' table.")
            else:
                print("  Table 'patient_encounters' does not exist yet. Run schema.sql first.")

        conn.close()
        return True
    except Exception as error:
        print(f"Connection test failed: {error}")
        return False


if __name__ == "__main__":
    test_connection()
