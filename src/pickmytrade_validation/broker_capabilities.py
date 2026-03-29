# ============================================================
# Broker Capabilities Map
# ============================================================
# This file defines which features each supported broker
# actually supports at the API level.
#
# Sources (verified from official API documentation):
#   - RITHMIC:      R|API+ server-side trailing stops & brackets
#   - IB:           TWS API — TRAIL order type, break_even param
#   - TRADOVATE:    Trail.Stop, autoTrail, autoBreakeven
#   - TRADIER:      market/limit/stop/stop_limit only (no native trailing)
#   - TRADELOCKER:  trStopOffset param for trailing
#   - TRADESTATION: TrailingStopOrder + SetBreakEven (EasyLanguage / REST API)
#   - PROJECTX:     Trailing stop = order type 5 with trailPrice param (TopstepX)
#   - BINANCE:      TRAILING_STOP_MARKET order type, trailingDelta param
#   - BYBIT:        trailingStop param via Set Trading Stop endpoint
#   - MATCHTRADER:  Trailing Stop Loss feature (platform-level support)
# ============================================================

BROKER_CAPABILITIES = {
    "RITHMIC": {
        "supports_trailing":           True,
        "supports_trail_stop":         False,
        "supports_trail_trigger":      True,
        "supports_trail_freq":         False,
        "supports_breakeven":          False,
        "supports_options":            True,
        "supports_equity_options":     False,
        "supports_update_tp_sl":       False,
        "supports_advance_tp_sl":      False,
        "supports_stop_orders":        False,
        "allowed_inst_types":          ["FUT", "FOP"],
    },
    "IB": {
        "supports_trailing":       True,
        "supports_trail_stop":     True,
        "supports_trail_trigger":  False,
        "supports_trail_freq":     False,
        "supports_breakeven":      True,
        "supports_options":        True,
        "supports_update_tp_sl":   False,
        "supports_advance_tp_sl":  False,
        "allowed_inst_types":      ["STK", "FUT", "OPT", "FOP", "CASH"],
    },
    "TRADOVATE": {
        "supports_trailing":       True,
        "supports_trail_stop":     True,
        "supports_trail_trigger":  True,
        "supports_trail_freq":     True,
        "supports_breakeven":      True,
        "supports_options":        True,
        "supports_update_tp_sl":   True,
        "supports_advance_tp_sl":  True,
        "allowed_inst_types":      ["FUT", "FOP"],
    },
    "TRADIER": {
        "supports_trailing":       False,
        "supports_trail_stop":     False,
        "supports_trail_trigger":  False,
        "supports_trail_freq":     False,
        "supports_breakeven":      False,
        "supports_options":        True,
        "supports_update_tp_sl":   False,
        "supports_advance_tp_sl":  False,
        "allowed_inst_types":      ["STK", "OPT"],
    },
    "TRADELOCKER": {
        "supports_trailing":       True,
        "supports_trail_stop":     True,
        "supports_trail_trigger":  False,
        "supports_trail_freq":     False,
        "supports_breakeven":      False,
        "supports_options":        False,
        "supports_update_tp_sl":   False,
        "supports_advance_tp_sl":  False,
        "allowed_inst_types":      ["EQUITY_CFD", "FOREX", "CRYPTO"],
    },
    "TRADESTATION": {
        "supports_trailing":       True,
        "supports_trail_stop":     True,
        "supports_trail_trigger":  False,
        "supports_trail_freq":     False,
        "supports_breakeven":      False,
        "supports_options":        True,
        "supports_update_tp_sl":   False,
        "supports_advance_tp_sl":  False,
        "allowed_inst_types":      ["STOCKS", "FUTURES", "OPTIONS"],
    },
    "PROJECTX": {
        "supports_trailing":       True,
        "supports_trail_stop":     False,
        "supports_trail_trigger":  False,
        "supports_trail_freq":     False,
        "supports_breakeven":      False,
        "supports_options":        False,
        "supports_update_tp_sl":   False,
        "supports_advance_tp_sl":  False,
        "allowed_inst_types":      ["FUT"],
        "notes": "TopstepX engine. Supports Futures only."
    },
    "BINANCE": {
        "supports_trailing":       True,
        "supports_trail_stop":     True,
        "supports_trail_trigger":  False,
        "supports_trail_freq":     False,
        "supports_breakeven":      False,
        "supports_options":        False,
        "supports_update_tp_sl":   False,
        "supports_advance_tp_sl":  False,
        "allowed_inst_types":      ["CRYPTO", "FUTURE", "FUTURES"],
    },
    "BYBIT": {
        "supports_trailing":       True,
        "supports_trail_stop":     True,
        "supports_trail_trigger":  False,
        "supports_trail_freq":     False,
        "supports_breakeven":      False,
        "supports_options":        False,
        "supports_update_tp_sl":   False,
        "supports_advance_tp_sl":  False,
        "allowed_inst_types":      ["CRYPTO", "FUTURE", "FUTURES"],
    },
    "MATCHTRADER": {
        "supports_trailing":       True,
        "supports_trail_stop":     False,
        "supports_trail_trigger":  False,
        "supports_trail_freq":     False,
        "supports_breakeven":      False,
        "supports_options":        False,
        "supports_update_tp_sl":   False,
        "supports_advance_tp_sl":  False,
        "allowed_inst_types":      ["CFD", "FOREX", "FOREXCFD"],
    },
}

def get_broker_capabilities(platform: str) -> dict:
    return BROKER_CAPABILITIES.get(str(platform).upper(), {})

def broker_supports_trailing(platform: str) -> bool:
    return get_broker_capabilities(platform).get("supports_trailing", False)

def broker_supports_trail_stop(platform: str) -> bool:
    return get_broker_capabilities(platform).get("supports_trail_stop", False)

def broker_supports_trail_trigger(platform: str) -> bool:
    return get_broker_capabilities(platform).get("supports_trail_trigger", False)

def broker_supports_trail_freq(platform: str) -> bool:
    return get_broker_capabilities(platform).get("supports_trail_freq", False)

def broker_supports_breakeven(platform: str) -> bool:
    return get_broker_capabilities(platform).get("supports_breakeven", False)

def broker_supports_options(platform: str) -> bool:
    return get_broker_capabilities(platform).get("supports_options", False)

def broker_supports_update_tp_sl(platform: str) -> bool:
    return get_broker_capabilities(platform).get("supports_update_tp_sl", False)

def broker_supports_advance_tp_sl(platform: str) -> bool:
    return get_broker_capabilities(platform).get("supports_advance_tp_sl", False)

def broker_supports_stop_orders(platform: str) -> bool:
    return get_broker_capabilities(platform).get("supports_stop_orders", True)

def get_allowed_inst_types(platform: str):
    return get_broker_capabilities(platform).get("allowed_inst_types", None)
