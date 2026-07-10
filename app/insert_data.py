import json
from db import get_connection

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


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def bulk_insert(records):
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
        print(f"\nInsert complete. Success: {inserted}, Failed: {failed}")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    records = load_json("scraper/listings_test500.json")
    print(f"Loaded {len(records)} records from file")
    bulk_insert(records)