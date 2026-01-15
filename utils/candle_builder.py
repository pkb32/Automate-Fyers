from datetime import datetime


class CandleBuilder:
    def __init__(self, interval_minutes=5):
        self.interval = interval_minutes
        self.current_candle = None
        self.candles = []

    def update(self, price, volume=0):
        now = datetime.now()
        bucket = now.replace(
            second=0, microsecond=0,
            minute=(now.minute // self.interval) * self.interval
        )

        if not self.current_candle or self.current_candle["time"] != bucket:
            if self.current_candle:
                self.candles.append(self.current_candle)

            self.current_candle = {
                "time": bucket,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume
            }
            return "NEW_CANDLE"

        self.current_candle["high"] = max(self.current_candle["high"], price)
        self.current_candle["low"] = min(self.current_candle["low"], price)
        self.current_candle["close"] = price
        self.current_candle["volume"] += volume

        return "UPDATE"

    def last_closed_candle(self):
        return self.candles[-1] if self.candles else None
