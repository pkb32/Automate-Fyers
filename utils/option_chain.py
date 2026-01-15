"""
Fetch NIFTY option chain and select ITM option by delta.
Primary: Delta ~ 0.85
Fallback: ITM + 5 strikes
"""

def select_option_by_delta(option_chain, option_type, target_delta=0.85):
    """
    option_chain: list of dicts
    option_type: 'CALL' or 'PUT'
    """

    # ---------- PRIMARY: Delta ≈ 0.85 ----------
    candidates = []
    for opt in option_chain:
        if opt.get("type") != option_type:
            continue

        delta = abs(opt.get("delta", 0))
        if 0.80 <= delta <= 0.90:
            candidates.append(opt)

    if candidates:
        return min(candidates, key=lambda x: abs(abs(x["delta"]) - target_delta))

    # ---------- FALLBACK: ITM + 5 STRIKES ----------
    strikes = sorted(set(o["strike"] for o in option_chain))
    spot = option_chain[0]["spot_price"]
    atm = min(strikes, key=lambda x: abs(x - spot))

    if option_type == "CALL":
        target = atm - (5 * 50)
    else:
        target = atm + (5 * 50)

    for opt in option_chain:
        if opt["strike"] == target and opt["type"] == option_type:
            return opt

    return None
