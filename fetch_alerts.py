import requests
import json
import os
import re
from datetime import datetime, timedelta

# Google Sheets API Configuration
SHEET_ID = "1MSaFExv2AEzf3h1PB9fLEBtpla-E9uP-kDkjqpK2V-g"
GOOGLE_SHEET_API = os.getenv("GOOGLE_SHEET_API")

# Slack API Configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

# JSON File to Store Alerts
ALERTS_JSON_FILE = "coin_listing_alerts.json"


def fetch_existing_alerts():
    """ Load existing alerts from JSON and remove outdated ones (older than 3 days). """
    try:
        if os.path.exists(ALERTS_JSON_FILE):
            with open(ALERTS_JSON_FILE, "r") as file:
                alerts = json.load(file)
                
            # Filter out old alerts (older than 3 days)
            three_days_ago = datetime.utcnow() - timedelta(days=3)
            fresh_alerts = [alert for alert in alerts if datetime.strptime(alert["date_added"], "%Y-%m-%d") >= three_days_ago]

            return fresh_alerts
        else:
            return []
    except Exception as e:
        print(f"Error loading existing alerts: {e}")
        return []


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

            return {row[name_index]: row[link_index] for row in rows[1:] if len(row) > max(name_index, link_index)}
        else:
            print(f"Failed to fetch Google Sheet: {response.status_code}")
            return {}

    except Exception as e:
        print(f"Error fetching exchange data from Google Sheet: {e}")
        return {}


def fetch_slack_alerts():
    """ Fetch latest messages from a Slack channel using Slack API. """
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        print("SLACK_BOT_TOKEN or SLACK_CHANNEL_ID is missing!")
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
            messages = [msg.get("text", "") for msg in data.get("messages", []) if "text" in msg]
            return messages
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
        cleaned_msg = re.sub(r"<[^|>]+\|([^>]+)>", r"\1", msg)
        match = re.search(r"(.+?) \((.+?)\) .* listed on (.+?) -", cleaned_msg)

        if match:
            extracted_data.append({
                "coin": match.group(1).strip(),
                "ticker": match.group(2).strip(),
                "exchange": match.group(3).strip(),
                "date_added": datetime.utcnow().strftime("%Y-%m-%d")  # Add timestamp
            })

    return extracted_data


def filter_and_format_alerts(alerts, exchange_dict, existing_alerts):
    """ Compare alerts with Google Sheet exchanges, avoid duplicates & add affiliate links. """
    formatted_alerts = []
    existing_entries = {(alert["coin"], alert["ticker"], alert["exchange"]) for alert in existing_alerts}

    for alert in alerts:
        exchange_name = alert.get("exchange")
        coin_name = alert.get("coin")
        ticker = alert.get("ticker")

        if exchange_name in exchange_dict and (coin_name, ticker, exchange_name) not in existing_entries:
            formatted_alerts.append({
                "exchange": exchange_name,
                "coin": coin_name,
                "ticker": ticker,
                "affiliate_url": exchange_dict[exchange_name],
                "date_added": alert["date_added"]
            })

    return formatted_alerts


def save_alerts_to_json(alerts):
    """ Save alerts to a JSON file, sorted by newest first. """
    try:
        # Sort alerts by 'date_added' (newest first)
        alerts.sort(key=lambda x: datetime.strptime(x["date_added"], "%Y-%m-%d"), reverse=True)

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
                print("\nFiltering alerts...")
                existing_alerts = fetch_existing_alerts()
                matched_alerts = filter_and_format_alerts(extracted_alerts, exchange_dict, existing_alerts)

                if matched_alerts:
                    # Combine new and existing alerts
                    final_alerts = existing_alerts + matched_alerts

                    # Sort the final list from newest to oldest
                    save_alerts_to_json(final_alerts)

                    print("\n✅ Updated Alerts (Sorted by Newest First):")
                    for alert in final_alerts:
                        print(f"- {alert['coin']} ({alert['ticker']}) on {alert['exchange']} ✅")
                else:
                    print("No new alerts matched or all were duplicates.")
            else:
                print("No coin listing data extracted.")
        else:
            print("No new messages from Slack.")
    else:
        print("No exchanges found in Google Sheet.")
