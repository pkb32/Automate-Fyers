#!/usr/bin/env python
"""
NIFTY VWAP Options Strategy (REST based - stable)
Works exactly like EMA example
"""

from openalgo import api
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import os

# ================= CONFIG =================

API_KEY = os.getenv("OPENALGO_APIKEY") or "4c8cf77f82b8f0c196f09bf09e250c44f6b155f60326ea8cab5120854b9d211a"
client = api(api_key=API_KEY, host="http://127.0.0.1:5000")

STRATEGY_NAME = "NIFTY VWAP OPTIONS"

# ---- MANUAL OPTION SYMBOL (CHANGE DAILY) ----
SYMBOL = "NIFTY20JAN2625000CE"   # must exist in OpenAlgo instruments
EXCHANGE = "NFO"
PRODUCT = "MIS"
QUANTITY = 1

STOPLOSS_POINTS = 15

# ===========================================

def calculate_vwap(df):
    """
    VWAP = cumulative(price * volume) / cumulative(volume)
    """
    pv = (df["close"] * df["volume"]).cumsum()
    vol = df["volume"].cumsum()
    return pv / vol


def get_previous_day_levels():
    """
    Fetch previous day OHLC using daily candle
    """
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    resp = client.history(
        symbol=SYMBOL,
        exchange=EXCHANGE,
        interval="1d",
        start_date=start,
        end_date=end
    )

    df = ensure_dataframe(resp)
    while df.empty:
        print("DataFrame empty while fetching previous day levels. Retrying...")
        time.sleep(5)
        continue

    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)

    prev = df.iloc[-2]
    return prev["high"], prev["low"], prev["close"]


def vwap_strategy():
    position_open = False
    entry_price = None
    stoploss = None

    print(f"🚀 Starting {STRATEGY_NAME}")

    # ---- PREVIOUS DAY LEVELS ----
    pdh, pdl, pdc = get_previous_day_levels()
    print(f"📌 Prev Day → High={pdh} Low={pdl} Close={pdc}")

    while True:
        try:
            now = datetime.now()

            # ---- MARKET TIME CHECK ----
            if now.time() < datetime.strptime("09:15", "%H:%M").time():
                time.sleep(30)
                continue

            # ---- AUTO EXIT @ 3:10 ----
            if now.time() >= datetime.strptime("15:10", "%H:%M").time():
                if position_open:
                    client.placesmartorder(
                        strategy=STRATEGY_NAME,
                        symbol=SYMBOL,
                        exchange=EXCHANGE,
                        action="SELL",
                        price_type="MARKET",
                        product=PRODUCT,
                        quantity=QUANTITY,
                        position_size=0
                    )
                    print("⏰ EOD EXIT DONE")
                break

            # ---- FETCH 5 MIN DATA ----
            end = now.strftime("%Y-%m-%d")
            start = (now - timedelta(days=1)).strftime("%Y-%m-%d")

            df = client.history(
                symbol=SYMBOL,
                exchange=EXCHANGE,
                interval="5m",
                start_date=start,
                end_date=end
            )

            if df.empty or "volume" not in df.columns:
                time.sleep(30)
                continue

            df["vwap"] = calculate_vwap(df)

            last = df.iloc[-2]   # completed candle
            close = last["close"]
            vwap = last["vwap"]

            print(
                f"LTP={df['close'].iloc[-1]} | "
                f"5m Close={close} | VWAP={round(vwap,2)}"
            )

            # ================= ENTRY =================
            if not position_open:
                if (
                    close > vwap
                    or close > pdl
                    or close > pdc
                ):
                    entry_price = close
                    stoploss = entry_price - STOPLOSS_POINTS

                    client.placesmartorder(
                        strategy=STRATEGY_NAME,
                        symbol=SYMBOL,
                        exchange=EXCHANGE,
                        action="BUY",
                        price_type="MARKET",
                        product=PRODUCT,
                        quantity=QUANTITY,
                        position_size=QUANTITY
                    )

                    position_open = True
                    print(f"🟢 BUY @ {entry_price} SL={stoploss}")

            # ================= STOPLOSS =================
            if position_open:
                ltp = df["close"].iloc[-1]
                if ltp <= stoploss:
                    client.placesmartorder(
                        strategy=STRATEGY_NAME,
                        symbol=SYMBOL,
                        exchange=EXCHANGE,
                        action="SELL",
                        price_type="MARKET",
                        product=PRODUCT,
                        quantity=QUANTITY,
                        position_size=0
                    )

                    print(f"🔴 SL HIT @ {ltp}")
                    position_open = False
                    entry_price = None
                    stoploss = None

            time.sleep(30)

        except Exception as e:
            print("❌ Error:", e)
            time.sleep(30)
def ensure_dataframe(resp):
    """
    Convert OpenAlgo history response to DataFrame safely
    """
    if isinstance(resp, dict):
        if "data" in resp:
            return pd.DataFrame(resp["data"])
        else:
            raise ValueError("History response missing 'data'")
    return resp



if __name__ == "__main__":
    vwap_strategy()
