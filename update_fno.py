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

session.get("https://www.nseindia.com", headers=headers)

# ==============================
# FETCH FNO STOCK LIST
# ==============================

fno_url = "https://www.nseindia.com/api/market-data-pre-open?key=FO"

response = session.get(fno_url, headers=headers)

data = response.json()

stocks = []

for item in data["data"]:

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
