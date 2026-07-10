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