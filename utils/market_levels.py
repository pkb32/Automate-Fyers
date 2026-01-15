class MarketLevels:
    def __init__(self):
        self.prev_day_high = None
        self.prev_day_low = None
        self.prev_day_close = None
        self.vwap = None

    def update_vwap(self, vwap_value):
        self.vwap = vwap_value

    def set_prev_day(self, high, low, close):
        self.prev_day_high = high
        self.prev_day_low = low
        self.prev_day_close = close
