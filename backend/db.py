import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()  # reads .env file into environment variables

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}


def get_connection():
    """
    Creates and returns a new MySQL connection.
    Caller is responsible for closing it (or use get_cursor() context manager below).
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection failed: {e}")
        raise


INSERT_QUERY = """
    INSERT INTO listing_master
        (business_name, category, city, address, pincode, phone, source)
    VALUES
        (%(business_name)s, %(category)s, %(city)s, %(address)s, %(pincode)s, %(phone)s, %(source)s)
    ON DUPLICATE KEY UPDATE
        address = VALUES(address),
        pincode = VALUES(pincode),
        phone = VALUES(phone)
"""


def insert_listings(records):
    """
    records: list of dicts with keys matching listing_master columns.
    Returns (inserted_count, failed_count).
    """
    conn = get_connection()
    cursor = conn.cursor()

    inserted = 0
    failed = 0

    try:
        for record in records:
            try:
                cursor.execute(INSERT_QUERY, record)
                inserted += 1
            except Exception as e:
                print(f"Failed to insert {record.get('business_name')}: {e}")
                failed += 1

        conn.commit()
    finally:
        cursor.close()
        conn.close()

    return inserted, failed


def get_counts_by(column):
    """
    Returns count of listings grouped by the given column.
    column must be one of a known safe set — never pass user input directly here.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)  # returns rows as dicts, not tuples

    query = f"SELECT {column} AS label, COUNT(*) AS count FROM listing_master GROUP BY {column} ORDER BY count DESC"

    try:
        cursor.execute(query)
        results = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return results

def get_all_listings():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT id, business_name, category, city, address, pincode, phone, source, created_at
        FROM listing_master
        ORDER BY id ASC
    """

    try:
        cursor.execute(query)
        results = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return results

if __name__ == "__main__":
    conn = get_connection()
    if conn.is_connected():
        print("Connected to MySQL successfully!")
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        result = cursor.fetchone()
        print(f"Connected to database: {result[0]}")
        cursor.close()
    conn.close()