"""WEBULL capability gating.

Webull Connect API (US stocks + options only, as implemented in the trade
path): equity orders MKT/LMT/STP/STPLMT (NO trailing), option orders priced
via option_premium (no MARKET option entries), TIF DAY/GTC, atomic OTO/OTOCO
TP/SL brackets, resting TP/SL children modifiable via order/replace.

NOTE: the generic ``validate_and_describe_alert_json`` was refactored on main
from platform-based dispatch (VALID_PLATFORMS + ``platform`` field) to
broker-based dispatch (``Broker`` enum + ``broker`` field) routing to the nine
per-broker validators. WEBULL is intentionally NOT one of those per-broker
validators (the PMT app does not import a webull validator); WEBULL is carried
purely as a broker-capabilities entry, which is what the trade path consumes.
The former platform-based validator-integration tests were therefore dropped
because the API they exercised no longer exists.
"""
from pickmytrade_validation.broker_capabilities import (
    broker_supports_breakeven,
    broker_supports_options,
    broker_supports_stop_orders,
    broker_supports_trailing,
    broker_supports_update_tp_sl,
    get_allowed_inst_types,
)


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
