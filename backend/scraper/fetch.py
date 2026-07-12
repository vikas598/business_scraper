import requests
import time
import random
import os

BASE_URL = "https://www.sulekha.com/packers-and-movers/{}/page-{}"
CITIES = ["mumbai", "delhi", "chennai", "bangalore", "pune", "kolkata"]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def fetch_page(city, page_num, max_retries=2, delay=1.5):
    url = BASE_URL.format(city, page_num)

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)

            if response.history and page_num != 1:
                print(f"Page {page_num} redirected (attempt {attempt}) — retrying...")
                if attempt < max_retries:
                    time.sleep(2 ** attempt + random.uniform(0, 1))
                    continue
                else:
                    return None  # genuinely gave up after retries

            response.raise_for_status()
            time.sleep(delay + random.uniform(0, 0.5))
            return response.text

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt} failed for page {page_num}: {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                return None

    return None
