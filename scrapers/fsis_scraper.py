import requests
import json
import os
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.fsis.usda.gov/recalls",
}

FSIS_API_URL = "https://www.fsis.usda.gov/fsis/api/recall/v/1"
DATA_FILE = "data/fsis_response.json"


def fetch_fsis_recalls():
    """Fetch all FSIS recalls in one call"""
    response = requests.get(FSIS_API_URL, headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"First 200 chars: {response.text[:200]}")

    data = response.json()

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Fetched {len(data)} records from FSIS API")
    return data


def load_or_fetch():
    """Load from file if exists and has data, otherwise fetch"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        if data and len(data) > 0:
            print(f"Loaded {len(data)} records from {DATA_FILE}")
            return data

    print(f"{DATA_FILE} empty or missing — fetching from FSIS...")
    return fetch_fsis_recalls()


def build_label_url(record):
    label_file = record.get("field_labels", "").strip()
    recall_date = record.get("field_recall_date", "")

    if not label_file or not recall_date:
        return None

    if not label_file.endswith(".pdf"):
        label_file += ".pdf"

    yyyy_mm = recall_date[:7]
    return f"https://www.fsis.usda.gov/sites/default/files/food_label_pdf/{yyyy_mm}/{label_file}"


def parse_fsis_record(record):
    """Parse a single FSIS record into our standard format"""
    summary_html = record.get("field_summary", "")
    soup = BeautifulSoup(summary_html, "html.parser")

    # Extract announcement text
    announcement_text = soup.get_text(separator=" ", strip=True)

    # Extract product details from <li> items
    product_details = []
    for li in soup.find_all("li"):
        text = li.get_text(strip=True)
        if text:
            product_details.append(text)

    # Build label URL
    label_url = build_label_url(record)

    # Determine terminated status (field_active_notice "False" means still active)
    active = record.get("field_active_notice", "").strip()
    is_terminated = active != "False"

    return {
        "source": "FSIS",
        "announcement_title": record.get("field_title", "").strip(),
        "brand_name": None,
        "product_description": record.get("field_product_items", "").strip(),
        "product_type": None,
        "recall_reason": record.get("field_recall_reason", "").strip(),
        "company_name": record.get("field_establishment", "").strip(),
        "is_terminated": is_terminated,
        "detail_url": record.get("field_recall_url", "").strip(),
        "company_announcement_date": None,
        "fda_publish_date": None,
        "recall_date": record.get("field_recall_date", "").strip(),
        "announcement_html": summary_html,
        "announcement_text": announcement_text,
        "product_details": product_details if product_details else None,
        "photo_urls": [label_url] if label_url else [],
        "risk_level": record.get("field_risk_level", "").strip(),
        "recall_classification": record.get("field_recall_classification", "").strip(),
        "recall_number": record.get("field_recall_number", "").strip(),
        "states": record.get("field_states", "").strip(),
        "processing": record.get("field_processing", "").strip(),
        "related_to_outbreak": record.get("field_related_to_outbreak", "").strip() == "True",
    }


if __name__ == "__main__":
    records = load_or_fetch()

    results = []
    for i, record in enumerate(records):
        try:
            parsed = parse_fsis_record(record)
            results.append(parsed)
        except Exception as e:
            print(f"  ✗ Error on record {i}: {e}")
            results.append({"error": str(e), "raw_record": record})

    with open("data/fsis_all_records.json", "w") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"Done! Saved {len(results)} records to data/fsis_all_records.json")