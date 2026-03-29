import pytest
from pickmytrade_validation import validate_and_describe_alert_json

# ── Shared helper payloads ───────────────────────────────────────────────────
MINIMAL_BUY = {
    "token": "abc", 
    "symbol": "ES", 
    "quantity": 2, 
    "data": "BUY", 
    "platform": "RITHMIC", 
    "order_type": "MKT", 
    "inst_type": "FUT"
}

MINIMAL_OPT = {
    **MINIMAL_BUY,
    "platform": "IB",
    "inst_type": "OPT",
    "option_type": "CALL",
    "expiry_date": "20240517",
    "order_strike": 4500
}

class TestRequiredFields:
    def test_missing_token_returns_error(self):
        r = validate_and_describe_alert_json({"symbol": "ES", "quantity": 1, "platform": "RITHMIC", "inst_type": "FUT", "order_type": "MKT"})
        assert r["error"] is True
        assert "token" in r["missing_fields"]

    def test_missing_quantity_and_risk_pct_returns_error(self):
        r = validate_and_describe_alert_json({"token": "abc", "symbol": "ES", "platform": "RITHMIC", "data": "BUY", "order_type": "MKT"})
        assert r["error"] is True
        assert any("quantity_or_risk_percentage" in f for f in r["missing_fields"])

class TestValueValidation:
    def test_invalid_platform_returns_error(self):
        r = validate_and_describe_alert_json({**MINIMAL_BUY, "platform": "FAKEBROKE"})
        assert r["error"] is True
        assert any("platform" in f for f in r["invalid_fields"])

    def test_invalid_boolean_field_returns_error(self):
        r = validate_and_describe_alert_json({**MINIMAL_BUY, "pyramid": "yes"})
        assert r["error"] is True
        assert any("pyramid" in f and "boolean" in f for f in r["invalid_fields"])

class TestBrokerSpecificEnforcement:
    def test_rithmic_stop_order_fails(self):
        r = validate_and_describe_alert_json({**MINIMAL_BUY, "platform": "RITHMIC", "order_type": "STP", "price": 4500})
        assert r["error"] is True
        assert any("RITHMIC only supports MKT and LMT" in str(f) for f in r["invalid_fields"])

    def test_projectx_fut_only(self):
        # ProjectX only supports FUT
        r = validate_and_describe_alert_json({**MINIMAL_BUY, "platform": "PROJECTX", "inst_type": "CFD"})
        assert r["error"] is True
        assert "strictly only supports the following instrument types: FUT" in str(r["invalid_fields"])

    def test_binance_crypto_future(self):
        r = validate_and_describe_alert_json({**MINIMAL_BUY, "platform": "BINANCE", "inst_type": "CRYPTO"})
        assert r["error"] is False

class TestPlaceholders:
    def test_valid_numeric_placeholder_passes(self):
        r = validate_and_describe_alert_json({**MINIMAL_BUY, "quantity": "{{strategy.market_position_size}}", "price": "{{close}}", "order_type": "LMT"})
        assert r["error"] is False

class TestDescriptionOutput:
    def test_basic_buy_description(self):
        r = validate_and_describe_alert_json(MINIMAL_BUY)
        assert "MARKET BUY order on ES for 2 contract(s) via RITHMIC" in r["description"]

    def test_tradovate_pyramid_description(self):
        r = validate_and_describe_alert_json({**MINIMAL_BUY, "platform": "TRADOVATE", "pyramid": True})
        assert "multiple buy/sell signals will generate multiple buy/sell trades with closing existing ones" in r["description"]
