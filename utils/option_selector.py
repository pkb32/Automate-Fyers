"""
Option Selector for NIFTY
Primary: ITM option with Delta ~ 0.85
Fallback: ITM + 5 strikes
"""

def select_itm_option(option_chain, spot_price, option_type):
    """
    option_chain: list of dicts from Fyers/OpenAlgo
    option_type: 'CALL' or 'PUT'
    """

    # =========================
    # PRIMARY: DELTA ~ 0.85
    # =========================
    eligible = []

    for opt in option_chain:
        if opt["type"] != option_type:
            continue

        delta = abs(opt.get("delta", 0))
        if 0.80 <= delta <= 0.90:
            eligible.append(opt)

    if eligible:
        # choose closest to 0.85
        return min(eligible, key=lambda x: abs(abs(x["delta"]) - 0.85))

    # =========================
    # FALLBACK: ITM + 5 STRIKES
    # =========================
    strikes = sorted(set(o["strike"] for o in option_chain))
    atm_strike = min(strikes, key=lambda x: abs(x - spot_price))

    if option_type == "CALL":
        target_strike = atm_strike - (5 * 50)
    else:
        target_strike = atm_strike + (5 * 50)

    fallback = [
        o for o in option_chain
        if o["strike"] == target_strike and o["type"] == option_type
    ]

    return fallback[0] if fallback else None
