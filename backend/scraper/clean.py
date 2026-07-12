import re
import json

def extract_city(address):
    """
    Extracts the city from an address string.
    Handles formats like:
      - "Mumbai, 400002"                    -> "Mumbai"
      - "Andheri East, Mumbai, 400072"       -> "Mumbai"
      - "Mumbai" (no comma at all)           -> "Mumbai"
    Anchors on the pincode being the LAST comma-separated piece,
    so the city is reliably the piece just before it.
    """
    if not address:
        return None

    parts = [p.strip() for p in address.split(",") if p.strip()]

    if len(parts) >= 2:
        return parts[-2]
    elif len(parts) == 1:
        return parts[0]

    return None


def clean_record(raw):
    business_name = (raw.get("business_name") or "").strip()
    category = (raw.get("category") or "").strip()
    address = (raw.get("address") or "").strip()
    match = re.search(r'\b\d{6}\b', raw.get("address"))
    pincode = match.group() if match else None
    phone = (raw.get("phone") or "").strip()
    source = (raw.get("source") or "").strip()

    # --- Extract city from address ---
    city = extract_city(address)

    # --- Required field validation ---
    if not business_name or not category or not city:
        return None  # drop this record entirely

    # --- Reasonable length sanity check (catches parsing bugs) ---
    if len(business_name) > 200 or len(category) > 200:
        return None

    # --- Phone normalization ---
    if phone:
        digits_only = re.sub(r"\D", "", phone)  # strip everything except digits

        # Strip a leading '91' country code if present (e.g. "919021117668" -> "9021117668")
        if len(digits_only) == 12 and digits_only.startswith("91"):
            digits_only = digits_only[2:]

        # Strip a single leading '0' STD/trunk prefix (e.g. "09021117668" -> "9021117668")
        if len(digits_only) == 11 and digits_only.startswith("0"):
            digits_only = digits_only[1:]

        if len(digits_only) == 10:
            phone = digits_only
        else:
            phone = None  # doesn't match expected Indian mobile number length after cleanup
    else:
        phone = None

    return {
        "business_name": business_name,
        "category": category,
        "city": city,
        "address": address,
        "pincode": pincode,
        "phone": phone,
        "source": source,
    }


def clean_records(raw_records):
    cleaned = []
    dropped = 0
    for raw in raw_records:
        result = clean_record(raw)
        if result:
            cleaned.append(result)
        else:
            dropped += 1
    print(f"Cleaned {len(cleaned)} records, dropped {dropped} invalid records")
    return cleaned

# def clean_records(raw_records): #debug
#     cleaned = []
#     dropped_samples = []

#     for raw in raw_records:
#         result = clean_record(raw)
#         if result:
#             cleaned.append(result)
#         else:
#             dropped_samples.append(raw)

#     print(f"Cleaned {len(cleaned)}, dropped {len(dropped_samples)}")
#     print("\n--- Sample of dropped raw records ---")
#     for r in dropped_samples[:10]:
#         print(r)

#     return cleaned