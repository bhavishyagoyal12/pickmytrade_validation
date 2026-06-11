import pytest

from src.pickmytrade_validation import validate_and_describe_alert_json
from src.pickmytrade_validation.validator import validate_and_describe_tradovate_alert_json

# from pickmytrade_validation import validate_and_describe_alert_json

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

    def test_binance_crypto_futures(self):
        r = validate_and_describe_alert_json({**MINIMAL_BUY, "platform": "BINANCE", "inst_type": "CRYPTO"})
        assert r["error"] is False

    def test_bybit_valid_futures(self):
        r = validate_and_describe_alert_json({**MINIMAL_BUY, "platform": "BYBIT", "inst_type": "FUTURES"})
        assert r["error"] is False

class TestPlaceholders:
    def test_valid_numeric_placeholder_passes(self):
        r = validate_and_describe_alert_json({**MINIMAL_BUY, "quantity": "{{strategy.market_position_size}}", "price": "{{close}}", "order_type": "LMT"})
        assert r["error"] is False

    def test_placeholders_disabled_rejects_templates(self):
        r = validate_and_describe_alert_json(
            {**MINIMAL_BUY, "quantity": "{{strategy.market_position_size}}", "price": "{{close}}", "order_type": "LMT"},
            allow_placeholders=False
        )
        assert r["error"] is True
        err_str = str(r["invalid_fields"])
        # Should fail placeholder syntax explicitly
        assert "Placeholders are disabled. Field 'quantity' must be an explicit value." in err_str
        assert "Placeholders are disabled. Field 'price' must be an explicit value." in err_str

    def test_placeholders_enabled_accepts_templates(self):
        # Even explicitly testing True behavior
        r = validate_and_describe_alert_json(
            {**MINIMAL_BUY, "quantity": "{{strategy.market_position_size}}", "price": "{{close}}", "order_type": "LMT"},
            allow_placeholders=True
        )
        assert r["error"] is False

class TestDescriptionOutput:
    def test_basic_buy_description(self):
        r = validate_and_describe_alert_json(MINIMAL_BUY)
        assert "MARKET BUY order on ES for 2 contract(s) via RITHMIC" in r["description"]

    def test_tradovate_pyramid_description(self):
        r = validate_and_describe_alert_json({**MINIMAL_BUY, "platform": "TRADOVATE", "pyramid": True})
        assert "Reverse Order Close: False -> Existing Position (Same Signal): It will not close the trade" in r["description"]

    def test_tradovate_reverse_and_pyramid(self):
        r = validate_and_describe_alert_json({**MINIMAL_BUY, "platform": "TRADOVATE", "pyramid": True, "reverse_order_close": True})
        assert "Reverse Order Close: True, Pyramid: True -> Existing Position (Same Signal): It will not be closed" in r["description"]


class TestTradovateValidation:
    def test_valid_tradovate_types(self):
        # payload = {
        #     "token": "Ct5tEt4t9t8tOt4tJt7tWtQtK",
        #     "symbol": "NQ1!",
        #     "platform": "TRADOVATE",
        #     "data": "buy",
        #     "quantity": 1,
        #     "risk_percentage": 0,
        #     "price": 28000,
        #     "order_type": "MKT",
        #     "tif": "DAY",
        #     "gtd_in_second": 0,
        #     "stp_limit_stp_price": 0,
        #     "tp": 0,
        #     "percentage_tp": 10,
        #     "dollar_tp": 0,
        #     "sl": 0,
        #     "percentage_sl": 10,
        #     "dollar_sl": 0,
        #     "trail": 0,
        #     "trail_stop": 0,
        #     "trail_trigger": 0,
        #     "trail_freq": 0,
        #     "update_tp": False,
        #     "update_sl": False,
        #     "breakeven": 0,
        #     "breakeven_offset": 0,
        #     "pyramid": False,
        #     "same_direction_ignore": True,
        #     "reverse_order_close": False,
        #     "multiple_accounts": [
        #         {
        #             "token": "Ct5tEt4t9t8tOt4tJt7tWtQtK",
        #             "account_id": "DEMO5907012",
        #             "risk_percentage": 0,
        #             "quantity_multiplier": 1,
        #             "connection_name":"TRADOVATE"
        #         }
        #     ],
        #     "strategy_name": "Test Strategy"
        # }
        payload = {
	"strategy_name": "asas",
	"symbol": "NQM6",
	"date": "{{timenow}}",
	"data": "fgh",
	"quantity": 1,
	"risk_percentage": 0,
	"price": "456",
	"gtd_in_second": 2,
	"stp_limit_stp_price": "342344",
	"update_tp": False,
	"update_sl": False,
	"breakeven_offset": 0,
	"token": "3tBtKt1tWtStNtPtUt9tQt4tA",
	"pyramid": False,
	"same_direction_ignore": False,
	"reverse_order_close": True,
	"order_type": "STPLMT",
	"advance_tp_sl": [
		{
			"quantity": 1,
			"tp": 0,
			"percentage_tp": 0,
			"dollar_tp": 14,
			"sl": 0,
			"percentage_sl": 0,
			"dollar_sl": 1,
			"breakeven": 1,
			"breakeven_offset": 3,
			"trail": 1,
			"trail_stop": 1,
			"trail_trigger": 1,
			"trail_freq": 1
		}
	],
	"multiple_accounts": [
		{
			"token": "3tBtKt1tWtStNtPtUt9tQt4tA",
			"account_id": "DEMO6376471",
			"risk_percentage": 0,
			"quantity_multiplier": 1
		}
	]
}
        r = validate_and_describe_tradovate_alert_json(payload)
        print(f"response {r['invalid_fields']}")
        assert r["error"] is False

    # def test_invalid_tradovate_types(self):
    #     base_payload = {
    #         "token": "Ct5tEt4t9t8tOt4tJt7tWtQtK",
    #         "symbol": "NQ1!",
    #         "platform": "TRADOVATE",
    #         "data": "buy",
    #         "quantity": 1,
    #         "price": 28000,
    #         "order_type": "MKT",
    #     }
    #
    #     # Test invalid string type (strategy_name)
    #     r = validate_and_describe_alert_json({**base_payload, "strategy_name": 123})
    #     assert r["error"] is True
    #     assert any("strategy_name" in f and "string" in f for f in r["invalid_fields"])
    #
    #     # Test invalid string type (tif)
    #     r = validate_and_describe_alert_json({**base_payload, "tif": True})
    #     assert r["error"] is True
    #     assert any("tif" in f and "string" in f for f in r["invalid_fields"])
    #
    #     # Test invalid numeric type (gtd_in_second)
    #     r = validate_and_describe_alert_json({**base_payload, "gtd_in_second": "not-a-number"})
    #     assert r["error"] is True
    #     assert any("gtd_in_second" in f and "number" in f for f in r["invalid_fields"])
    #
    #     # Test invalid numeric type (stp_limit_stp_price)
    #     r = validate_and_describe_alert_json({**base_payload, "stp_limit_stp_price": "not-a-number"})
    #     assert r["error"] is True
    #     assert any("stp_limit_stp_price" in f and "number" in f for f in r["invalid_fields"])
    #
    #     # Test invalid numeric type (trail_freq)
    #     r = validate_and_describe_alert_json({**base_payload, "trail_freq": "not-a-number"})
    #     assert r["error"] is True
    #     assert any("trail_freq" in f and "number" in f for f in r["invalid_fields"])
    #
    #     # Test invalid numeric type (breakeven_offset)
    #     r = validate_and_describe_alert_json({**base_payload, "breakeven_offset": "not-a-number"})
    #     assert r["error"] is True
    #     assert any("breakeven_offset" in f and "number" in f for f in r["invalid_fields"])
    #
    #     # Test invalid boolean type (same_direction_ignore)
    #     r = validate_and_describe_alert_json({**base_payload, "same_direction_ignore": "yes"})
    #     assert r["error"] is True
    #     assert any("same_direction_ignore" in f and "boolean" in f for f in r["invalid_fields"])
    #
    #     # Test invalid boolean type (reverse_order_close)
    #     r = validate_and_describe_alert_json({**base_payload, "reverse_order_close": "yes"})
    #     assert r["error"] is True
    #     assert any("reverse_order_close" in f and "boolean" in f for f in r["invalid_fields"])
    #
    #     # Test invalid quantity_multiplier in multiple_accounts
    #     payload_with_acc = {
    #         **base_payload,
    #         "multiple_accounts": [
    #             {
    #                 "token": "Ct5tEt4t9t8tOt4tJt7tWtQtK",
    #                 "account_id": "DEMO5907012",
    #                 "risk_percentage": 0,
    #                 "quantity_multiplier": "one"
    #             }
    #         ]
    #     }
    #     r = validate_and_describe_alert_json(payload_with_acc)
    #     assert r["error"] is True
    #     assert any("multiple_accounts[0].quantity_multiplier" in f and "number" in f for f in r["invalid_fields"])


if __name__ == "__main__":
    TestTradovateValidation().test_valid_tradovate_types()