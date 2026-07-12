from bs4 import BeautifulSoup
import json

def parse_listings(html, source="Sulekha", default_category=None):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.flex.flex-col.rounded-none.bg-white.w-full.p-4.h-full")

    results = []
    for card in cards:
        name_tag = card.select_one("h3")
        address_tag = card.select_one("address")
        phone_tag = card.select_one("a[href^='tel:']")
        service_tags = card.select("span.bg-gray-100")

        business_name = name_tag.get_text(strip=True) if name_tag else None
        full_address = address_tag.get_text(strip=True) if address_tag else None
        phone = phone_tag.get_text(strip=True) if phone_tag else None

        # Prefer the specific service tag if present, else fall back to the page-level category
        category = service_tags[0].get_text(strip=True) if service_tags else default_category

        results.append({
            "business_name": business_name,
            "category": category,
            "address": full_address,
            "phone": phone,
            "source": source,
        })

    return results
