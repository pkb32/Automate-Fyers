import json
import os
import time
from datetime import datetime

import sys
import os

# Ensure openalgo root is in PYTHONPATH
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from utils.candle_builder import CandleBuilder
from utils.market_levels import MarketLevels
from utils.excel_logger import ExcelLogger
from utils.logger import log

LIVE_MODE = True   #  KEEP FALSE until final confirmation

STATE_FILE = os.path.join(
    os.path.dirname(__file__),
    "nifty_vwap_state.json"
)

LOG_PREFIX = "[NIFTY_VWAP_ITM]"


class NiftyVWAPStrategy:
    def __init__(self):
        # Position state
        self.position_open = False
        self.entry_price = None
        self.stoploss = None

        # Risk state
        self.daily_loss = 0

        # Market data helpers
        self.candle_builder = CandleBuilder(interval_minutes=5)
        self.levels = MarketLevels()
        self.excel = ExcelLogger()

    # ================= STATE =================
    def read_state(self):
        with open(STATE_FILE, "r") as f:
            return json.load(f)

    # ================= LOG =================
    def log(self, msg):
        print(f"{LOG_PREFIX} {datetime.now().strftime('%H:%M:%S')} | {msg}")

    # ================= MARKET CHECK =================
    def is_market_time(self):
        now = datetime.now().time()
        return (
            now >= datetime.strptime("09:15", "%H:%M").time()
            and now <= datetime.strptime("15:10", "%H:%M").time()
        )

    # ================= TICK HANDLER =================

    
    def on_tick(self, price):
        """
        Called ONLY by the live WebSocket runner with REAL LTP
        """
        self.log(f"📈 TICK RECEIVED: {price}")
        status = self.candle_builder.update(price)

        # ===== NEW 5-MIN CANDLE CLOSED =====
        if status == "NEW_CANDLE":
            candle = self.candle_builder.last_closed_candle()

            if candle:
                # 🔑 REAL VWAP from REAL candle
                if "vwap" in candle:
                    self.levels.update_vwap(candle["vwap"])

                self.log(
                    f"5m Close={candle['close']} | "
                    f"VWAP={self.levels.vwap} | "
                    f"PDL={self.levels.prev_day_low} | "
                    f"PDC={self.levels.prev_day_close}"
                )

                # 🔑 ENTRY DECISION BASED ON REAL DATA
                self.evaluate_entry(candle)

        # ===== MANAGE OPEN POSITION TICK-BY-TICK =====
        if self.position_open:
            self.manage_position(price)

    # ================= prev_day_data =============

    def set_prev_day_levels(self, high, low, close):
        self.levels.set_prev_day(high=high, low=low, close=close)
        self.log(
            f"Prev Day Levels Set | High={high} | Low={low} | Close={close}"
        )



    # ================= ENTRY LOGIC =================
    def evaluate_entry(self, candle):
        if self.position_open:
            return

        close = candle["close"]

        self.log(
            f"5m Close={close} | VWAP={self.levels.vwap} | "
            f"PDL={self.levels.prev_day_low} | "
            f"PDC={self.levels.prev_day_close}"
        )

        entry_condition = (
            (self.levels.vwap and close > self.levels.vwap)
            or (self.levels.prev_day_low and close > self.levels.prev_day_low)
            or (self.levels.prev_day_close and close > self.levels.prev_day_close)
        )

        if entry_condition:
            self.position_open = True
            self.entry_price = close
            self.stoploss = close - 15

            self.log(
                f"🟢 PAPER BUY @ {self.entry_price} | SL={self.stoploss}"
            )

    # ================= POSITION MANAGEMENT =================

    def manage_position(self, price):
        """
        Position management rules:
        - Initial SL = Entry - 15 points (fixed)
        - Do NOT exit before this SL unless 3:10 PM
        - RR = 2:1 → 30 points
        - SL moves ONLY after RR >= 2:1
        - After RR >= 2:1, maintain RR dynamically
        """

        # Safety check
        if self.entry_price is None or self.stoploss is None:
            return

        INITIAL_RISK = 15
        RR_MULTIPLE = 2
        RR_DISTANCE = INITIAL_RISK * RR_MULTIPLE  # 30 points

        now = datetime.now().time()

        # ================= AUTO SQUARE-OFF @ 3:10 PM =================
        if now >= datetime.strptime("15:10", "%H:%M").time():
            pnl = price - self.entry_price
            self.daily_loss += pnl

            self.log(
                f"⏰ EOD EXIT @ {price} | "
                f"PnL={pnl} | DailyPnL={self.daily_loss}"
            )

            # ===== EXCEL LOGGING =====
            self.excel.log_trade({
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Time": datetime.now().strftime("%H:%M:%S"),
                "Instrument": "NIFTY_OPTION",
                "Quantity": "Lots-based",
                "Entry Price": self.entry_price,
                "Exit Price": price,
                "PnL": pnl,
                "Cumulative PnL": self.daily_loss,
                "Exit Reason": "EOD"
            })

            # ===== RESET POSITION =====
            self.position_open = False
            self.entry_price = None
            self.stoploss = None
            return

        # ================= RR & SL MANAGEMENT =================
        price_move = price - self.entry_price

        # ---- ONLY AFTER RR >= 2:1 ----
        if price_move >= RR_DISTANCE:
            # First RR hit → move SL to breakeven
            if self.stoploss < self.entry_price:
                self.stoploss = self.entry_price
                self.log(f"🟢 RR 2:1 reached | SL moved to BE @ {self.stoploss}")

            # Dynamic SL to maintain RR >= 2:1
            dynamic_sl = price - RR_DISTANCE
            if dynamic_sl > self.stoploss:
                self.stoploss = dynamic_sl
                self.log(f"🔁 Trailing SL updated to {self.stoploss}")

        # ================= STOPLOSS HIT =================
        if price <= self.stoploss:
            pnl = price - self.entry_price
            self.daily_loss += pnl

            self.log(
                f"🔴 SL HIT @ {price} | "
                f"SL={self.stoploss} | "
                f"PnL={pnl} | DailyPnL={self.daily_loss}"
            )

            # ===== EXCEL LOGGING =====
            self.excel.log_trade({
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Time": datetime.now().strftime("%H:%M:%S"),
                "Instrument": "NIFTY_OPTION",
                "Quantity": "Lots-based",
                "Entry Price": self.entry_price,
                "Exit Price": price,
                "PnL": pnl,
                "Cumulative PnL": self.daily_loss,
                "Exit Reason": "STOPLOSS"
            })

            # ===== RESET POSITION =====
            self.position_open = False
            self.entry_price = None
            self.stoploss = None


   
    def run(self):
        self.log("Strategy started (REAL DATA MODE)")

        while True:
            try:
                state = self.read_state()

                # ===== Strategy ON/OFF from GUI =====
                if not state["enabled"]:
                    time.sleep(2)
                    continue

                # ===== Daily loss protection =====
                if self.daily_loss <= -2000:
                    self.log("Daily loss limit hit. Trading disabled.")
                    time.sleep(5)
                    continue

                # ===== Market hours check =====
                if not self.is_market_time():
                    self.log("Outside market hours. Waiting for market open...")
                    time.sleep(30)
                    continue

                # 🔑 REAL DATA COMES FROM RUNNER → on_tick()
                time.sleep(1)

            except Exception as e:
                self.log(f"ERROR: {e}")
                time.sleep(5)


if __name__ == "__main__":
    strategy = NiftyVWAPStrategy()
    strategy.run()
