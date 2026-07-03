"""WEBULL platform recognition + capability gating.

Webull Connect API (US stocks + options only, as implemented in the trade
path): equity orders MKT/LMT/STP/STPLMT (NO trailing), option orders priced
via option_premium (no MARKET option entries), TIF DAY/GTC, atomic OTO/OTOCO
TP/SL brackets, resting TP/SL children modifiable via order/replace.
"""
from pickmytrade_validation import validate_and_describe_alert_json
from pickmytrade_validation.broker_capabilities import (
    broker_supports_breakeven,
    broker_supports_options,
    broker_supports_stop_orders,
    broker_supports_trailing,
    broker_supports_update_tp_sl,
    get_allowed_inst_types,
)

WEBULL_STOCK_BUY = {
    "token": "abc",
    "symbol": "AAPL",
    "quantity": 1,
    "data": "BUY",
    "platform": "WEBULL",
    "order_type": "MKT",
    "inst_type": "STK",
}

WEBULL_OPTION_BUY = {
    **WEBULL_STOCK_BUY,
    "order_type": "LMT",
    "price": 1.25,
    "inst_type": "OPT",
    "option_type": "CALL",
    "expiry_date": "20260619",
    "order_strike": 1,
}


class TestWebullCapabilityFlags:
    def test_webull_options_supported(self):
        assert broker_supports_options("WEBULL") is True

    def test_webull_no_trailing(self):
        assert broker_supports_trailing("WEBULL") is False

    def test_webull_no_breakeven(self):
        assert broker_supports_breakeven("WEBULL") is False

    def test_webull_stop_orders_supported(self):
        assert broker_supports_stop_orders("WEBULL") is True

    def test_webull_update_tp_sl_supported(self):
        # Resting TP/SL children are replaced via order/replace (handle_modify).
        assert broker_supports_update_tp_sl("WEBULL") is True

    def test_webull_inst_types_stocks_and_options_only(self):
        allowed = get_allowed_inst_types("WEBULL")
        assert "STK" in allowed and "OPT" in allowed
        assert "FUT" not in allowed and "CRYPTO" not in allowed


class TestWebullValidatorIntegration:
    def test_webull_platform_recognised(self):
        r = validate_and_describe_alert_json(WEBULL_STOCK_BUY)
        assert r["error"] is False
        assert not any("platform" in f for f in r["invalid_fields"])

    def test_webull_stock_stop_order_permitted(self):
        r = validate_and_describe_alert_json(
            {**WEBULL_STOCK_BUY, "order_type": "STP", "price": 150}
        )
        assert r["error"] is False

    def test_webull_option_alert_passes(self):
        r = validate_and_describe_alert_json(WEBULL_OPTION_BUY)
        assert r["error"] is False

    def test_webull_futures_rejected(self):
        r = validate_and_describe_alert_json({**WEBULL_STOCK_BUY, "inst_type": "FUT"})
        assert r["error"] is True
        assert any("instrument types" in str(f) for f in r["invalid_fields"])

    def test_webull_trailing_warned_as_ignored(self):
        r = validate_and_describe_alert_json(
            {**WEBULL_STOCK_BUY, "trail": 1, "price": 150}
        )
        assert any(
            "does not support native API trailing stops" in w for w in r["warnings"]
        )
