"""Tests for the unified per-leg spread_validator gate (2026-07-14 schema).

Covers the finalized canonical strategy JSON: unified per-leg strike selector
(absolute / delta / offset / relative), relative-leg topology, delta 0-100
(TI-1), pricing (mid / best_fill / manual + slippage + signed max_net), top-level
time_in_force, multiple_accounts sizing exclusivity, tp/sl/exit/safety, and the
removal of the closed strategy allow-list (TI-2).
"""
import copy
import pytest
from pickmytrade_validation.spread_validator import (
    validate_spread_payload,
    SpreadValidationError,
)


# A valid canonical iron condor: 2 delta shorts + 2 relative wings.
VALID_IRON_CONDOR = {
    "token": "test-token",
    "broker": "IB",
    "inst_type": "OPT",
    "name": "SPY_IronCondor_16D_5wide",
    "description": "45 DTE SPY iron condor",
    "connection_name": "Account1",
    "account_id": "DU111",
    "quantity": 1,
    "multiple_accounts": [
        {"token": "USER_TOKEN", "connection_name": "Account1", "account_id": "DU111", "quantity_multiplier": 1},
        {"token": "USER_TOKEN", "connection_name": "Account2", "account_id": "DU222", "quantity_multiplier": 2},
        {"token": "USER_TOKEN", "connection_name": "Account3", "account_id": "DU333", "fixed_quantity": 5},
    ],
    "underlying": "SPY",
    "side": "sell",
    "expiration": {"mode": "dte", "dte": 45, "dte_tolerance": 7},
    "legs": [
        {"id": "short_put", "side": "sell", "right": "put", "strike": {"mode": "delta", "delta": 16}, "ratio": 1},
        {"id": "long_put", "side": "buy", "right": "put", "strike": {"mode": "relative", "ref": "short_put", "offset": -5, "unit": "usd"}, "ratio": 1},
        {"id": "short_call", "side": "sell", "right": "call", "strike": {"mode": "delta", "delta": 16}, "ratio": 1},
        {"id": "long_call", "side": "buy", "right": "call", "strike": {"mode": "relative", "ref": "short_call", "offset": 5, "unit": "usd"}, "ratio": 1},
    ],
    "pricing": {"mode": "best_fill", "slippage": 0.05, "slippage_unit": "usd", "max_net": -1.20, "limit_price": None},
    "time_in_force": "DAY",
    "tp": {"type": "percent_of_credit", "value": 50},
    "sl": {"type": "multiple_of_credit", "value": 2},
    "exit": {"dte": 21, "time_of_day": "15:55:00", "tz": "America/New_York"},
    "safety": {"risk_defined_only": True, "max_legs": 4, "non_guaranteed": False},
    "strategy_type": "iron_condor",
}


def payload(**overrides):
    p = copy.deepcopy(VALID_IRON_CONDOR)
    p.update(overrides)
    return p


def one_leg(strike, **extra):
    leg = {"id": "L1", "side": "buy", "right": "call", "strike": strike, "ratio": 1}
    leg.update(extra)
    return leg


def two_leg_payload(leg0_strike, leg1_strike, **top):
    p = payload(**top)
    p["legs"] = [
        {"id": "a", "side": "sell", "right": "call", "strike": leg0_strike, "ratio": 1},
        {"id": "b", "side": "buy", "right": "call", "strike": leg1_strike, "ratio": 1},
    ]
    # simplify: drop the multiple_accounts to isolate leg testing
    p["safety"] = {"max_legs": 6}
    return p


# --------------------------------------------------------------------------
# Happy path
# --------------------------------------------------------------------------

class TestHappyPath:
    def test_canonical_iron_condor_passes(self):
        assert validate_spread_payload(VALID_IRON_CONDOR) is None

    def test_minimal_two_leg_absolute_passes(self):
        p = two_leg_payload({"mode": "absolute", "value": 520}, {"mode": "absolute", "value": 525})
        assert validate_spread_payload(p) is None

    def test_time_in_force_optional_defaults(self):
        p = payload()
        del p["time_in_force"]
        assert validate_spread_payload(p) is None


# --------------------------------------------------------------------------
# Top-level required / broker / side / quantity
# --------------------------------------------------------------------------

class TestTopLevel:
    @pytest.mark.parametrize("field", ["token", "broker", "underlying", "side", "expiration", "quantity", "pricing", "legs"])
    def test_missing_required_field_rejects(self, field):
        p = payload()
        del p[field]
        with pytest.raises(SpreadValidationError):
            validate_spread_payload(p)

    def test_non_dict_payload_rejects(self):
        with pytest.raises(SpreadValidationError):
            validate_spread_payload(["not", "a", "dict"])

    def test_non_ib_broker_rejects(self):
        with pytest.raises(SpreadValidationError, match="does not support spreads"):
            validate_spread_payload(payload(broker="TRADOVATE"))

    def test_bad_side_rejects(self):
        with pytest.raises(SpreadValidationError, match="side"):
            validate_spread_payload(payload(side="long"))

    @pytest.mark.parametrize("q", [0, -1, 1.5, True, "1"])
    def test_bad_quantity_rejects(self, q):
        with pytest.raises(SpreadValidationError, match="quantity"):
            validate_spread_payload(payload(quantity=q))


# --------------------------------------------------------------------------
# Strike selector modes
# --------------------------------------------------------------------------

class TestStrikeSelector:
    def test_absolute_positive_ok(self):
        p = two_leg_payload({"mode": "absolute", "value": 100}, {"mode": "absolute", "value": 105})
        assert validate_spread_payload(p) is None

    @pytest.mark.parametrize("bad", [0, -5, "100", True, None])
    def test_absolute_non_positive_rejects(self, bad):
        p = two_leg_payload({"mode": "absolute", "value": bad}, {"mode": "absolute", "value": 105})
        with pytest.raises(SpreadValidationError, match="strike.value"):
            validate_spread_payload(p)

    def test_unknown_mode_rejects(self):
        p = two_leg_payload({"mode": "wizardry", "value": 1}, {"mode": "absolute", "value": 105})
        with pytest.raises(SpreadValidationError, match="strike.mode"):
            validate_spread_payload(p)

    def test_strike_not_object_rejects(self):
        p = two_leg_payload(500, {"mode": "absolute", "value": 105})
        with pytest.raises(SpreadValidationError, match="strike"):
            validate_spread_payload(p)

    def test_offset_valid_ok(self):
        p = two_leg_payload({"mode": "offset", "anchor": "atm", "offset": 1, "unit": "steps"},
                            {"mode": "offset", "anchor": "spot", "offset": -2, "unit": "usd"})
        assert validate_spread_payload(p) is None

    def test_offset_zero_ok_for_offset_mode(self):
        # offset==0 is ATM itself for offset mode (only relative rejects 0).
        p = two_leg_payload({"mode": "offset", "anchor": "atm", "offset": 0, "unit": "steps"},
                            {"mode": "absolute", "value": 105})
        assert validate_spread_payload(p) is None

    def test_offset_bad_anchor_rejects(self):
        p = two_leg_payload({"mode": "offset", "anchor": "moon", "offset": 1, "unit": "steps"},
                            {"mode": "absolute", "value": 105})
        with pytest.raises(SpreadValidationError, match="strike.anchor"):
            validate_spread_payload(p)

    def test_offset_bad_unit_rejects(self):
        p = two_leg_payload({"mode": "offset", "anchor": "atm", "offset": 1, "unit": "furlongs"},
                            {"mode": "absolute", "value": 105})
        with pytest.raises(SpreadValidationError, match="strike.unit"):
            validate_spread_payload(p)

    def test_offset_non_number_rejects(self):
        p = two_leg_payload({"mode": "offset", "anchor": "atm", "offset": "1", "unit": "steps"},
                            {"mode": "absolute", "value": 105})
        with pytest.raises(SpreadValidationError, match="strike.offset"):
            validate_spread_payload(p)


# --------------------------------------------------------------------------
# TI-1 delta 0-100 scale
# --------------------------------------------------------------------------

class TestDeltaScale:
    @pytest.mark.parametrize("d", [1, 16, 16.5, 100])
    def test_delta_in_range_ok(self, d):
        p = two_leg_payload({"mode": "delta", "delta": d}, {"mode": "absolute", "value": 105})
        assert validate_spread_payload(p) is None

    @pytest.mark.parametrize("d", [0, -5, 101, 150])
    def test_delta_out_of_range_rejects(self, d):
        p = two_leg_payload({"mode": "delta", "delta": d}, {"mode": "absolute", "value": 105})
        with pytest.raises(SpreadValidationError, match="0-100"):
            validate_spread_payload(p)

    @pytest.mark.parametrize("d", [0.16, 0.5, 0.99])
    def test_delta_fraction_rejects(self, d):
        p = two_leg_payload({"mode": "delta", "delta": d}, {"mode": "absolute", "value": 105})
        with pytest.raises(SpreadValidationError, match="fraction"):
            validate_spread_payload(p)

    def test_delta_non_number_rejects(self):
        p = two_leg_payload({"mode": "delta", "delta": "16"}, {"mode": "absolute", "value": 105})
        with pytest.raises(SpreadValidationError, match="strike.delta"):
            validate_spread_payload(p)


# --------------------------------------------------------------------------
# Relative-leg topology
# --------------------------------------------------------------------------

class TestRelativeTopology:
    def test_relative_signed_negative_offset_ok(self):
        p = two_leg_payload({"mode": "absolute", "value": 100},
                            {"mode": "relative", "ref": "a", "offset": -5, "unit": "usd"})
        assert validate_spread_payload(p) is None

    def test_missing_ref_rejects(self):
        p = two_leg_payload({"mode": "absolute", "value": 100},
                            {"mode": "relative", "ref": "does_not_exist", "offset": 5, "unit": "usd"})
        with pytest.raises(SpreadValidationError, match="unknown leg id"):
            validate_spread_payload(p)

    def test_ref_missing_field_rejects(self):
        p = two_leg_payload({"mode": "absolute", "value": 100},
                            {"mode": "relative", "offset": 5, "unit": "usd"})
        with pytest.raises(SpreadValidationError, match="strike.ref"):
            validate_spread_payload(p)

    def test_self_ref_rejects(self):
        p = two_leg_payload({"mode": "absolute", "value": 100},
                            {"mode": "relative", "ref": "b", "offset": 5, "unit": "usd"})
        with pytest.raises(SpreadValidationError, match="own leg"):
            validate_spread_payload(p)

    def test_relative_to_relative_chain_rejects(self):
        p = payload()
        p["safety"] = {"max_legs": 6}
        p["legs"] = [
            {"id": "anchor", "side": "sell", "right": "call", "strike": {"mode": "absolute", "value": 100}, "ratio": 1},
            {"id": "mid", "side": "buy", "right": "call", "strike": {"mode": "relative", "ref": "anchor", "offset": 5, "unit": "usd"}, "ratio": 1},
            {"id": "chain", "side": "buy", "right": "call", "strike": {"mode": "relative", "ref": "mid", "offset": 5, "unit": "usd"}, "ratio": 1},
        ]
        with pytest.raises(SpreadValidationError, match="relative leg"):
            validate_spread_payload(p)

    def test_relative_offset_zero_collapse_rejects(self):
        p = two_leg_payload({"mode": "absolute", "value": 100},
                            {"mode": "relative", "ref": "a", "offset": 0, "unit": "usd"})
        with pytest.raises(SpreadValidationError, match="collapse"):
            validate_spread_payload(p)

    def test_relative_bad_unit_rejects(self):
        p = two_leg_payload({"mode": "absolute", "value": 100},
                            {"mode": "relative", "ref": "a", "offset": 5, "unit": "bananas"})
        with pytest.raises(SpreadValidationError, match="strike.unit"):
            validate_spread_payload(p)


# --------------------------------------------------------------------------
# Leg-level required fields, ids, count range
# --------------------------------------------------------------------------

class TestLegs:
    def test_missing_id_rejects(self):
        p = payload()
        p["safety"] = {"max_legs": 6}
        p["legs"] = [
            {"side": "sell", "right": "call", "strike": {"mode": "absolute", "value": 100}, "ratio": 1},
            {"id": "b", "side": "buy", "right": "call", "strike": {"mode": "absolute", "value": 105}, "ratio": 1},
        ]
        with pytest.raises(SpreadValidationError, match="id"):
            validate_spread_payload(p)

    def test_duplicate_id_rejects(self):
        p = two_leg_payload({"mode": "absolute", "value": 100}, {"mode": "absolute", "value": 105})
        p["legs"][1]["id"] = "a"
        with pytest.raises(SpreadValidationError, match="duplicates"):
            validate_spread_payload(p)

    def test_empty_id_rejects(self):
        p = two_leg_payload({"mode": "absolute", "value": 100}, {"mode": "absolute", "value": 105})
        p["legs"][0]["id"] = "   "
        with pytest.raises(SpreadValidationError, match="id"):
            validate_spread_payload(p)

    def test_bad_ratio_rejects(self):
        p = two_leg_payload({"mode": "absolute", "value": 100}, {"mode": "absolute", "value": 105})
        p["legs"][0]["ratio"] = 0
        with pytest.raises(SpreadValidationError, match="ratio"):
            validate_spread_payload(p)

    def test_bad_right_rejects(self):
        p = two_leg_payload({"mode": "absolute", "value": 100}, {"mode": "absolute", "value": 105})
        p["legs"][0]["right"] = "future"
        with pytest.raises(SpreadValidationError, match="right"):
            validate_spread_payload(p)

    def test_one_leg_rejects(self):
        p = payload()
        p["legs"] = [{"id": "a", "side": "sell", "right": "call", "strike": {"mode": "absolute", "value": 100}, "ratio": 1}]
        with pytest.raises(SpreadValidationError, match="at least 2 legs"):
            validate_spread_payload(p)

    def test_over_broker_max_rejects(self):
        # 7 legs, IB cap is 6. Raise safety cap so the broker cap is the binding one.
        p = payload()
        p["safety"] = {"max_legs": 10}
        p["legs"] = [
            {"id": f"L{i}", "side": "buy", "right": "call", "strike": {"mode": "absolute", "value": 100 + i}, "ratio": 1}
            for i in range(7)
        ]
        with pytest.raises(SpreadValidationError, match="at most 6"):
            validate_spread_payload(p)

    def test_safety_max_legs_is_binding_when_lower(self):
        # safety.max_legs=3 is lower than IB's 6, so 4 legs must reject.
        p = payload()  # canonical has 4 legs
        p["multiple_accounts"] = []
        p["safety"] = {"max_legs": 3}
        with pytest.raises(SpreadValidationError, match="at most 3"):
            validate_spread_payload(p)

    def test_four_legs_within_caps_ok(self):
        p = payload()
        p["safety"] = {"max_legs": 4}
        assert validate_spread_payload(p) is None


# --------------------------------------------------------------------------
# Leg-level expiration override
# --------------------------------------------------------------------------

class TestLegExpiration:
    def test_valid_leg_expiration_override_ok(self):
        p = two_leg_payload({"mode": "absolute", "value": 100}, {"mode": "absolute", "value": 105})
        p["legs"][0]["expiration"] = {"mode": "date", "date": "2026-12-18"}
        assert validate_spread_payload(p) is None

    def test_invalid_leg_expiration_rejects(self):
        p = two_leg_payload({"mode": "absolute", "value": 100}, {"mode": "absolute", "value": 105})
        p["legs"][0]["expiration"] = {"mode": "date", "date": "not-a-date"}
        with pytest.raises(SpreadValidationError, match=r"legs\[0\].expiration"):
            validate_spread_payload(p)


# --------------------------------------------------------------------------
# Expiration dte upper bound + dte_tolerance
# --------------------------------------------------------------------------

class TestExpirationBounds:
    def test_dte_at_bound_ok(self):
        assert validate_spread_payload(payload(expiration={"mode": "dte", "dte": 1000})) is None

    def test_dte_over_bound_rejects(self):
        with pytest.raises(SpreadValidationError, match="at most 1000"):
            validate_spread_payload(payload(expiration={"mode": "dte", "dte": 1001}))

    def test_negative_dte_still_rejects(self):
        with pytest.raises(SpreadValidationError, match="dte"):
            validate_spread_payload(payload(expiration={"mode": "dte", "dte": -1}))

    def test_good_dte_tolerance_ok(self):
        assert validate_spread_payload(
            payload(expiration={"mode": "dte", "dte": 45, "dte_tolerance": 7})
        ) is None

    def test_negative_dte_tolerance_rejects(self):
        with pytest.raises(SpreadValidationError, match="dte_tolerance"):
            validate_spread_payload(payload(expiration={"mode": "dte", "dte": 45, "dte_tolerance": -1}))

    @pytest.mark.parametrize("tol", [1.5, "7", True])
    def test_non_int_dte_tolerance_rejects(self, tol):
        with pytest.raises(SpreadValidationError, match="dte_tolerance"):
            validate_spread_payload(payload(expiration={"mode": "dte", "dte": 45, "dte_tolerance": tol}))


# --------------------------------------------------------------------------
# Pricing
# --------------------------------------------------------------------------

class TestPricing:
    def test_best_fill_ok(self):
        assert validate_spread_payload(payload(pricing={"mode": "best_fill"})) is None

    def test_mid_ok(self):
        assert validate_spread_payload(payload(pricing={"mode": "mid"})) is None

    def test_smart_mode_now_rejects(self):
        with pytest.raises(SpreadValidationError, match="pricing.mode"):
            validate_spread_payload(payload(pricing={"mode": "smart"}))

    def test_market_mode_now_rejects(self):
        with pytest.raises(SpreadValidationError, match="pricing.mode"):
            validate_spread_payload(payload(pricing={"mode": "market"}))

    def test_manual_without_limit_rejects(self):
        with pytest.raises(SpreadValidationError, match="limit_price"):
            validate_spread_payload(payload(pricing={"mode": "manual"}))

    def test_manual_with_limit_ok(self):
        # Pure pricing check: a positive limit is a DEBIT open, and the base
        # payload's leftover credit tp/sl would (correctly) be a basis
        # contradiction against it, so drop them to isolate the pricing rule.
        p = payload(pricing={"mode": "manual", "limit_price": 1.25})
        p.pop("tp", None)
        p.pop("sl", None)
        assert validate_spread_payload(p) is None

    def test_manual_negative_limit_ok(self):
        # A negative limit is a CREDIT open, consistent with the base credit tp/sl.
        assert validate_spread_payload(payload(pricing={"mode": "manual", "limit_price": -1.25})) is None

    def test_signed_credit_max_net_ok(self):
        assert validate_spread_payload(payload(pricing={"mode": "best_fill", "max_net": -1.20})) is None

    def test_bad_slippage_unit_rejects(self):
        with pytest.raises(SpreadValidationError, match="slippage_unit"):
            validate_spread_payload(payload(pricing={"mode": "mid", "slippage": 0.05, "slippage_unit": "points"}))

    def test_negative_slippage_rejects(self):
        with pytest.raises(SpreadValidationError, match="slippage"):
            validate_spread_payload(payload(pricing={"mode": "mid", "slippage": -0.05}))

    def test_non_number_max_net_rejects(self):
        with pytest.raises(SpreadValidationError, match="max_net"):
            validate_spread_payload(payload(pricing={"mode": "mid", "max_net": "cheap"}))


# --------------------------------------------------------------------------
# time_in_force
# --------------------------------------------------------------------------

class TestTimeInForce:
    @pytest.mark.parametrize("tif", ["DAY", "GTC"])
    def test_valid_tif_ok(self, tif):
        assert validate_spread_payload(payload(time_in_force=tif)) is None

    @pytest.mark.parametrize("tif", ["FOK", "IOC", "day", "gtc"])
    def test_bad_tif_rejects(self, tif):
        with pytest.raises(SpreadValidationError, match="time_in_force"):
            validate_spread_payload(payload(time_in_force=tif))


# --------------------------------------------------------------------------
# multiple_accounts
# --------------------------------------------------------------------------

class TestMultipleAccounts:
    def test_valid_multiplier_ok(self):
        p = payload(multiple_accounts=[
            {"token": "T", "connection_name": "C", "account_id": "A", "quantity_multiplier": 2},
        ])
        assert validate_spread_payload(p) is None

    def test_valid_fixed_quantity_ok(self):
        p = payload(multiple_accounts=[
            {"token": "T", "connection_name": "C", "account_id": "A", "fixed_quantity": 5},
        ])
        assert validate_spread_payload(p) is None

    def test_both_sizing_fields_rejects(self):
        p = payload(multiple_accounts=[
            {"token": "T", "connection_name": "C", "account_id": "A", "quantity_multiplier": 2, "fixed_quantity": 5},
        ])
        with pytest.raises(SpreadValidationError, match="only one of"):
            validate_spread_payload(p)

    def test_neither_sizing_field_ok(self):
        # Both-absent is allowed (defaults to multiplier 1 downstream).
        p = payload(multiple_accounts=[
            {"token": "T", "connection_name": "C", "account_id": "A"},
        ])
        assert validate_spread_payload(p) is None

    @pytest.mark.parametrize("field", ["token", "connection_name", "account_id"])
    def test_missing_required_entry_field_rejects(self, field):
        entry = {"token": "T", "connection_name": "C", "account_id": "A", "quantity_multiplier": 1}
        del entry[field]
        with pytest.raises(SpreadValidationError, match=field):
            validate_spread_payload(payload(multiple_accounts=[entry]))

    def test_non_list_rejects(self):
        with pytest.raises(SpreadValidationError, match="multiple_accounts"):
            validate_spread_payload(payload(multiple_accounts={"not": "a list"}))

    def test_zero_multiplier_rejects(self):
        p = payload(multiple_accounts=[
            {"token": "T", "connection_name": "C", "account_id": "A", "quantity_multiplier": 0},
        ])
        with pytest.raises(SpreadValidationError, match="quantity_multiplier"):
            validate_spread_payload(p)

    def test_misspelled_sizing_key_rejects(self):
        # A typo like "quantity_multipler" must be caught, not silently ignored.
        p = payload(multiple_accounts=[
            {"token": "T", "connection_name": "C", "account_id": "A", "quantity_multipler": 2},
        ])
        with pytest.raises(SpreadValidationError, match="unknown key"):
            validate_spread_payload(p)

    def test_unknown_extra_key_rejects(self):
        p = payload(multiple_accounts=[
            {"token": "T", "connection_name": "C", "account_id": "A", "surprise": 1},
        ])
        with pytest.raises(SpreadValidationError, match="unknown key"):
            validate_spread_payload(p)


# --------------------------------------------------------------------------
# tp / sl / exit / safety thin checks
# --------------------------------------------------------------------------

class TestTpSlExitSafety:
    def test_negative_tp_value_rejects(self):
        with pytest.raises(SpreadValidationError, match="tp.value"):
            validate_spread_payload(payload(tp={"type": "percent_of_credit", "value": -1}))

    def test_valid_tp_sl_types_ok(self):
        assert validate_spread_payload(payload(
            tp={"type": "percent_of_credit", "value": 50},
            sl={"type": "multiple_of_credit", "value": 2},
        )) is None

    def test_bad_tp_type_rejects(self):
        with pytest.raises(SpreadValidationError, match="tp.type"):
            validate_spread_payload(payload(tp={"type": "bogus", "value": 50}))

    def test_bad_sl_type_rejects(self):
        with pytest.raises(SpreadValidationError, match="sl.type"):
            validate_spread_payload(payload(sl={"type": "bogus", "value": 2}))

    def test_bad_exit_dte_rejects(self):
        with pytest.raises(SpreadValidationError, match="exit.dte"):
            validate_spread_payload(payload(exit={"dte": -3}))

    @pytest.mark.parametrize("tod", ["15:55", "15:55:00", "00:00", "09:30:15", "23:59:59"])
    def test_valid_time_of_day_ok(self, tod):
        assert validate_spread_payload(payload(exit={"dte": 21, "time_of_day": tod})) is None

    @pytest.mark.parametrize("tod", ["25:99", "5pm", "9", "3:5", "24:00", "15:60", "12:00:60", "15:55 ", "1555"])
    def test_bad_time_of_day_rejects(self, tod):
        with pytest.raises(SpreadValidationError, match="time_of_day"):
            validate_spread_payload(payload(exit={"dte": 21, "time_of_day": tod}))

    def test_non_string_time_of_day_rejects(self):
        with pytest.raises(SpreadValidationError, match="time_of_day"):
            validate_spread_payload(payload(exit={"dte": 21, "time_of_day": 1555}))

    def test_good_exit_tz_ok(self):
        assert validate_spread_payload(
            payload(exit={"dte": 21, "time_of_day": "15:55", "tz": "America/New_York"})
        ) is None

    @pytest.mark.parametrize("tz", ["", "   ", "Not/AZone", "Mars/Olympus"])
    def test_bad_exit_tz_rejects(self, tz):
        with pytest.raises(SpreadValidationError, match="tz"):
            validate_spread_payload(payload(exit={"dte": 21, "tz": tz}))

    def test_non_string_exit_tz_rejects(self):
        with pytest.raises(SpreadValidationError, match="tz"):
            validate_spread_payload(payload(exit={"dte": 21, "tz": 5}))

    def test_bad_safety_max_legs_type_rejects(self):
        with pytest.raises(SpreadValidationError, match="safety.max_legs"):
            validate_spread_payload(payload(safety={"max_legs": "four"}))

    def test_bad_safety_flag_rejects(self):
        with pytest.raises(SpreadValidationError, match="risk_defined_only"):
            validate_spread_payload(payload(safety={"max_legs": 4, "risk_defined_only": "yes"}))


# --------------------------------------------------------------------------
# BUG-3 — basis-appropriate tp/sl type acceptance. A DEBIT spread must accept
# the debit-basis typed bracket (percent_of_debit / multiple_of_debit), a CREDIT
# spread the credit-basis types, value-only both, and a basis mismatch must be
# rejected with a clear message (Java rejects the mismatch downstream with
# BASIS_TYPE_CONTRADICTION). Signed max_net declares the basis up front (credit
# negative, debit positive); mid pricing with no max_net leaves the label's own
# basis word to declare it.
# --------------------------------------------------------------------------

_CREDIT_PRICING = {"mode": "best_fill", "slippage": 0.05,
                   "slippage_unit": "usd", "max_net": -1.20}
_DEBIT_PRICING = {"mode": "best_fill", "slippage": 0.05,
                  "slippage_unit": "usd", "max_net": 1.20}
_MID_PRICING = {"mode": "mid"}


class TestTpSlBasis:
    def test_debit_typed_tp_sl_accepted_on_debit_spread(self):
        assert validate_spread_payload(payload(
            pricing=_DEBIT_PRICING,
            tp={"type": "percent_of_debit", "value": 150},
            sl={"type": "multiple_of_debit", "value": 0.5},
        )) is None

    def test_credit_typed_tp_sl_accepted_on_credit_spread(self):
        assert validate_spread_payload(payload(
            pricing=_CREDIT_PRICING,
            tp={"type": "percent_of_credit", "value": 50},
            sl={"type": "multiple_of_credit", "value": 2},
        )) is None

    def test_credit_type_on_debit_spread_rejected(self):
        with pytest.raises(SpreadValidationError, match="credit-oriented"):
            validate_spread_payload(payload(
                pricing=_DEBIT_PRICING,
                tp={"type": "percent_of_credit", "value": 50},
                sl={"type": "multiple_of_credit", "value": 2},
            ))

    def test_debit_type_on_credit_spread_rejected(self):
        with pytest.raises(SpreadValidationError, match="debit-oriented"):
            validate_spread_payload(payload(
                pricing=_CREDIT_PRICING,
                tp={"type": "percent_of_debit", "value": 150},
                sl={"type": "multiple_of_debit", "value": 0.5},
            ))

    def test_value_only_tp_sl_accepted_credit(self):
        assert validate_spread_payload(payload(
            pricing=_CREDIT_PRICING,
            tp={"value": 50}, sl={"value": 2},
        )) is None

    def test_value_only_tp_sl_accepted_debit(self):
        assert validate_spread_payload(payload(
            pricing=_DEBIT_PRICING,
            tp={"value": 150}, sl={"value": 0.5},
        )) is None

    def test_debit_typed_accepted_when_basis_from_labels_only(self):
        # mid pricing with no max_net: basis is not knowable up front, so the
        # debit-word labels themselves declare the basis and are accepted.
        assert validate_spread_payload(payload(
            pricing=_MID_PRICING,
            tp={"type": "percent_of_debit", "value": 150},
            sl={"type": "multiple_of_debit", "value": 0.5},
        )) is None

    def test_mixed_basis_tp_sl_rejected(self):
        with pytest.raises(SpreadValidationError, match="conflicting bases"):
            validate_spread_payload(payload(
                pricing=_MID_PRICING,
                tp={"type": "percent_of_credit", "value": 50},
                sl={"type": "multiple_of_debit", "value": 0.5},
            ))

    def test_role_swap_rejected_on_tp(self):
        # tp must be the percent-of-basis label, not the multiple label.
        with pytest.raises(SpreadValidationError, match="tp.type"):
            validate_spread_payload(payload(
                pricing=_CREDIT_PRICING,
                tp={"type": "multiple_of_credit", "value": 2},
                sl={"type": "multiple_of_credit", "value": 2},
            ))

    def test_manual_positive_limit_price_is_debit_basis(self):
        # manual mode: the signed limit_price is the open price; positive => debit.
        assert validate_spread_payload(payload(
            pricing={"mode": "manual", "limit_price": 1.25},
            tp={"type": "percent_of_debit", "value": 150},
            sl={"type": "multiple_of_debit", "value": 0.5},
        )) is None

    def test_manual_positive_limit_price_rejects_credit_type(self):
        with pytest.raises(SpreadValidationError, match="credit-oriented"):
            validate_spread_payload(payload(
                pricing={"mode": "manual", "limit_price": 1.25},
                tp={"type": "percent_of_credit", "value": 50},
                sl={"type": "multiple_of_credit", "value": 2},
            ))


# --------------------------------------------------------------------------
# TI-2 — strategy_type is a free label, no closed allow-list
# --------------------------------------------------------------------------

class TestStrategyTypeFreeLabel:
    def test_arbitrary_strategy_type_accepted(self):
        # A label that was never in the old VALID_STRATEGIES list must pass now.
        assert validate_spread_payload(payload(strategy_type="my_custom_frankenspread")) is None

    def test_strategy_type_optional(self):
        p = payload()
        del p["strategy_type"]
        assert validate_spread_payload(p) is None

    def test_non_string_strategy_type_rejects(self):
        with pytest.raises(SpreadValidationError, match="strategy_type"):
            validate_spread_payload(payload(strategy_type=123))

    def test_legs_drive_validation_not_strategy_type(self):
        # Mismatched label + a genuinely broken leg: the leg error wins, proving
        # the legs (not the label) drive validation.
        p = payload(strategy_type="iron_condor")
        p["legs"][0]["strike"] = {"mode": "delta", "delta": 0.16}
        with pytest.raises(SpreadValidationError, match="fraction"):
            validate_spread_payload(p)
