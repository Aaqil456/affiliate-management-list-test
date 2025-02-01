import requests
import json
import os
import re

# 🔹 **API & Google Sheets Configuration**
API_BASE_URL = "https://api.cryptocurrencyalerting.com/v1/alert-conditions"
ALERT_API = os.getenv("ALERT_API")  # GitHub Secret for API Token
HEADERS = {"Content-Type": "application/json"}

# 🔹 **Google Sheets API configuration**
SHEET_ID = "1MSaFExv2AEzf3h1PB9fLEBtpla-E9uP-kDkjqpK2V-g"
GOOGLE_SHEET_API = os.getenv("GOOGLE_SHEET_API")  # GitHub Secret for Google API Key

# 🔹 **Discord Webhook Configuration**
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")  # GitHub Secret for Discord Webhook

# 🔹 **JSON File to Store Alerts**
ALERTS_JSON_FILE = "coin_listing_alerts.json"

def fetch_exchanges_from_google_sheet():
    """ Fetch exchange names and affiliate links from a Google Sheet. """
    try:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/A1:Z1000?key={GOOGLE_SHEET_API}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            rows = data.get("values", [])

            if not rows:
                print("⚠️ No data found in Google Sheet.")
                return {}

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

def fetch_discord_alerts():
    """ Fetch latest alerts from Discord Webhook. """
    try:
        response = requests.get(DISCORD_WEBHOOK_URL)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to fetch messages from Discord: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error fetching Discord messages: {e}")
        return []

def extract_coin_listing_data(messages):
    """ Parses alert messages to extract coin listing details. """
    extracted_data = []

    for msg in messages:
        match = re.search(r"(.+?) \((.+?)\) .* listed on (.+?) \(", msg)
        if match:
            coin_name = match.group(1)
            ticker = match.group(2)
            exchange = match.group(3)
            extracted_data.append({
                "coin": coin_name,
                "ticker": ticker,
                "exchange": exchange,
                "alert_message": msg
            })

    return extracted_data

def filter_and_format_alerts(alerts, exchange_dict):
    """ Compare alerts with Google Sheet exchanges & add affiliate links. """
    formatted_alerts = []

    for alert in alerts:
        exchange_name = alert.get("exchange")
        coin_name = alert.get("coin")
        ticker = alert.get("ticker")

        if exchange_name in exchange_dict:
            formatted_alerts.append({
                "exchange": exchange_name,
                "coin": coin_name,
                "ticker": ticker,
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
    print("📡 Fetching exchange data from Google Sheet...")
    exchange_dict = fetch_exchanges_from_google_sheet()

    if exchange_dict:
        print(f"✅ Found {len(exchange_dict)} exchanges from Google Sheet.")

        print("📡 Fetching latest Discord alerts...")
        messages = fetch_discord_alerts()

        if messages:
            extracted_alerts = extract_coin_listing_data(messages)

            if extracted_alerts:
                matched_alerts = filter_and_format_alerts(extracted_alerts, exchange_dict)

                if matched_alerts:
                    save_alerts_to_json(matched_alerts)
                else:
                    print("⚠️ No alerts matched the exchanges from Google Sheet.")
            else:
                print("⚠️ No coin listing data extracted.")
        else:
            print("⚠️ No new messages from Discord.")
    else:
        print("⚠️ No exchanges found in Google Sheet.")
