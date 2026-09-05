import sqlite3
from datetime import datetime

import requests
import os
from dotenv import load_dotenv


load_dotenv()
base_url = "https://api.twelvedata.com/time_series?"


API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY is missing.")



def get_market_data(pair, interval):
    url =f"{base_url}symbol={pair}&interval={interval}&apikey={API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Request failed with status code {response.status_code}")

    data = response.json()
    if "values" not in data:
        raise Exception("No values found in response")
    
    return data
    


def transform_market_data(data, pair, interval):
    candle_list = []
    for candle in data["values"]:
        new_candle = {"pair": pair, "interval": interval, **candle}
        new_candle["datetime"] = datetime.strptime(new_candle["datetime"], "%Y-%m-%d %H:%M:%S")
        new_candle["open"] = float(new_candle["open"])
        new_candle["high"] = float(new_candle["high"])
        new_candle["low"] = float(new_candle["low"])
        new_candle["close"] = float(new_candle["close"])
        candle_list.append(new_candle)
    print(f"candles received : {len(candle_list)}")
        
    return candle_list

def create_table():
    conn = sqlite3.connect("market_data.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair TEXT NOT NULL,
            interval TEXT NOT NULL,
            datetime DATETIME NOT NULL,
            open DECIMAL(10, 5) NOT NULL,
            high DECIMAL(10, 5) NOT NULL,
            low DECIMAL(10, 5) NOT NULL,
            close DECIMAL(10, 5) NOT NULL,
            UNIQUE(pair, interval, datetime)
        )
    """)

    conn.commit()
    conn.close()

def load_market_data(candles):
   
    conn = sqlite3.connect("market_data.db")
    cursor = conn.cursor()

    inserted = 0
    

    try:
        for candle in candles:
            '''
            if candle["datetime"] == "2026-01-01 03:00:00":
                raise sqlite3.Error("Simulated database failure")
                '''
            cursor.execute("""
                INSERT OR IGNORE INTO candles (pair, interval, datetime, open, high, low, close)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (candle["pair"], candle["interval"], candle["datetime"].strftime("%Y-%m-%d %H:%M:%S"), candle["open"], candle["high"], candle["low"], candle["close"]))

            if cursor.rowcount == 1:
                inserted += 1
            

        conn.commit()
        
        print(f"Inserted: {inserted}")
        
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_latest_datetime(pair, interval):
    conn = sqlite3.connect("market_data.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT MAX(datetime) FROM candles WHERE pair = ? AND interval = ?
    """, (pair, interval))

    result = cursor.fetchone()
    conn.close()

    return datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S") if result[0] else None

def filter_new_candles(candles, latest_datetime):
    if latest_datetime is None:
        return candles

    new_candles = []

    for candle in candles:
        if candle["datetime"] > latest_datetime:
            new_candles.append(candle)
    print(f"candles received for filtering: {len(candles)}")        
    print(f"New candles to insert: {len(new_candles)}")
    print(f"Already ingested: {len(candles) - len(new_candles)}")
    return new_candles

def validate_market_data(candles):
    valid_candles = []
    invalid_candles = []
    for candle in candles:
        if not all(key in candle for key in ["pair", "interval", "datetime", "open", "high", "low", "close"]):
           
            invalid_candles.append((candle, {"reason": "Missing required fields"}))
            continue
        if not isinstance(candle["datetime"], datetime):

            invalid_candles.append((candle, {"reason": "Invalid datetime format"}))
            continue
        if not all(isinstance(candle[key], (int, float)) for key in ["open", "high", "low", "close"]):
            invalid_candles.append((candle, {"reason": "Invalid price format"}))
            continue
        if any(candle[key] <= 0 for key in ["open", "high", "low", "close"]):
                    invalid_candles.append((candle, {"reason": "Negative prices"}))
                    continue
        if candle["high"] < candle["low"]:
            invalid_candles.append((candle, {"reason": "High price is less than low price"}))
            continue
        if candle["open"] < candle["low"] or candle["open"] > candle["high"]:
            invalid_candles.append((candle, {"reason": "Open price is out of range"}))
            continue
        if candle["close"] < candle["low"] or candle["close"] > candle["high"]:
            invalid_candles.append((candle, {"reason": "Close price is out of range"}))
            continue
        
        valid_candles.append(candle)

    return valid_candles, invalid_candles




create_table()

data = get_market_data("EUR/USD", "1h")

candles = transform_market_data(
    data,
    "EUR/USD",
    "1h"
)
valid_candles, invalid_candles = validate_market_data(candles)
print(f"Valid candles: {len(valid_candles)}")
print(f"Invalid candles: {len(invalid_candles)}")

for candle, error in invalid_candles:
    print(error["reason"], candle)

filtered_candles = filter_new_candles(
    valid_candles,
    get_latest_datetime("EUR/USD", "1h")
)

load_market_data(filtered_candles)


