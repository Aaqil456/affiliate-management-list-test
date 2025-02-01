import requests
import json
import os

# 🔹 **API & Google Sheets Configuration**
API_BASE_URL = "https://api.cryptocurrencyalerting.com/v1/alert-conditions"
ALERT_API = os.getenv("ALERT_API")  # Use GitHub Secrets
HEADERS = {"Content-Type": "application/json"}

# 🔹 **Google Sheets API configuration**
SHEET_ID = "1MSaFExv2AEzf3h1PB9fLEBtpla-E9uP-kDkjqpK2V-g"
GOOGLE_SHEET_API = os.getenv("GOOGLE_SHEET_API")  # Use GitHub Secrets

# 🔹 **JSON File to Store Alerts**
ALERTS_JSON_FILE = "coin_listing_alerts.json"

def fetch_exchanges_from_google_sheet():
    """ Fetch exchange names and links from a Google Sheet. """
    try:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/A1:Z1000?key={GOOGLE_SHEET_API}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            rows = data.get("values", [])

            header = rows[0]
            if "Name" not in header or "Link" not in header:
                print("⚠️ Required columns 'Name' and 'Link' not found in the sheet.")
                return {}

            name_index = header.index("Name")
            link_index = header.index("Link")

            exchange_dict = {
                row[name_index]: row[link_index]
                for row in rows[1:]
                if len(row) > name_index and len(row) > link_index
            }

            return exchange_dict
        else:
            print(f"❌ Failed to fetch Google Sheet: {response.status_code}")
            return {}

    except Exception as e:
        print(f"⚠️ Error fetching exchange data from Google Sheet: {e}")
        return {}

def fetch_coin_listing_alerts():
    """ Fetch all active new_coin alert conditions from the API. """
    try:
        url = f"{API_BASE_URL}?type=new_coin"
        response = requests.get(url, auth=(ALERT_API, ""), headers=HEADERS)

        if response.status_code == 200:
            alerts = response.json()
            return alerts if alerts else []
        else:
            print(f"❌ Failed to fetch coin listing alerts: {response.status_code}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error fetching alerts: {e}")
        return []

def filter_and_format_alerts(alerts, exchange_dict):
    """ Compare API alerts with Google Sheet exchanges & add affiliate links. """
    formatted_alerts = []

    for alert in alerts:
        exchange_name = alert.get("exchange")
        alert_id = alert.get("id")
        coin_name = alert.get("currency", "Unknown")

        if exchange_name in exchange_dict:
            formatted_alerts.append({
                "id": alert_id,
                "exchange": exchange_name,
                "coin": coin_name,
                "affiliate_url": exchange_dict[exchange_name]
            })

    return formatted_alerts

def save_alerts_to_json(alerts):
    """ Save alerts to a JSON file. """
    try:
        with open(ALERTS_JSON_FILE, "w") as file:
            json.dump(alerts, file, indent=4)
        print("✅ Alerts saved to JSON file.")
    except Exception as e:
        print(f"⚠️ Error saving alerts: {e}")

if __name__ == "__main__":
    exchange_dict = fetch_exchanges_from_google_sheet()
    alerts = fetch_coin_listing_alerts()
    matched_alerts = filter_and_format_alerts(alerts, exchange_dict)

    if matched_alerts:
        save_alerts_to_json(matched_alerts)
