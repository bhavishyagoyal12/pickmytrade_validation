"""Tests for option-spread capability flags on broker_capabilities."""
import pytest
from pickmytrade_validation.broker_capabilities import (
    BROKER_CAPABILITIES,
    get_broker_capabilities,
    broker_supports_spreads,
    get_supported_spread_strategies,
    get_max_spread_legs,
)


class TestSpreadCapabilitiesIB:
    def test_ib_supports_spreads_flag_true(self):
        assert broker_supports_spreads("IB") is True

    def test_ib_supports_spreads_case_insensitive(self):
        assert broker_supports_spreads("ib") is True
        assert broker_supports_spreads("Ib") is True

    def test_ib_max_spread_legs_is_6(self):
        assert get_max_spread_legs("IB") == 6

    def test_ib_supported_strategies_include_v1_set(self):
        strategies = get_supported_spread_strategies("IB")
        for s in ("vertical", "iron_condor", "iron_butterfly", "butterfly",
                  "calendar", "diagonal", "straddle", "strangle", "custom"):
            assert s in strategies, f"missing strategy: {s}"

    def test_ib_dict_entry_has_new_keys(self):
        ib = BROKER_CAPABILITIES["IB"]
        assert ib["supports_spreads"] is True
        assert isinstance(ib["supported_spread_strategies"], list)
        assert ib["max_spread_legs"] == 6


class TestNonIBBrokersDoNotSupportSpreadsInV1:
    @pytest.mark.parametrize("platform", [
        "TRADIER", "TRADESTATION", "TRADOVATE", "TRADELOCKER", "PROJECTX",
        "BINANCE", "BYBIT", "MATCHTRADER", "RITHMIC",
    ])
    def test_broker_does_not_support_spreads(self, platform):
        assert broker_supports_spreads(platform) is False
        assert get_max_spread_legs(platform) == 0
        assert get_supported_spread_strategies(platform) == []


class TestUnknownPlatform:
    def test_unknown_platform_returns_false(self):
        assert broker_supports_spreads("does_not_exist") is False
        assert get_max_spread_legs("does_not_exist") == 0
        assert get_supported_spread_strategies("does_not_exist") == []

    def test_empty_string_returns_false(self):
        assert broker_supports_spreads("") is False

    def test_none_returns_false(self):
        # Existing helpers tolerate non-string via str() coercion;
        # mirror that behavior — None should not raise
        assert broker_supports_spreads(None) is False  # type: ignore[arg-type]


class TestExistingFunctionalityNotRegressed:
    """The new fields must not break existing helper functions."""
    def test_ib_still_supports_options(self):
        from pickmytrade_validation.broker_capabilities import broker_supports_options
        assert broker_supports_options("IB") is True

    def test_ib_allowed_inst_types_unchanged(self):
        from pickmytrade_validation.broker_capabilities import get_allowed_inst_types
        assert "STK" in get_allowed_inst_types("IB")
        assert "OPT" in get_allowed_inst_types("IB")
        assert "FOP" in get_allowed_inst_types("IB")
