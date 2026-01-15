# import sys
# import os
# import time

# # Ensure openalgo root is in PYTHONPATH
# BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# if BASE_DIR not in sys.path:
#     sys.path.insert(0, BASE_DIR)

# from strategies.nifty_vwap_itm import NiftyVWAPStrategy
# from services.websocket_client import WebSocketClient

# from utils.option_chain import select_option_by_delta
# from services.websocket_service import WebSocketService


# # def fetch_option_chain(symbol="NIFTY"):
# #     """
# #     Fetch option chain from OpenAlgo local REST API (authenticated)
# #     """
# #     url = "http://localhost:8765/api/v1/optionchain"

# #     headers = {
# #         "X-API-KEY": '4c8cf77f82b8f0c196f09bf09e250c44f6b155f60326ea8cab5120854b9d211a'
# #     }

# #     params = {
# #         "symbol": symbol
# #     }

# #     response = requests.get(
# #         url,
# #         headers=headers,
# #         params=params,
# #         timeout=5
# #     )

# #     response.raise_for_status()

# #     data = response.json()

# #     # OpenAlgo standard response
# #     return data["data"]


# class VWAPLiveRunner:
#     def __init__(self):
#         self.strategy = NiftyVWAPStrategy()

#     def on_message(self, message):
#         """
#         Example message (OpenAlgo standard):
#         {
#             'symbol': 'NIFTY24JAN19800CE',
#             'ltp': 198.5,
#             'volume': 25
#         }
#         """
#         try:
#             price = message.get("ltp")
#             if price:
#                 self.strategy.on_tick(price)
#         except Exception as e:
#             self.strategy.log(f"Runner error: {e}")

#     def start(self):
#         self.strategy.log("Live feed runner started (PAPER MODE)")

#         state = self.strategy.read_state()
#         option_type = state["option_type"]  # CALL / PUT

#         # ---- INTERNAL OPENALGO SERVICE (AUTHENTICATED) ----
#         service = WebSocketService(api_key='4c8cf77f82b8f0c196f09bf09e250c44f6b155f60326ea8cab5120854b9d211a')

#         chain = service.get_option_chain("NIFTY")

#         selected = select_option_by_delta(chain, option_type)

#         if not selected:
#             self.strategy.log("❌ No suitable option found")
#             return

#         option_symbol = selected["symbol"]
#         self.strategy.log(f"📌 Subscribed Option: {option_symbol}")

#         # ---- WebSocket ----
#         ws = WebSocketClient('4c8cf77f82b8f0c196f09bf09e250c44f6b155f60326ea8cab5120854b9d211a')
#         ws.on_message = self.on_message

#         ws.subscribe([option_symbol])
#         ws.connect()

#         while True:
#             time.sleep(1)





# if __name__ == "__main__":
#     VWAPLiveRunner().start()

import sys
import os
import time
import threading

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from strategies.nifty_vwap_itm import NiftyVWAPStrategy
from services.websocket_client import WebSocketClient
API_KEY='4c8cf77f82b8f0c196f09bf09e250c44f6b155f60326ea8cab5120854b9d211a'   # same key you already use


class VWAPLiveRunner:
    def __init__(self):
        self.strategy = NiftyVWAPStrategy()
        self.prev_day_sent = False
        threading.Thread(
            target=self.strategy.run,
            daemon=True
        ).start()



    def on_message(self, message):
        """
        Handles OpenAlgo WebSocket messages
        """

        # 🔍 TEMP DEBUG (keep for now)
        print("RAW MESSAGE:", message)

        # OpenAlgo payload lives inside "data"
        data = message.get("data")
        if not data:
            return

        # ================= PREVIOUS DAY LEVELS (ONCE) =================
        ohlc = data.get("ohlc")
        if ohlc and not self.prev_day_sent:
            self.strategy.set_prev_day_levels(
                high=ohlc.get("prev_high"),
                low=ohlc.get("prev_low"),
                close=ohlc.get("prev_close")
            )
            self.prev_day_sent = True

        # ================= LIVE PRICE =================
        ltp = data.get("ltp")
        print("LTP:", ltp)
        self.strategy.log(f"📈 LTP RECEIVED: {ltp}"    )
        if ltp is not None:
            self.strategy.on_tick(float(ltp))


    # def start(self):
    #     self.strategy.log("Live feed runner started (PAPER MODE)")

    #     state = self.strategy.read_state()
    #     option_symbol = state.get("symbol")

    #     if not option_symbol:
    #         self.strategy.log("❌ No option symbol provided in GUI")
    #         return
      

    #     self.strategy.log(f"📌 Subscribing to: {option_symbol}")

    #     ws = WebSocketClient(API_KEY)

    #     def _on_open():
    #         self.strategy.log("✅ WebSocket CONNECTED")

    #     def _on_close():
    #         self.strategy.log("❌ WebSocket DISCONNECTED")

    #     ws.on_message = self.on_message
    #     ws.on_open = _on_open
    #     ws.on_close = _on_close

    #     ws.connect()
    #     ws.subscribe([option_symbol])
    #     self.strategy.log("📡 WebSocket connect() called")

    #     while True:
    #         time.sleep(1)
    def start(self):
        self.strategy.log("Live feed runner started (PAPER MODE)")

        state = self.strategy.read_state()
        option_symbol = state.get("symbol")

        if not option_symbol:
            self.strategy.log("❌ No option symbol provided in GUI")
            return

        self.strategy.log(f"📌 Will subscribe to: {option_symbol}")

        while True:
            try:
                ws = WebSocketClient(API_KEY)
                ws.on_message = self.on_message

                # 1️⃣ Start connection
                ws.connect()
                self.strategy.log("⏳ Connecting to WebSocket...")

                # 2️⃣ WAIT until authenticated / connected
                timeout = time.time() + 15  # max 15s
                while not ws.connected:
                    if time.time() > timeout:
                        raise TimeoutError("WebSocket connect timeout")
                    time.sleep(0.2)

                self.strategy.log("✅ WebSocket authenticated & ready")

                # 3️⃣ NOW subscribe (safe)
                               
                ws.subscribe([
                    {
                        "exchange": "NSE_INDEX",
                        "symbol": "NIFTY"
                    }
                ])


                self.strategy.log(f"✅ Subscribed to {option_symbol}")

                # 4️⃣ Keep runner alive
                while True:
                    time.sleep(1)

            except Exception as e:
                self.strategy.log(f"⚠️ WebSocket error, retrying in 5s: {e}")
                time.sleep(5)



if __name__ == "__main__":
    VWAPLiveRunner().start()
