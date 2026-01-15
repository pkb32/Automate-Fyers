import pandas as pd
from datetime import datetime
import os


class ExcelLogger:
    def __init__(self):
        self.trades = []

    def log_trade(self, data: dict):
        self.trades.append(data)

    def save(self):
        if not self.trades:
            return

        df = pd.DataFrame(self.trades)

        filename = datetime.now().strftime("%d%m%y") + ".xlsx"
        report_dir = os.path.join("reports")
        os.makedirs(report_dir, exist_ok=True)

        #path = os.path.join(report_dir, filename)
        path = r'C:/Users/praya/Desktop/Fyres/reports'
        df.to_excel(path, index=False)

        print(f"[REPORT] Excel saved: {path}")
