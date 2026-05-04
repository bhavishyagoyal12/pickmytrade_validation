"""Tests for the spread_validator pure-function gate."""
import pytest
from pickmytrade_validation.spread_validator import (
    validate_spread_payload,
    SpreadValidationError,
)


VALID_IRON_CONDOR = {
    "token": "test-token",
    "broker": "IB",
    "strategy": "iron_condor",
    "underlying": "SPY",
    "side": "sell",
    "expiration": {"mode": "dte", "dte": 45},
    "legs_mode": "auto",
    "auto": {
        "short_call_delta": 16,
        "short_put_delta": 16,
        "call_wing_width": 5,
        "put_wing_width": 5,
    },
    "quantity": 1,
    "pricing": {"mode": "mid"},
    "manage": "tasty_default",
}


VALID_VERTICAL = {
    "token": "test-token",
    "broker": "IB",
    "strategy": "vertical",
    "underlying": "SPY",
    "side": "sell",
    "expiration": {"mode": "dte", "dte": 45},
    "legs_mode": "auto",
    "auto": {"right": "put", "short_delta": 30, "wing_width": 5},
    "quantity": 1,
    "pricing": {"mode": "mid"},
    "manage": "tasty_default",
}


class TestIronCondorValidation:
    def test_valid_iron_condor_passes(self):
        validate_spread_payload(VALID_IRON_CONDOR)

    def test_iron_condor_requires_4_delta_fields(self):
        payload = dict(VALID_IRON_CONDOR)
        payload["auto"] = {"short_call_delta": 16}
        with pytest.raises(SpreadValidationError, match="short_put_delta"):
            validate_spread_payload(payload)

    def test_invalid_strategy_rejected(self):
        payload = dict(VALID_IRON_CONDOR)
        payload["strategy"] = "not_a_real_strategy"
        with pytest.raises(SpreadValidationError, match="strategy"):
            validate_spread_payload(payload)

    def test_unsupported_broker_rejected(self):
        payload = dict(VALID_IRON_CONDOR)
        payload["broker"] = "TRADOVATE"
        with pytest.raises(SpreadValidationError, match="does not support spreads"):
            validate_spread_payload(payload)

    def test_quantity_must_be_positive(self):
        payload = dict(VALID_IRON_CONDOR)
        payload["quantity"] = 0
        with pytest.raises(SpreadValidationError, match="quantity"):
            validate_spread_payload(payload)


class TestVerticalValidation:
    def test_valid_vertical_passes(self):
        validate_spread_payload(VALID_VERTICAL)

    def test_vertical_requires_right(self):
        payload = dict(VALID_VERTICAL)
        payload["auto"] = {"short_delta": 30, "wing_width": 5}
        with pytest.raises(SpreadValidationError, match="right"):
            validate_spread_payload(payload)


class TestExpiration:
    def test_dte_mode_requires_dte_field(self):
        payload = dict(VALID_VERTICAL)
        payload["expiration"] = {"mode": "dte"}
        with pytest.raises(SpreadValidationError, match="dte"):
            validate_spread_payload(payload)

    def test_date_mode_requires_iso_date(self):
        payload = dict(VALID_VERTICAL)
        payload["expiration"] = {"mode": "date", "date": "not-a-date"}
        with pytest.raises(SpreadValidationError, match="date"):
            validate_spread_payload(payload)

    def test_alias_mode_requires_known_alias(self):
        payload = dict(VALID_VERTICAL)
        payload["expiration"] = {"mode": "alias", "alias": "bogus"}
        with pytest.raises(SpreadValidationError, match="alias"):
            validate_spread_payload(payload)

    def test_invalid_expiration_mode_rejected(self):
        payload = dict(VALID_VERTICAL)
        payload["expiration"] = {"mode": "telepathy"}
        with pytest.raises(SpreadValidationError, match="mode"):
            validate_spread_payload(payload)


class TestExplicitLegs:
    def test_explicit_legs_mode_accepted(self):
        payload = {
            "token": "test-token",
            "broker": "IB",
            "strategy": "iron_condor",
            "underlying": "SPY",
            "side": "sell",
            "expiration": {"mode": "date", "date": "2026-06-20"},
            "legs_mode": "explicit",
            "legs": [
                {"side": "sell", "right": "put", "strike": 480, "ratio": 1},
                {"side": "buy",  "right": "put", "strike": 475, "ratio": 1},
                {"side": "sell", "right": "call", "strike": 520, "ratio": 1},
                {"side": "buy",  "right": "call", "strike": 525, "ratio": 1},
            ],
            "quantity": 1,
            "pricing": {"mode": "mid"},
            "manage": "tasty_default",
        }
        validate_spread_payload(payload)

    def test_iron_condor_explicit_must_have_4_legs(self):
        payload = {
            "token": "test-token",
            "broker": "IB",
            "strategy": "iron_condor",
            "underlying": "SPY",
            "side": "sell",
            "expiration": {"mode": "date", "date": "2026-06-20"},
            "legs_mode": "explicit",
            "legs": [
                {"side": "sell", "right": "put", "strike": 480, "ratio": 1},
                {"side": "buy",  "right": "put", "strike": 475, "ratio": 1},
            ],
            "quantity": 1,
            "pricing": {"mode": "mid"},
            "manage": "tasty_default",
        }
        with pytest.raises(SpreadValidationError, match="4 legs"):
            validate_spread_payload(payload)

    def test_vertical_explicit_must_have_2_legs(self):
        payload = {
            "token": "test-token",
            "broker": "IB",
            "strategy": "vertical",
            "underlying": "SPY",
            "side": "sell",
            "expiration": {"mode": "date", "date": "2026-06-20"},
            "legs_mode": "explicit",
            "legs": [
                {"side": "sell", "right": "put", "strike": 480, "ratio": 1},
            ],
            "quantity": 1,
            "pricing": {"mode": "mid"},
            "manage": "tasty_default",
        }
        with pytest.raises(SpreadValidationError, match="2 legs"):
            validate_spread_payload(payload)

    def test_explicit_leg_missing_required_field(self):
        payload = {
            "token": "test-token",
            "broker": "IB",
            "strategy": "vertical",
            "underlying": "SPY",
            "side": "sell",
            "expiration": {"mode": "date", "date": "2026-06-20"},
            "legs_mode": "explicit",
            "legs": [
                {"side": "sell", "right": "put", "strike": 480},  # missing ratio
                {"side": "buy",  "right": "put", "strike": 475, "ratio": 1},
            ],
            "quantity": 1,
            "pricing": {"mode": "mid"},
            "manage": "tasty_default",
        }
        with pytest.raises(SpreadValidationError, match="ratio"):
            validate_spread_payload(payload)


class TestRequiredTopLevelFields:
    @pytest.mark.parametrize("missing", [
        "token", "broker", "strategy", "underlying", "side",
        "expiration", "legs_mode", "quantity", "pricing", "manage",
    ])
    def test_missing_required_field_rejected(self, missing):
        payload = dict(VALID_IRON_CONDOR)
        payload.pop(missing)
        with pytest.raises(SpreadValidationError, match=missing):
            validate_spread_payload(payload)


class TestSideEnum:
    def test_invalid_side_rejected(self):
        payload = dict(VALID_VERTICAL)
        payload["side"] = "hold"
        with pytest.raises(SpreadValidationError, match="side"):
            validate_spread_payload(payload)


class TestLegsMode:
    def test_legs_mode_auto_requires_auto_block(self):
        payload = dict(VALID_VERTICAL)
        payload["legs_mode"] = "auto"
        payload.pop("auto", None)
        with pytest.raises(SpreadValidationError, match="auto"):
            validate_spread_payload(payload)

    def test_legs_mode_explicit_requires_legs_block(self):
        payload = dict(VALID_VERTICAL)
        payload["legs_mode"] = "explicit"
        payload.pop("auto", None)
        with pytest.raises(SpreadValidationError, match="legs"):
            validate_spread_payload(payload)

    def test_invalid_legs_mode_rejected(self):
        payload = dict(VALID_VERTICAL)
        payload["legs_mode"] = "psychic"
        with pytest.raises(SpreadValidationError, match="legs_mode"):
            validate_spread_payload(payload)


class TestUnsupportedStrategy:
    def test_strategy_not_in_broker_supported_list(self, monkeypatch):
        # IB has all 9 strategies enabled in v1, so to force this test we use
        # a broker whose supported list is empty (all non-IB brokers).
        # But broker_supports_spreads is False for them, so we'd hit that gate first.
        # Instead, use IB with a strategy that's deliberately not in the list.
        # Since IB supports all 9 v1 strategies, we test by patching the helper.
        from pickmytrade_validation import spread_validator
        from pickmytrade_validation import broker_capabilities as bc
        # Temporarily restrict IB's strategy list to verify the gate works
        original = bc.BROKER_CAPABILITIES["IB"]["supported_spread_strategies"]
        bc.BROKER_CAPABILITIES["IB"]["supported_spread_strategies"] = ["vertical"]
        try:
            payload = dict(VALID_IRON_CONDOR)  # iron_condor not in restricted list
            with pytest.raises(SpreadValidationError, match="iron_condor"):
                validate_spread_payload(payload)
        finally:
            bc.BROKER_CAPABILITIES["IB"]["supported_spread_strategies"] = original
