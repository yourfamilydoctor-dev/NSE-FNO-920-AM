import requests
import pandas as pd
import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==============================
# GOOGLE SHEETS LOGIN
# ==============================

creds_json = os.environ.get("GCP_CREDENTIALS")

if not creds_json:
    print("Missing credentials")
    exit()

creds_dict = json.loads(creds_json)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict,
    scope
)

client = gspread.authorize(creds)

# PUT YOUR GOOGLE SHEET ID HERE
spreadsheet_id = "1-DEnDQufP_SU52ZhEJ7GBQ9NReIq2uEgmEPzv1KtoKw"

sheet_live = client.open_by_key(spreadsheet_id).worksheet("LIVE_FNO")
sheet_market = client.open_by_key(spreadsheet_id).worksheet("MARKET_STATUS")

# ==============================
# NSE SESSION
# ==============================

session = requests.Session()

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br"
}

import time

# ==============================
# CREATE NSE SESSION
# ==============================

session = requests.Session()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "application/json,text/html",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive"
}

# FIRST HIT HOMEPAGE
homepage = session.get(
    "https://www.nseindia.com",
    headers=headers,
    timeout=10
)

print("Homepage status:", homepage.status_code)

# WAIT 3 SECONDS
time.sleep(3)

# NOW FETCH API
fno_url = "https://www.nseindia.com/api/live-analysis-oi-spurts-underlyings"

response = session.get(
    fno_url,
    headers=headers,
    timeout=10
)

print("API status:", response.status_code)

# DEBUG RESPONSE
print(response.text[:500])

# CHECK VALID RESPONSE
if response.status_code != 200:
    print("NSE API FAILED")
    exit()

try:
    data = response.json()

except Exception as e:
    print("JSON ERROR")
    print(e)
    print(response.text[:1000])
    exit()

stocks = []

for item in data["data"]:

    try:

        symbol = item["symbol"]

        pchange = float(item["pChange"])

        oi_change = float(item["oiChangePct"])

        last_price = item["ltP"]

        prev_close = 0

        signal = ""

        if pchange >= 2 and oi_change >= 7:

            signal = "BULLISH"

            stocks.append([
                symbol,
                last_price,
                prev_close,
                round(pchange, 2),
                round(oi_change, 2),
                signal
            ])

    except Exception as e:
        print(e)

    try:
        meta = item["metadata"]

        symbol = meta["symbol"]

        last_price = float(meta["lastPrice"])

        prev_close = float(meta["previousClose"])

        pchange = ((last_price - prev_close) / prev_close) * 100

        # Dummy OI change logic
        # Replace later with actual option chain OI API
        oi_change = float(meta.get("pChange", 0))

        signal = ""

        if pchange >= 2 and oi_change >= 7:
            signal = "BULLISH"

            stocks.append([
                symbol,
                last_price,
                prev_close,
                round(pchange, 2),
                round(oi_change, 2),
                signal
            ])

    except:
        pass

# ==============================
# UPDATE GOOGLE SHEET
# ==============================

sheet_live.batch_clear(["A2:F500"])

if stocks:
    sheet_live.update("A2", stocks)

# ==============================
# MARKET BREADTH
# ==============================

breadth_url = "https://www.nseindia.com/api/allIndices"

breadth_response = session.get(
    breadth_url,
    headers=headers
)

breadth_data = breadth_response.json()

adv = 0
dec = 0

for idx in breadth_data["data"]:

    if "advances" in idx and "declines" in idx:

        adv += idx["advances"]
        dec += idx["declines"]

market_trend = ""

if adv > dec:
    market_trend = "BULLISH DAY"

elif dec > adv:
    market_trend = "BEARISH DAY"

else:
    market_trend = "SIDEWAYS"

sheet_market.update("B1", [[adv]])
sheet_market.update("B2", [[dec]])
sheet_market.update("B3", [[market_trend]])

print("SUCCESS")
for i in range(3):

    try:

        response = session.get(
            fno_url,
            headers=headers,
            timeout=10
        )

        data = response.json()

        break

    except Exception as e:

        print("Retry:", i)

        time.sleep(5)
