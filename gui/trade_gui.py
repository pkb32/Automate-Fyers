import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import json
import os
import subprocess
import time
import sys
import threading
# ================= PATH SETUP =================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

STATE_FILE = os.path.join(
    BASE_DIR, "strategies", "nifty_vwap_state.json"
)

LOG_FILE = os.path.join(
    BASE_DIR, "logs", "runtime.log"
)

PYTHON_EXEC = sys.executable


# Import LIVE_MODE safely
try:
    from strategies.nifty_vwap_itm import LIVE_MODE
except Exception:
    LIVE_MODE = False


class TradeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NIFTY VWAP Options Trader")
        self.root.geometry("560x680")

        self.trade_running = False
        self.strategy_process = None
        self.runner_process = None
        self.openalgo_process = None

        self._ensure_state_file()
        self._build_ui()

        # ===== LIVE MODE INDICATOR =====
        mode_text = "🔴 LIVE MODE" if LIVE_MODE else "🟢 PAPER MODE"
        mode_color = "red" if LIVE_MODE else "green"

        self.mode_label = tk.Label(
            self.root,
            text=mode_text,
            fg="white",
            bg=mode_color,
            font=("Arial", 14, "bold"),
            pady=10
        )
        self.mode_label.pack(fill="x")

        # Start log tailing
        self.tail_logs()

    # ================= STATE =================
    def _ensure_state_file(self):
        if not os.path.exists(STATE_FILE):
            self._write_state(False, "CALL", 1, 0, "NIFTY")

    def _write_state(self, enabled, option_type, lots, daily_loss, symbol):
        state = {
            "enabled": enabled,
            "option_type": option_type,
            "lots": lots,
            "daily_loss": daily_loss,
            "symbol": symbol,
            "last_updated": datetime.now().isoformat()
        }

        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)

    # ================= UI =================
    def _build_ui(self):
        title = ttk.Label(
            self.root,
            text="NIFTY VWAP ITM OPTIONS STRATEGY",
            font=("Arial", 14, "bold")
        )
        title.pack(pady=10)

        # ===== Option Type =====
        frame_option = ttk.LabelFrame(self.root, text="Option Type")
        frame_option.pack(fill="x", padx=15, pady=5)

        self.option_type = tk.StringVar(value="CALL")

        ttk.Radiobutton(
            frame_option, text="CALL", variable=self.option_type, value="CALL"
        ).pack(side="left", padx=20)

        ttk.Radiobutton(
            frame_option, text="PUT", variable=self.option_type, value="PUT"
        ).pack(side="left", padx=20)

        # ===== Option Symbol =====
        frame_symbol = ttk.LabelFrame(self.root, text="Option Symbol")
        frame_symbol.pack(fill="x", padx=15, pady=5)

        ttk.Label(frame_symbol, text="Symbol:").pack(side="left", padx=10)

        self.symbol_entry = ttk.Entry(frame_symbol, width=30)
        self.symbol_entry.pack(side="left", padx=10)
        self.symbol_entry.insert(0, "NIFTY25JAN19800CE")

        # ===== Quantity =====
        frame_qty = ttk.LabelFrame(self.root, text="Quantity")
        frame_qty.pack(fill="x", padx=15, pady=5)

        ttk.Label(frame_qty, text="Lots:").pack(side="left", padx=10)
        self.lots_entry = ttk.Entry(frame_qty, width=10)
        self.lots_entry.pack(side="left", padx=10)
        self.lots_entry.insert(0, "1")

        # ===== Buttons =====
        frame_buttons = ttk.Frame(self.root)
        frame_buttons.pack(pady=10)

        self.start_btn = ttk.Button(
            frame_buttons, text="START", command=self.start_trading
        )
        self.start_btn.pack(side="left", padx=10)

        self.end_btn = ttk.Button(
            frame_buttons, text="END", command=self.stop_trading, state="disabled"
        )
        self.end_btn.pack(side="left", padx=10)

        # ===== Backend Status =====
        status_frame = ttk.LabelFrame(self.root, text="Backend Status")
        status_frame.pack(fill="x", padx=15, pady=5)

        self.strategy_status = ttk.Label(
            status_frame, text="Strategy: STOPPED", foreground="red"
        )
        self.strategy_status.pack(anchor="w", padx=10)

        self.runner_status = ttk.Label(
            status_frame, text="WebSocket: STOPPED", foreground="red"
        )
        self.runner_status.pack(anchor="w", padx=10)

        # ===== Logs =====
        frame_logs = ttk.LabelFrame(self.root, text="Live Logs")
        frame_logs.pack(fill="both", expand=True, padx=15, pady=10)

        self.log_text = tk.Text(
            frame_logs,
            height=15,
            state="disabled",
            bg="black",
            fg="lime",
            font=("Consolas", 9)
        )
        self.log_text.pack(fill="both", expand=True)

    # ================= LOGGING =================
    def tail_logs(self):
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r") as f:
                    lines = f.readlines()[-100:]

                self.log_text.config(state="normal")
                self.log_text.delete("1.0", tk.END)
                for line in lines:
                    self.log_text.insert(tk.END, line)
                self.log_text.config(state="disabled")
        except Exception:
            pass

        self.root.after(2000, self.tail_logs)

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.root.after(0, _append)

    # ================= CONTROLS =================
    def start_trading(self):
        if self.trade_running:
            return

        try:
            lots = int(self.lots_entry.get())
            if lots <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Lots must be a positive number")
            return

        symbol = self.symbol_entry.get().strip().upper()
        if not symbol:
            messagebox.showerror("Invalid Input", "Option symbol cannot be empty")
            return

        if LIVE_MODE:
            confirm = messagebox.askyesno(
                "LIVE MODE CONFIRMATION",
                "⚠️ YOU ARE IN LIVE MODE ⚠️\n\n"
                "REAL orders will be placed.\n\n"
                "Do you want to continue?"
            )
            if not confirm:
                return

        self.trade_running = True
        self.start_btn.config(state="disabled")
        self.end_btn.config(state="normal")

        self._write_state(
            enabled=True,
            option_type=self.option_type.get(),
            lots=lots,
            daily_loss=0,
            symbol=symbol
        )

        self.log("Trading ENABLED")
        self.log(f"Symbol: {symbol}")
        self.log(f"Lots: {lots}")

        # -------- Start OpenAlgo Engine --------
        #self.openalgo_process = subprocess.Popen(
        #     [PYTHON_EXEC, "app.py"],
        #     cwd=BASE_DIR
        # )

        # time.sleep(3)

        # -------- Start Strategy --------
        self.strategy_process = subprocess.Popen(
            [PYTHON_EXEC, "strategies/nifty_vwap_itm.py"],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
         # 👉 START STREAMING STRATEGY LOGS INTO GUI
        threading.Thread(
            target=self.stream_logs,
            args=(self.strategy_process,),
            daemon=True
        ).start()

        self.strategy_status.config(text="Strategy: RUNNING", foreground="green")

        # -------- Start Runner --------
        self.runner_process = subprocess.Popen(
            [PYTHON_EXEC, "strategies/nifti_vwap_runner.py"],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
         # 👉 START STREAMING STRATEGY LOGS INTO GUI
        threading.Thread(
            target=self.stream_logs,
            args=(self.runner_process,),
            daemon=True
        ).start()

        self.log("Strategy process started")
        self.runner_status.config(text="WebSocket: RUNNING", foreground="green")

    def stop_trading(self):
        if not self.trade_running:
            return

        self.trade_running = False
        self.start_btn.config(state="normal")
        self.end_btn.config(state="disabled")

        self._write_state(
            enabled=False,
            option_type=self.option_type.get(),
            lots=int(self.lots_entry.get()),
            daily_loss=0,
            symbol=self.symbol_entry.get().strip().upper()
        )

        self.log("Trading DISABLED by user")

        for proc, name in [
            (self.strategy_process, "Strategy"),
            (self.runner_process, "Runner"),
            (self.openalgo_process, "OpenAlgo"),
        ]:
            if proc:
                proc.terminate()

        self.strategy_status.config(text="Strategy: STOPPED", foreground="red")
        self.runner_status.config(text="WebSocket: STOPPED", foreground="red")

    def stream_logs(self, process):
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            self.log(line.strip())



if __name__ == "__main__":
    root = tk.Tk()
    app = TradeGUI(root)
    root.mainloop()
