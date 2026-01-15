#!/usr/bin/env python
"""
NIFTY VWAP OPTIONS STRATEGY (STABLE, REST-BASED)

Uses:
- client.history()
- ta.vwap()
- client.placesmartorder()

Works exactly like EMA example
"""

from openalgo import api, ta
import pandas as pd
import time
from datetime import datetime, timedelta
import os

# ================= CONFIG =================

API_KEY = os.getenv("OPENALGO_APIKEY") or "4c8cf77f82b8f0c196f09bf09e250c44f6b155f60326ea8cab5120854b9d211a"
client = api(api_key=API_KEY, host="http://127.0.0.1:5000")

STRATEGY = "NIFTY_VWAP_OPTIONS"

# 🔴 CHANGE DAILY (must exist in OpenAlgo instruments)
SYMBOL = "NIFTY20JAN2625400CE"
EXCHANGE = "NFO"
PRODUCT = "MIS"
QTY = 1

STOPLOSS_POINTS = 15

# =========================================


def ensure_df(resp):
    if isinstance(resp, dict):
        return pd.DataFrame(resp.get("data", []))
    return resp


def get_previous_day_levels():
    """
    Fetch previous day High / Low / Close from NIFTY index
    """
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    df = ensure_df(
        client.history(
            symbol="NIFTY",
            exchange="NSE_INDEX",
            interval="5m",
            start_date=start,
            end_date=end
        )
    )

    if df.empty or len(df) < 1:
        raise Exception("No previous day NIFTY data")

    prev = df.iloc[-1]
    return float(prev["high"]), float(prev["low"]), float(prev["close"])


def vwap_strategy():
    position = False
    entry = None
    sl = None

    print("🚀 Starting NIFTY VWAP OPTIONS")

    pdh, pdl, pdc = get_previous_day_levels()
    print(f"📌 Prev Day → High={pdh} Low={pdl} Close={pdc}")

    while True:
        try:
            now = datetime.now()

            # ===== MARKET HOURS =====
            if now.time() < datetime.strptime("09:15", "%H:%M").time():
                time.sleep(30)
                continue

            # ===== EOD EXIT =====
            if now.time() >= datetime.strptime("15:10", "%H:%M").time():
                if position:
                    client.placesmartorder(
                        strategy=STRATEGY,
                        symbol=SYMBOL,
                        exchange=EXCHANGE,
                        action="SELL",
                        price_type="MARKET",
                        product=PRODUCT,
                        quantity=QTY,
                        position_size=0
                    )
                    print("⏰ EOD EXIT")
                break

            # ===== FETCH 5m DATA =====
            start = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            end = now.strftime("%Y-%m-%d")

            df = ensure_df(
                client.history(
                    symbol=SYMBOL,
                    exchange=EXCHANGE,
                    interval="5m",
                    start_date=start,
                    end_date=end
                )
            )

            if df.empty or "volume" not in df.columns:
                time.sleep(30)
                continue

            # ===== VWAP USING openalgo.ta =====
            vwap_series = ta.vwap(
                high=df["high"],
                low=df["low"],
                close=df["close"],
                volume=df["volume"]
            )

            df["vwap"] = vwap_series

            candle = df.iloc[-2]   # completed candle
            close = float(candle["close"])
            vwap = float(candle["vwap"])
            ltp = float(df.iloc[-1]["close"])

            print(f"LTP={ltp} | 5m Close={close} | VWAP={round(vwap,2)}")

            # ===== ENTRY =====
            if not position:
                if close > vwap or close > pdl or close > pdc:
                    entry = close
                    sl = entry - STOPLOSS_POINTS

                    client.placeorder(
                        strategy=STRATEGY,
                        symbol=SYMBOL,
                        exchange=EXCHANGE,
                        action="BUY",
                        price_type="MARKET",
                        product=PRODUCT,
                        quantity=QTY,
                        position_size=QTY
                    )

                    position = True
                    print(f"🟢 BUY @ {entry} SL={sl}")

            # ===== STOPLOSS =====
            if position and ltp <= sl:
                client.placeorder(
                    strategy=STRATEGY,
                    symbol=SYMBOL,
                    exchange=EXCHANGE,
                    action="SELL",
                    price_type="MARKET",
                    product=PRODUCT,
                    quantity=QTY,
                    position_size=0
                )

                print(f"🔴 SL HIT @ {ltp}")
                position = False
                entry = None
                sl = None

            time.sleep(30)

        except Exception as e:
            print("❌ Error:", e)
            time.sleep(30)


if __name__ == "__main__":
    vwap_strategy()




# #!/usr/bin/env python
# """
# NIFTY VWAP OPTIONS STRATEGY (REST ONLY - STABLE)

# • Uses OpenAlgo history() only
# • VWAP read directly from candle data
# • Same execution model as EMA strategy
# """

# from openalgo import api
# import pandas as pd
# import time
# from datetime import datetime, timedelta
# import os

# # ================= CONFIG =================

# API_KEY = os.getenv("OPENALGO_APIKEY") or "4c8cf77f82b8f0c196f09bf09e250c44f6b155f60326ea8cab5120854b9d211a"
# client = api(api_key=API_KEY, host="http://127.0.0.1:5000")

# STRATEGY = "NIFTY_VWAP_OPTIONS"

# # 🔴 CHANGE DAILY
# SYMBOL = "NIFTY20JAN2625400CE"
# EXCHANGE = "NFO"
# PRODUCT = "MIS"
# QTY = 1

# STOPLOSS_POINTS = 15

# # =========================================


# def ensure_df(resp):
#     if isinstance(resp, dict):
#         return pd.DataFrame(resp.get("data", []))
#     return resp


# def get_previous_day_levels():
#     end = datetime.now().strftime("%Y-%m-%d")
#     start = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

#     resp = client.history(
#         symbol="NIFTY",
#         exchange="NSE_INDEX",
#         interval="5m",
#         start_date=start,
#         end_date=end
#     )

#     df = ensure_df(resp)

#     if df.empty or len(df) < 2:
#         print("⚠️ PD levels unavailable → VWAP-only mode")
#         return None, None, None

#     prev = df.iloc[-2]
#     return float(prev["high"]), float(prev["low"]), float(prev["close"])


# def vwap_strategy():
#     position = False
#     entry = None
#     sl = None

#     print("🚀 Starting NIFTY VWAP OPTIONS")

#     pdh, pdl, pdc = get_previous_day_levels()
#     print(f"📌 Prev Day → High={pdh} Low={pdl} Close={pdc}")

#     while True:
#         try:
#             now = datetime.now().time()

#             # Market hours
#             if now < datetime.strptime("09:15", "%H:%M").time():
#                 time.sleep(30)
#                 continue

#             # EOD exit
#             if now >= datetime.strptime("15:10", "%H:%M").time():
#                 if position:
#                     client.placesmartorder(
#                         strategy=STRATEGY,
#                         symbol=SYMBOL,
#                         exchange=EXCHANGE,
#                         action="SELL",
#                         price_type="MARKET",
#                         product=PRODUCT,
#                         quantity=QTY,
#                         position_size=0
#                     )
#                     print("⏰ EOD EXIT")
#                 break

#             # Fetch candles
#             start = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
#             end = datetime.now().strftime("%Y-%m-%d")

#             df = ensure_df(
#                 client.history(
#                     symbol=SYMBOL,
#                     exchange=EXCHANGE,
#                     interval="5m",
#                     start_date=start,
#                     end_date=end
#                 )
#             )

#             if df.empty or "vwap" not in df.columns:
#                 time.sleep(30)
#                 continue

#             df["close"] = df["close"].astype(float)
#             df["vwap"] = df["vwap"].astype(float)

#             last = df.iloc[-2]  # completed candle
#             close = last["close"]
#             vwap = last["vwap"]
#             ltp = df.iloc[-1]["close"]

#             print(f"LTP={ltp} | 5m Close={close} | VWAP={round(vwap,2)}")

#             # ENTRY
#             if not position:
#                 entry_condition = close > vwap
#                 if pdl:
#                     entry_condition |= close > pdl
#                 if pdc:
#                     entry_condition |= close > pdc

#                 if entry_condition:
#                     entry = close
#                     sl = entry - STOPLOSS_POINTS

#                     client.placesmartorder(
#                         strategy=STRATEGY,
#                         symbol=SYMBOL,
#                         exchange=EXCHANGE,
#                         action="BUY",
#                         price_type="MARKET",
#                         product=PRODUCT,
#                         quantity=QTY,
#                         position_size=QTY
#                     )

#                     position = True
#                     print(f"🟢 BUY @ {entry} SL={sl}")

#             # STOPLOSS
#             if position and ltp <= sl:
#                 client.placesmartorder(
#                     strategy=STRATEGY,
#                     symbol=SYMBOL,
#                     exchange=EXCHANGE,
#                     action="SELL",
#                     price_type="MARKET",
#                     product=PRODUCT,
#                     quantity=QTY,
#                     position_size=0
#                 )

#                 print(f"🔴 SL HIT @ {ltp}")
#                 position = False
#                 entry = None
#                 sl = None

#             time.sleep(30)

#         except Exception as e:
#             print("❌ Error:", e)
#             time.sleep(30)


# if __name__ == "__main__":
#     vwap_strategy()




# #!/usr/bin/env python
# #!/usr/bin/env python
# """
# NIFTY VWAP OPTIONS STRATEGY (OpenAlgo REST - STABLE)

# • Uses OpenAlgo built-in VWAP indicator
# • 5-minute candles
# • SL = 15 points
# • Exit only at SL or 3:10 PM
# • Same execution model as EMA example
# """

# from openalgo import api
# import pandas as pd
# import time
# from datetime import datetime, timedelta
# import os

# # ================= CONFIG =================

# API_KEY = os.getenv("OPENALGO_APIKEY") or "4c8cf77f82b8f0c196f09bf09e250c44f6b155f60326ea8cab5120854b9d211a"
# client = api(api_key=API_KEY, host="http://127.0.0.1:5000")

# STRATEGY = "NIFTY_VWAP_OPTIONS"

# # 🔴 CHANGE DAILY (must exist in OpenAlgo instruments)
# SYMBOL = "NIFTY20JAN2625400CE"
# EXCHANGE = "NFO"
# PRODUCT = "MIS"
# QTY = 1

# STOPLOSS_POINTS = 15

# # =========================================


# def ensure_df(resp):
#     """Convert OpenAlgo response to DataFrame safely"""
#     if isinstance(resp, dict):
#         return pd.DataFrame(resp.get("data", []))
#     return resp


# def get_previous_day_levels():
#     """
#     Robust previous-day High / Low / Close
#     Uses NIFTY INDEX (not option)
#     """

#     end = datetime.now().strftime("%Y-%m-%d")
#     start = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

#     resp = client.history(
#         symbol="NIFTY",
#         exchange="NSE_INDEX",
#         interval="1d",
#         start_date=start,
#         end_date=end
#     )

#     df = ensure_df(resp)

#     if df.empty or len(df) < 2:
#         print("⚠️ Previous-day data unavailable → VWAP-only mode")
#         return None, None, None

#     prev = df.iloc[-2]   # yesterday
#     return (
#         float(prev["high"]),
#         float(prev["low"]),
#         float(prev["close"])
#     )


# def fetch_vwap_df():
#     """
#     Fetch VWAP using OpenAlgo built-in indicator
#     """
#     resp = client.indicator(
#         name="vwap",
#         symbol=SYMBOL,
#         exchange=EXCHANGE,
#         interval="5m"
#     )

#     df = ensure_df(resp)

#     if df.empty or "vwap" not in df.columns:
#         raise Exception("VWAP data unavailable")

#     df["time"] = pd.to_datetime(df["time"])
#     df["vwap"] = df["vwap"].astype(float)

#     return df


# def fetch_5m_candles():
#     """
#     Fetch 5-minute option candles
#     """
#     end = datetime.now().strftime("%Y-%m-%d")
#     start = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

#     resp = client.history(
#         symbol=SYMBOL,
#         exchange=EXCHANGE,
#         interval="5m",
#         start_date=start,
#         end_date=end
#     )

#     df = ensure_df(resp)

#     if df.empty:
#         return pd.DataFrame()

#     df["time"] = pd.to_datetime(df["time"])
#     df["close"] = df["close"].astype(float)

#     return df


# def vwap_strategy():
#     position = False
#     entry_price = None
#     stoploss = None

#     print("🚀 Starting NIFTY VWAP OPTIONS")

#     pdh, pdl, pdc = get_previous_day_levels()
#     print(f"📌 Prev Day → High={pdh} Low={pdl} Close={pdc}")

#     while True:
#         try:
#             now = datetime.now().time()

#             # ===== Market hours =====
#             if now < datetime.strptime("09:15", "%H:%M").time():
#                 time.sleep(30)
#                 continue

#             # ===== EOD exit =====
#             if now >= datetime.strptime("15:10", "%H:%M").time():
#                 if position:
#                     client.placesmartorder(
#                         strategy=STRATEGY,
#                         symbol=SYMBOL,
#                         exchange=EXCHANGE,
#                         action="SELL",
#                         price_type="MARKET",
#                         product=PRODUCT,
#                         quantity=QTY,
#                         position_size=0
#                     )
#                     print("⏰ EOD EXIT")
#                 break

#             # ===== Data fetch =====
#             candle_df = fetch_5m_candles()
#             vwap_df = fetch_vwap_df()

#             if candle_df.empty or vwap_df.empty:
#                 time.sleep(30)
#                 continue

#             df = candle_df.merge(vwap_df, on="time", how="inner")

#             if len(df) < 2:
#                 time.sleep(30)
#                 continue

#             last_candle = df.iloc[-2]     # completed candle
#             close = last_candle["close"]
#             vwap = last_candle["vwap"]
#             ltp = df.iloc[-1]["close"]

#             print(f"LTP={ltp} | 5m Close={close} | VWAP={round(vwap,2)}")

#             # ===== ENTRY =====
#             if not position:
#                 entry_condition = close > vwap

#                 if pdl is not None:
#                     entry_condition = entry_condition or close > pdl
#                 if pdc is not None:
#                     entry_condition = entry_condition or close > pdc

#                 if entry_condition:
#                     entry_price = close
#                     stoploss = entry_price - STOPLOSS_POINTS

#                     client.placesmartorder(
#                         strategy=STRATEGY,
#                         symbol=SYMBOL,
#                         exchange=EXCHANGE,
#                         action="BUY",
#                         price_type="MARKET",
#                         product=PRODUCT,
#                         quantity=QTY,
#                         position_size=QTY
#                     )

#                     position = True
#                     print(f"🟢 BUY @ {entry_price} SL={stoploss}")

#             # ===== STOPLOSS =====
#             if position and ltp <= stoploss:
#                 client.placesmartorder(
#                     strategy=STRATEGY,
#                     symbol=SYMBOL,
#                     exchange=EXCHANGE,
#                     action="SELL",
#                     price_type="MARKET",
#                     product=PRODUCT,
#                     quantity=QTY,
#                     position_size=0
#                 )

#                 print(f"🔴 SL HIT @ {ltp}")
#                 position = False
#                 entry_price = None
#                 stoploss = None

#             time.sleep(30)

#         except Exception as e:
#             print("❌ Error:", e)
#             time.sleep(30)


# if __name__ == "__main__":
#     vwap_strategy()


