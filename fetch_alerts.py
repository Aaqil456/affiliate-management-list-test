import discord
import asyncio
import os
import re
import json
import requests  # ✅ Ensure requests module is imported

# 🔹 **Bot Configuration**
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Get bot token from GitHub Secrets
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))  # Get Discord Channel ID from GitHub Secrets

# 🔹 **Google Sheets API Configuration**
SHEET_ID = "1MSaFExv2AEzf3h1PB9fLEBtpla-E9uP-kDkjqpK2V-g"
GOOGLE_SHEET_API = os.getenv("GOOGLE_SHEET_API")  # GitHub Secret for Google API Key

# 🔹 **JSON File to Store Alerts**
ALERTS_JSON_FILE = "coin_listing_alerts.json"

# ✅ Initialize Discord Client with INTENTS to READ MESSAGES
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True  # ✅ REQUIRED to read messages
client = discord.Client(intents=intents)

async def fetch_messages():
    """ Fetch latest messages from Discord channel """
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print("❌ ERROR: Bot CANNOT find the channel. Check DISCORD_CHANNEL_ID!")
        await client.close()
        return

    print(f"✅ Bot found channel: {channel.name} ({CHANNEL_ID})")
    
    messages = []
    async for message in channel.history(limit=10):  # Fetch last 10 messages
        print(f"🔹 [DEBUG] Found Message: {message.content} (by {message.author})")  # Debugging
        messages.append(message.content)

    if not messages:
        print("⚠️ ERROR: Bot **can access the channel but NO messages retrieved!** Check bot permissions.")

    # ✅ Extract Coin Listings
    extracted_alerts = extract_coin_listing_data(messages)
    
    # ✅ Fetch exchanges from Google Sheets
    exchange_dict = fetch_exchanges_from_google_sheet()

    # ✅ Filter & Format Alerts
    if extracted_alerts and exchange_dict:
        matched_alerts = filter_and_format_alerts(extracted_alerts, exchange_dict)

        if matched_alerts:
            save_alerts_to_json(matched_alerts)
        else:
            print("⚠️ No alerts matched the exchanges from Google Sheet.")

    print("✅ Messages processed. Shutting down bot.")
    await client.close()  # Stop the bot after fetching messages

def fetch_exchanges_from_google_sheet():
    """ Fetch exchange names and affiliate links from a Google Sheet. """
    try:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/A1:Z1000?key={GOOGLE_SHEET_API}"
        response = requests.get(url)  # ✅ Ensure requests is used correctly

        if response.status_code == 200:
            data = response.json()
            rows = data.get("values", [])

            if not rows:
                print("⚠️ No data found in Google Sheet.")
                return {}

            header = rows[0]
            if "Name" not in header or "Link" not in header:
                print("⚠️ ERROR: Google Sheet **missing required columns** 'Name' & 'Link'.")
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
            print(f"❌ ERROR: Failed to fetch Google Sheet - Status Code: {response.status_code}")
            return {}

    except Exception as e:
        print(f"⚠️ ERROR: Failed to fetch exchange data from Google Sheet: {e}")
        return {}

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
        print("✅ Alerts saved to JSON file.")
    except Exception as e:
        print(f"⚠️ ERROR: Failed to save alerts: {e}")

@client.event
async def on_ready():
    print(f"🚀 Bot logged in as {client.user}")
    await fetch_messages()

client.run(TOKEN)
