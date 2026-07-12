import json

def normalize_key(value):
    """
    Normalizes a string for use as a dedup key:
    lowercase, strip whitespace, collapse internal whitespace,
    remove common punctuation that doesn't affect identity.
    """
    if not value:
        return ""
    value = value.lower().strip()
    value = " ".join(value.split())  # collapse multiple spaces into one
    value = value.replace(".", "").replace(",", "").replace("&", "and")
    return value


def dedupe_records(records):
    seen = set()
    unique = []
    duplicates = []

    for record in records:
        key = (
            normalize_key(record["business_name"]),
            normalize_key(record["city"]),
        )

        if key in seen:
            duplicates.append(key)
            continue

        seen.add(key)
        unique.append(record)
    print("\n duplicates dropped are \n")
    for dup in duplicates:
        print(dup)
    print(f"Kept {len(unique)} unique records, removed {len(duplicates)} duplicates")
    return unique
