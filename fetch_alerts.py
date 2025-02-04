import requests
import json
import os
import re

# Google Sheets API Configuration
SHEET_ID = "1MSaFExv2AEzf3h1PB9fLEBtpla-E9uP-kDkjqpK2V-g"
GOOGLE_SHEET_API = os.getenv("GOOGLE_SHEET_API")  # GitHub Secret for Google API Key

# Slack API Configuration (Replaced Webhook with Bot Token & Channel ID)
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")  # Slack Bot Token (xoxb-...)
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")  # Slack Channel ID

# JSON File to Store Alerts
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
                print("No data found in Google Sheet.")
                return {}

            header = rows[0]
            if "Name" not in header or "Link" not in header:
                print("Required columns 'Name' and 'Link' not found in the sheet.")
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
            print(f"Failed to fetch Google Sheet: {response.status_code}")
            return {}

    except Exception as e:
        print(f"Error fetching exchange data from Google Sheet: {e}")
        return {}


def fetch_slack_alerts():
    """ Fetch latest messages from a Slack channel using Slack API. """
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        print("SLACK_BOT_TOKEN or SLACK_CHANNEL_ID is missing! Check your environment variables.")
        return []

    url = "https://slack.com/api/conversations.history"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    params = {
        "channel": SLACK_CHANNEL_ID,
        "limit": 10  # Fetch the last 10 messages
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if response.status_code == 200 and data.get("ok"):
            return [msg.get("text", "") for msg in data.get("messages", []) if "text" in msg]
        else:
            print(f"Error fetching messages: {data.get('error')}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Slack messages: {e}")
        return []


def extract_coin_listing_data(messages):
    """ Parses alert messages to extract coin listing details. """
    extracted_data = []

    for msg in messages:
        match = re.search(r"(.+?) \((.+?)\) .* listed on (.+?) -", msg)
        if match:
            extracted_data.append({
                "coin": match.group(1),
                "ticker": match.group(2),
                "exchange": match.group(3),
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
        print("Alerts saved to JSON file.")
    except Exception as e:
        print(f"Error saving alerts: {e}")


if __name__ == "__main__":
    print("Fetching exchange data from Google Sheet...")
    exchange_dict = fetch_exchanges_from_google_sheet()

    if exchange_dict:
        print(f"Found {len(exchange_dict)} exchanges from Google Sheet.")

        print("Fetching latest Slack alerts...")
        messages = fetch_slack_alerts()

        if messages:
            extracted_alerts = extract_coin_listing_data(messages)

            if extracted_alerts:
                matched_alerts = filter_and_format_alerts(extracted_alerts, exchange_dict)

                if matched_alerts:
                    save_alerts_to_json(matched_alerts)
                else:
                    print("No alerts matched the exchanges from Google Sheet.")
            else:
                print("No coin listing data extracted.")
        else:
            print("No new messages from Slack.")
    else:
        print("No exchanges found in Google Sheet.")
