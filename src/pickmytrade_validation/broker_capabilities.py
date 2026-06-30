# ============================================================
# Broker Capabilities Map
# ============================================================
# This file defines which features each supported broker
# actually supports at the API level.
#
# Sources (verified from official API documentation):
#   - RITHMIC:      R|API+ server-side trailing stops & brackets
#   - IB:           TWS API — TRAIL order type, break_even param
#                   + native multi-leg via BAG/ComboLeg (v1: 9 strategies, max 6 legs)
#   - TRADOVATE:    Trail.Stop, autoTrail, autoBreakeven
#   - TRADIER:      market/limit/stop/stop_limit only (no native trailing);
#                   multileg API exists but spreads deferred to v2
#   - TRADELOCKER:  trStopOffset param for trailing
#   - TRADESTATION: TrailingStopOrder + SetBreakEven (EasyLanguage / REST API);
#                   multileg API exists but spreads deferred to v2
#   - PROJECTX:     Trailing stop = order type 5 with trailPrice param (TopstepX)
#   - BINANCE:      TRAILING_STOP_MARKET order type, trailingDelta param
#   - BYBIT:        trailingStop param via Set Trading Stop endpoint
#   - MATCHTRADER:  Trailing Stop Loss feature (platform-level support)
#
# Spread fields (added 2026-05): supports_spreads, supported_spread_strategies,
# max_spread_legs — used by /v3/add-option-spread to gate inbound spread
# payloads. v1 ships IB only.
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
        "supports_spreads":            False,
        "supported_spread_strategies": [],
        "max_spread_legs":             0,
        "allowed_inst_types":          ["FUT", "FOP"],
    },
    "IB": {
        "supports_trailing":            True,
        "supports_trail_stop":          True,
        "supports_trail_trigger":       False,
        "supports_trail_freq":          False,
        "supports_breakeven":           True,
        "supports_options":             True,
        "supports_update_tp_sl":        False,
        "supports_advance_tp_sl":       False,
        "supports_spreads":             True,
        "supported_spread_strategies":  [
            "vertical", "iron_condor", "iron_butterfly", "butterfly",
            "calendar", "diagonal", "straddle", "strangle", "custom",
        ],
        "max_spread_legs":              6,
        "allowed_inst_types":           ["STK", "FUT", "OPT", "FOP", "CASH"],
    },
    "TRADOVATE": {
        "supports_trailing":            True,
        "supports_trail_stop":          True,
        "supports_trail_trigger":       True,
        "supports_trail_freq":          True,
        "supports_breakeven":           True,
        "supports_options":             True,
        "supports_update_tp_sl":        True,
        "supports_advance_tp_sl":       True,
        "supports_spreads":             False,
        "supported_spread_strategies":  [],
        "max_spread_legs":              0,
        "allowed_inst_types":           ["FUT"],
    },
    "TRADIER": {
        "supports_trailing":            False,
        "supports_trail_stop":          False,
        "supports_trail_trigger":       False,
        "supports_trail_freq":          False,
        "supports_breakeven":           False,
        "supports_options":             True,
        "supports_update_tp_sl":        False,
        "supports_advance_tp_sl":       False,
        "supports_spreads":             False,
        "supported_spread_strategies":  [],
        "max_spread_legs":              0,
        "allowed_inst_types":           ["STK", "OPT"],
    },
    "TRADELOCKER": {
        "supports_trailing":            True,
        "supports_trail_stop":          True,
        "supports_trail_trigger":       False,
        "supports_trail_freq":          False,
        "supports_breakeven":           False,
        "supports_options":             False,
        "supports_update_tp_sl":        False,
        "supports_advance_tp_sl":       False,
        "supports_spreads":             False,
        "supported_spread_strategies":  [],
        "max_spread_legs":              0,
        "allowed_inst_types":           ["EQUITY_CFD", "FOREX", "CRYPTO"],
    },
    "TRADESTATION": {
        "supports_trailing":            True,
        "supports_trail_stop":          True,
        "supports_trail_trigger":       False,
        "supports_trail_freq":          False,
        "supports_breakeven":           False,
        "supports_options":             True,
        "supports_update_tp_sl":        False,
        "supports_advance_tp_sl":       False,
        "supports_spreads":             False,
        "supported_spread_strategies":  [],
        "max_spread_legs":              0,
        "allowed_inst_types":           ["STOCKS", "FUTURES", "OPTIONS"],
    },
    "PROJECTX": {
        "supports_trailing":            True,
        "supports_trail_stop":          False,
        "supports_trail_trigger":       False,
        "supports_trail_freq":          False,
        "supports_breakeven":           False,
        "supports_options":             False,
        "supports_update_tp_sl":        False,
        "supports_advance_tp_sl":       False,
        "supports_spreads":             False,
        "supported_spread_strategies":  [],
        "max_spread_legs":              0,
        "allowed_inst_types":           ["FUT"],
        "notes": "TopstepX engine. Supports Futures only."
    },
    "BINANCE": {
        "supports_trailing":            True,
        "supports_trail_stop":          True,
        "supports_trail_trigger":       False,
        "supports_trail_freq":          False,
        "supports_breakeven":           False,
        "supports_options":             False,
        "supports_update_tp_sl":        False,
        "supports_advance_tp_sl":       False,
        "supports_spreads":             False,
        "supported_spread_strategies":  [],
        "max_spread_legs":              0,
        "allowed_inst_types":           ["CRYPTO", "FUTURE", "FUTURES"],
    },
    "BYBIT": {
        "supports_trailing":            True,
        "supports_trail_stop":          True,
        "supports_trail_trigger":       False,
        "supports_trail_freq":          False,
        "supports_breakeven":           False,
        "supports_options":             False,
        "supports_update_tp_sl":        False,
        "supports_advance_tp_sl":       False,
        "supports_spreads":             False,
        "supported_spread_strategies":  [],
        "max_spread_legs":              0,
        "allowed_inst_types":           ["CRYPTO", "FUTURE", "FUTURES"],
    },
    "MATCHTRADER": {
        "supports_trailing":            True,
        "supports_trail_stop":          False,
        "supports_trail_trigger":       False,
        "supports_trail_freq":          False,
        "supports_breakeven":           False,
        "supports_options":             False,
        "supports_update_tp_sl":        False,
        "supports_advance_tp_sl":       False,
        "supports_spreads":             False,
        "supported_spread_strategies":  [],
        "max_spread_legs":              0,
        "allowed_inst_types":           ["CFD", "FOREX", "FOREXCFD"],
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

def broker_supports_spreads(platform: str) -> bool:
    return bool(get_broker_capabilities(platform).get("supports_spreads", False))

def get_supported_spread_strategies(platform: str) -> list:
    return list(get_broker_capabilities(platform).get("supported_spread_strategies", []))

def get_max_spread_legs(platform: str) -> int:
    return int(get_broker_capabilities(platform).get("max_spread_legs", 0))