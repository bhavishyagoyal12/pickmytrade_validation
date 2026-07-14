"""Pure-function gate validator for option-spread payloads.

Used by /v3/add-option-spread to validate inbound payloads BEFORE any DB
write or broker dispatch. This is a cheap, dict-walking sanity check at
the API boundary; deeper typed access is provided by SpreadOrderDTO
(Pydantic) at the business-logic layer.

Schema (finalized 2026-07-14, unified per-leg strike selector):
  - Top level: token, broker, inst_type, name, description, connection_name,
    account_id, quantity, multiple_accounts[], underlying, side, expiration,
    legs[], pricing, time_in_force, tp, sl, exit, safety, strategy_type.
  - Every leg carries its own strike selector {mode: absolute|delta|offset|
    relative}. A "wing" is just a leg with mode == relative that references
    another leg by id. There is no separate auto/explicit split and no fixed
    per-strategy leg geometry any more; strategy_type is a free label.

NOTE: This validator never modifies the input dict. Each violation raises
SpreadValidationError immediately on the first problem found, with a
message that names the offending field so a TradingView user looking at
a webhook 400 response can fix their alert.
"""
import datetime
import re
from .broker_capabilities import (
    broker_supports_spreads,
    # get_supported_spread_strategies,  # No longer used as a gate — see comment 15.
    get_max_spread_legs,
)


# ---------------------------------------------------------------------------
# Schema reference — active constants for the unified per-leg schema.
# ---------------------------------------------------------------------------

# Required top-level fields. Dropped the old strategy / legs_mode / manage
# fields; added legs. time_in_force is optional (defaults to DAY when absent).
REQUIRED_TOP_LEVEL_FIELDS = (
    "token", "broker", "underlying", "side",
    "expiration", "quantity", "pricing", "legs",
)

VALID_SIDES = ("buy", "sell")

VALID_RIGHTS = ("call", "put")

VALID_EXPIRATION_MODES = ("dte", "date", "alias")

VALID_EXPIRATION_ALIASES = (
    "weekly", "monthly", "quarterly",
    "this_friday", "next_friday", "next_monthly", "0dte",
)

# Per-leg strike selector.
STRIKE_MODES = ("absolute", "delta", "offset", "relative")
VALID_OFFSET_ANCHORS = ("atm", "spot")
VALID_STRIKE_UNITS = ("usd", "steps")

# Pricing / order controls.
VALID_PRICING_MODES = ("mid", "best_fill", "manual")
VALID_SLIPPAGE_UNITS = ("usd", "ticks")
VALID_TIF = ("DAY", "GTC")

# exit.time_of_day feeds the shared exit_at_time_ny scheduler column, which the
# legacy path guards with a strict HH:MM regex. Accept ONLY 24-hour HH:MM or
# HH:MM:SS so a malformed value (e.g. "5pm", "25:99", "9") is rejected here too.
TIME_OF_DAY_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")

# Every leg must carry these fields ('id' is new — relative legs reference
# an anchor leg by this stable id).
EXPLICIT_LEG_REQUIRED_FIELDS = ("id", "side", "right", "strike", "ratio")


# ---------------------------------------------------------------------------
# SUPERSEDED constants (kept, not deleted — replaced by the unified schema).
# ---------------------------------------------------------------------------
#
# Removed the fixed strategy list. The new per-leg builder can make any shape,
# so strategy_type is now just a label, not a switch validated against a closed
# list.
# VALID_STRATEGIES = (
#     "vertical", "iron_condor", "iron_butterfly", "butterfly",
#     "calendar", "diagonal", "straddle", "strangle", "custom",
# )
#
# There is no auto vs explicit split anymore. The payload always has one legs
# list.
# VALID_LEGS_MODES = ("auto", "explicit")
#
# Dropped smart and market. Only mid, best_fill, and manual are real modes now.
# VALID_PRICING_MODES = ("mid", "smart", "manual", "market")
#
# The auto block is gone; each leg carries its own strike selector, so there is
# nothing to look up per strategy.
# AUTO_REQUIRED_FIELDS = {
#     "vertical":       ("right", "short_delta", "wing_width"),
#     "iron_condor":    ("short_call_delta", "short_put_delta",
#                        "call_wing_width", "put_wing_width"),
#     "iron_butterfly": ("center_strike_method", "wing_width"),
#     "butterfly":      ("right", "center_strike_method", "wing_width"),
#     "calendar":       ("strike_method", "right", "front_dte", "back_dte"),
#     "diagonal":       ("front_delta", "back_delta", "back_dte", "right"),
#     "straddle":       ("strike_method",),
#     "strangle":       ("call_delta", "put_delta"),
# }
#
# Leg count is no longer fixed per named strategy. Replaced by a simple 2 to
# max-legs range check.
# EXPLICIT_LEG_COUNT = {
#     "vertical":       2,
#     "iron_condor":    4,
#     "iron_butterfly": 4,
#     "butterfly":      3,
#     "calendar":       2,
#     "diagonal":       2,
#     "straddle":       2,
#     "strangle":       2,
# }


class SpreadValidationError(ValueError):
    """Raised when an inbound spread payload fails validation.

    Subclasses ValueError to match the existing convention in this package
    (validator.py raises ValueError-equivalent errors via dict returns; this
    new module raises explicitly so the API layer can catch one exception
    type and translate to a 400).
    """


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_required(payload: dict, field: str) -> None:
    """Raise SpreadValidationError if `field` is missing from payload."""
    if field not in payload:
        raise SpreadValidationError(f"Missing required field: '{field}'")


def _is_number(value) -> bool:
    """True for a real int/float (bool is NOT accepted as a number)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_signed_number(idx: int, value, field: str) -> None:
    """A signed offset may be positive or negative but must be a number."""
    if not _is_number(value):
        raise SpreadValidationError(
            f"Field 'legs[{idx}].strike.{field}' must be a number "
            f"(may be negative), got: {value!r}"
        )


def _safety_max_legs(payload: dict):
    """Return safety.max_legs if it is a positive int, else None."""
    safety = payload.get("safety")
    if isinstance(safety, dict):
        m = safety.get("max_legs")
        if isinstance(m, int) and not isinstance(m, bool) and m > 0:
            return m
    return None


def _validate_expiration(expiration, where: str = "expiration") -> None:
    """Validate an expiration object. Used both top-level and per-leg
    (leg-level override), so the field path is parameterized via `where`."""
    if not isinstance(expiration, dict):
        raise SpreadValidationError(
            f"Field '{where}' must be an object with a 'mode' key"
        )

    mode = expiration.get("mode")
    if mode is None:
        raise SpreadValidationError(
            f"Field '{where}.mode' is required (one of: "
            + ", ".join(VALID_EXPIRATION_MODES) + ")"
        )
    if mode not in VALID_EXPIRATION_MODES:
        raise SpreadValidationError(
            f"Field '{where}.mode' has invalid value '{mode}' — "
            f"expected one of: {', '.join(VALID_EXPIRATION_MODES)}"
        )

    if mode == "dte":
        if "dte" not in expiration:
            raise SpreadValidationError(
                f"Field '{where}.dte' is required when {where}.mode == 'dte'"
            )
        dte = expiration["dte"]
        if not isinstance(dte, int) or isinstance(dte, bool) or dte < 0:
            raise SpreadValidationError(
                f"Field '{where}.dte' must be a non-negative integer, got: {dte!r}"
            )

    elif mode == "date":
        if "date" not in expiration:
            raise SpreadValidationError(
                f"Field '{where}.date' is required when {where}.mode == 'date'"
            )
        date_val = expiration["date"]
        if not isinstance(date_val, str):
            raise SpreadValidationError(
                f"Field '{where}.date' must be a YYYY-MM-DD string, got: {date_val!r}"
            )
        try:
            datetime.date.fromisoformat(date_val)
        except ValueError:
            raise SpreadValidationError(
                f"Field '{where}.date' is not a valid ISO date (YYYY-MM-DD): "
                f"'{date_val}'"
            )

    elif mode == "alias":
        if "alias" not in expiration:
            raise SpreadValidationError(
                f"Field '{where}.alias' is required when {where}.mode == 'alias'"
            )
        alias = expiration["alias"]
        if alias not in VALID_EXPIRATION_ALIASES:
            raise SpreadValidationError(
                f"Field '{where}.alias' has invalid value '{alias}' — "
                f"expected one of: {', '.join(VALID_EXPIRATION_ALIASES)}"
            )


def _validate_strike_selector(idx: int, strike) -> None:
    """Validate one leg's strike selector by dispatching on its mode.

    Note: for mode 'relative' this checks the shape of `ref` (a non-empty
    string) but NOT that it points at a valid anchor — the ref-target rules
    (must exist, must be non-relative) need all leg ids and are enforced in
    the topological pass inside _validate_legs.
    """
    if not isinstance(strike, dict):
        raise SpreadValidationError(
            f"Field 'legs[{idx}].strike' must be an object with a 'mode' key "
            f"(one of: {', '.join(STRIKE_MODES)})"
        )
    mode = strike.get("mode")
    if mode not in STRIKE_MODES:
        raise SpreadValidationError(
            f"Field 'legs[{idx}].strike.mode' has invalid value {mode!r} — "
            f"expected one of: {', '.join(STRIKE_MODES)}"
        )

    if mode == "absolute":
        value = strike.get("value")
        if not _is_number(value) or value <= 0:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].strike.value' must be a positive number "
                f"for mode 'absolute', got: {value!r}"
            )

    elif mode == "delta":
        delta = strike.get("delta")
        if not _is_number(delta):
            raise SpreadValidationError(
                f"Field 'legs[{idx}].strike.delta' must be a number, got: {delta!r}"
            )
        # TI-1: delta is on a 0-100 scale (16 == a 16-delta option).
        if delta <= 0 or delta > 100:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].strike.delta' must be on a 0-100 scale "
                f"(0 < delta <= 100), got: {delta!r}"
            )
        # A value below 1 is almost always a 0-to-1 fraction typed by mistake
        # (e.g. 0.16 instead of 16). Reject it so the user fixes the scale.
        if delta < 1:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].strike.delta' looks like a 0-to-1 fraction "
                f"({delta!r}); use the 0-100 scale, e.g. 16 for a 16-delta option"
            )

    elif mode == "offset":
        anchor = strike.get("anchor")
        if anchor not in VALID_OFFSET_ANCHORS:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].strike.anchor' must be one of "
                f"{VALID_OFFSET_ANCHORS} for mode 'offset', got: {anchor!r}"
            )
        _require_signed_number(idx, strike.get("offset"), "offset")
        unit = strike.get("unit")
        if unit not in VALID_STRIKE_UNITS:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].strike.unit' must be one of "
                f"{VALID_STRIKE_UNITS}, got: {unit!r}"
            )

    elif mode == "relative":
        ref = strike.get("ref")
        if not isinstance(ref, str) or not ref.strip():
            raise SpreadValidationError(
                f"Field 'legs[{idx}].strike.ref' must be a non-empty leg id string "
                f"for mode 'relative', got: {ref!r}"
            )
        offset = strike.get("offset")
        _require_signed_number(idx, offset, "offset")
        # A relative offset of 0 would land the leg exactly on its anchor
        # strike (collapse), which is never a real spread leg.
        if offset == 0:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].strike.offset' must be non-zero for mode "
                f"'relative' (offset 0 collapses the leg onto its anchor)"
            )
        unit = strike.get("unit")
        if unit not in VALID_STRIKE_UNITS:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].strike.unit' must be one of "
                f"{VALID_STRIKE_UNITS}, got: {unit!r}"
            )


def _validate_legs(payload: dict, broker: str) -> None:
    """Validate the legs[] array: per-leg fields + strike selector, a
    2..max-legs count range, and the relative-leg topological pass."""
    legs = payload["legs"]
    if not isinstance(legs, list):
        raise SpreadValidationError("Field 'legs' must be an array")

    n = len(legs)

    # Upper bound = the smaller of the broker cap and any user-set
    # safety.max_legs. min() so neither can be exceeded.
    limits = [
        m for m in (get_max_spread_legs(broker), _safety_max_legs(payload))
        if isinstance(m, int) and m > 0
    ]
    max_legs = min(limits) if limits else None

    if n < 2:
        raise SpreadValidationError(f"A spread needs at least 2 legs, got {n}")
    if max_legs is not None and n > max_legs:
        raise SpreadValidationError(
            f"A spread supports at most {max_legs} legs (broker/safety cap), got {n}"
        )

    seen_ids = {}
    for idx, leg in enumerate(legs):
        if not isinstance(leg, dict):
            raise SpreadValidationError(f"Field 'legs[{idx}]' must be an object")
        for field in EXPLICIT_LEG_REQUIRED_FIELDS:
            if field not in leg:
                raise SpreadValidationError(f"Field 'legs[{idx}].{field}' is required")

        leg_id = leg["id"]
        if not isinstance(leg_id, str) or not leg_id.strip():
            raise SpreadValidationError(
                f"Field 'legs[{idx}].id' must be a non-empty string"
            )
        if leg_id in seen_ids:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].id' duplicates id '{leg_id}' "
                f"(already used by legs[{seen_ids[leg_id]}]); ids must be unique"
            )
        seen_ids[leg_id] = idx

        if leg["side"] not in VALID_SIDES:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].side' has invalid value {leg['side']!r} — "
                f"expected one of: {', '.join(VALID_SIDES)}"
            )
        if leg["right"] not in VALID_RIGHTS:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].right' has invalid value {leg['right']!r} — "
                f"expected one of: {', '.join(VALID_RIGHTS)}"
            )

        ratio = leg["ratio"]
        if not isinstance(ratio, int) or isinstance(ratio, bool) or ratio < 1:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].ratio' must be an integer >= 1, got: {ratio!r}"
            )

        _validate_strike_selector(idx, leg["strike"])

        # Optional per-leg expiration override (same shape as the top-level one).
        if "expiration" in leg and leg["expiration"] is not None:
            _validate_expiration(leg["expiration"], where=f"legs[{idx}].expiration")

    # Topological pass: a relative leg's ref must point at an EXISTING,
    # NON-relative leg. One level deep only — no relative->relative chains,
    # no cycles, no self-reference, no missing target.
    id_to_mode = {leg["id"]: leg["strike"].get("mode") for leg in legs}
    for idx, leg in enumerate(legs):
        strike = leg["strike"]
        if strike.get("mode") != "relative":
            continue
        ref = strike["ref"]
        if ref == leg["id"]:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].strike.ref' cannot reference its own leg '{ref}'"
            )
        if ref not in id_to_mode:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].strike.ref' points at unknown leg id '{ref}' "
                f"(no leg has that id)"
            )
        if id_to_mode[ref] == "relative":
            raise SpreadValidationError(
                f"Field 'legs[{idx}].strike.ref' points at relative leg '{ref}'; "
                f"a relative leg may only reference a non-relative leg "
                f"(one level deep, no chains)"
            )


def _validate_pricing(pricing) -> None:
    if not isinstance(pricing, dict):
        raise SpreadValidationError(
            "Field 'pricing' must be an object with a 'mode' key"
        )
    mode = pricing.get("mode")
    if mode is None:
        raise SpreadValidationError(
            "Field 'pricing.mode' is required (one of: "
            + ", ".join(VALID_PRICING_MODES) + ")"
        )
    if mode not in VALID_PRICING_MODES:
        raise SpreadValidationError(
            f"Field 'pricing.mode' has invalid value '{mode}' — "
            f"expected one of: {', '.join(VALID_PRICING_MODES)}"
        )

    # slippage: tolerance worse than the reference price. Optional, >= 0.
    if pricing.get("slippage") is not None:
        slip = pricing["slippage"]
        if not _is_number(slip) or slip < 0:
            raise SpreadValidationError(
                f"Field 'pricing.slippage' must be a non-negative number, got: {slip!r}"
            )
    if pricing.get("slippage_unit") is not None:
        su = pricing["slippage_unit"]
        if su not in VALID_SLIPPAGE_UNITS:
            raise SpreadValidationError(
                f"Field 'pricing.slippage_unit' must be one of {VALID_SLIPPAGE_UNITS}, "
                f"got: {su!r}"
            )
    # max_net: SIGNED hard cap (debit positive, credit negative). Any number.
    if pricing.get("max_net") is not None:
        mn = pricing["max_net"]
        if not _is_number(mn):
            raise SpreadValidationError(
                f"Field 'pricing.max_net' must be a signed number "
                f"(debit positive, credit negative), got: {mn!r}"
            )

    # manual mode requires an explicit signed net limit price.
    if mode == "manual":
        lp = pricing.get("limit_price")
        if not _is_number(lp):
            raise SpreadValidationError(
                "Field 'pricing.limit_price' is required (a signed net price) "
                "when pricing.mode == 'manual'"
            )


def _validate_time_in_force(payload: dict) -> None:
    # Optional at the top level; defaults to DAY when absent.
    tif = payload.get("time_in_force")
    if tif is None:
        return
    if tif not in VALID_TIF:
        raise SpreadValidationError(
            f"Field 'time_in_force' has invalid value {tif!r} — "
            f"expected one of: {', '.join(VALID_TIF)}"
        )


def _validate_multiple_accounts(payload: dict) -> None:
    accounts = payload.get("multiple_accounts")
    if accounts is None:
        return
    if not isinstance(accounts, list):
        raise SpreadValidationError("Field 'multiple_accounts' must be an array")
    for idx, entry in enumerate(accounts):
        if not isinstance(entry, dict):
            raise SpreadValidationError(
                f"Field 'multiple_accounts[{idx}]' must be an object"
            )
        for field in ("token", "connection_name", "account_id"):
            val = entry.get(field)
            if not isinstance(val, str) or not val.strip():
                raise SpreadValidationError(
                    f"Field 'multiple_accounts[{idx}].{field}' is required and "
                    f"must be a non-empty string"
                )
        # At most one sizing field. Both-present is ambiguous; both-absent is
        # allowed and defaults to a multiplier of 1 downstream.
        has_mult = entry.get("quantity_multiplier") is not None
        has_fixed = entry.get("fixed_quantity") is not None
        if has_mult and has_fixed:
            raise SpreadValidationError(
                f"Field 'multiple_accounts[{idx}]' may set only one of "
                f"'quantity_multiplier' or 'fixed_quantity', not both"
            )
        if has_mult:
            qm = entry["quantity_multiplier"]
            if not _is_number(qm) or qm <= 0:
                raise SpreadValidationError(
                    f"Field 'multiple_accounts[{idx}].quantity_multiplier' must be "
                    f"a positive number, got: {qm!r}"
                )
        if has_fixed:
            fq = entry["fixed_quantity"]
            if not _is_number(fq) or fq <= 0:
                raise SpreadValidationError(
                    f"Field 'multiple_accounts[{idx}].fixed_quantity' must be "
                    f"a positive number, got: {fq!r}"
                )


def _validate_tp_sl(name: str, block) -> None:
    # Thin shape check — the whole-spread take-profit / stop-loss block.
    if block is None:
        return
    if not isinstance(block, dict):
        raise SpreadValidationError(f"Field '{name}' must be an object")
    # Enforce the type label. The Java gateway hardcodes the percent-vs-multiple
    # convention by basis+role, so a mismatched label would be silently misread
    # downstream. Only one type is supported per role in v1.
    expected_type = "percent_of_credit" if name == "tp" else "multiple_of_credit"
    if block.get("type") is not None and block["type"] != expected_type:
        raise SpreadValidationError(
            f"Field '{name}.type' must be {expected_type!r}, got: {block['type']!r}"
        )
    if block.get("value") is not None:
        v = block["value"]
        if not _is_number(v) or v < 0:
            raise SpreadValidationError(
                f"Field '{name}.value' must be a non-negative number, got: {v!r}"
            )


def _validate_exit(exit_block) -> None:
    # Thin shape check — exit-by-DTE / exit-at-time block.
    if exit_block is None:
        return
    if not isinstance(exit_block, dict):
        raise SpreadValidationError("Field 'exit' must be an object")
    if exit_block.get("dte") is not None:
        dte = exit_block["dte"]
        if not isinstance(dte, int) or isinstance(dte, bool) or dte < 0:
            raise SpreadValidationError(
                f"Field 'exit.dte' must be a non-negative integer, got: {dte!r}"
            )
    if exit_block.get("time_of_day") is not None:
        tod = exit_block["time_of_day"]
        if not isinstance(tod, str):
            raise SpreadValidationError("Field 'exit.time_of_day' must be a string")
        # Strict 24-hour HH:MM or HH:MM:SS — it feeds the shared exit_at_time_ny
        # scheduler column, which the legacy path guards with the same regex.
        if not TIME_OF_DAY_RE.match(tod):
            raise SpreadValidationError(
                f"Field 'exit.time_of_day' must be 24-hour HH:MM or HH:MM:SS, "
                f"got: {tod!r}"
            )
    if exit_block.get("tz") is not None and not isinstance(exit_block["tz"], str):
        raise SpreadValidationError("Field 'exit.tz' must be a string")


def _validate_safety(safety) -> None:
    # Thin shape check — safety guards block (max_legs is also read by the
    # leg-count range check in _validate_legs).
    if safety is None:
        return
    if not isinstance(safety, dict):
        raise SpreadValidationError("Field 'safety' must be an object")
    if safety.get("max_legs") is not None:
        m = safety["max_legs"]
        if not isinstance(m, int) or isinstance(m, bool) or m < 1:
            raise SpreadValidationError(
                f"Field 'safety.max_legs' must be an integer >= 1, got: {m!r}"
            )
    for flag in ("risk_defined_only", "non_guaranteed"):
        if safety.get(flag) is not None and not isinstance(safety[flag], bool):
            raise SpreadValidationError(
                f"Field 'safety.{flag}' must be a boolean, got: {safety[flag]!r}"
            )


# ---------------------------------------------------------------------------
# SUPERSEDED validators (kept, not deleted — replaced by the unified schema).
# ---------------------------------------------------------------------------
#
# The auto block is gone; each leg carries its own strike selector, so there is
# nothing to look up per strategy.
# def _validate_auto_block(strategy, payload):
#     if "auto" not in payload:
#         raise SpreadValidationError(
#             "Field 'auto' is required when legs_mode == 'auto'"
#         )
#     auto = payload["auto"]
#     if not isinstance(auto, dict):
#         raise SpreadValidationError("Field 'auto' must be an object")
#     if strategy == "custom":
#         raise SpreadValidationError(
#             "Strategy 'custom' does not support legs_mode == 'auto' — "
#             "use legs_mode == 'explicit' with a legs[] array"
#         )
#     required = AUTO_REQUIRED_FIELDS.get(strategy, ())
#     for field in required:
#         if field not in auto:
#             raise SpreadValidationError(
#                 f"Field 'auto.{field}' is required for strategy '{strategy}'"
#             )
#
# The old explicit-leg validator did three things that no longer apply:
#   - Leg count is no longer fixed per named strategy (replaced by a simple
#     2 to max-legs range check).
#   - The butterfly N-2N-N ratio check was strategy-specific geometry. With
#     the generic per-leg builder there is no strategy switch, so this rule
#     is gone.
#   - strike is now an object, not a number, so the positive-number check is
#     replaced by the strike-selector validator.
# def _validate_explicit_legs(strategy, payload):
#     if "legs" not in payload:
#         raise SpreadValidationError(
#             "Field 'legs' is required when legs_mode == 'explicit'"
#         )
#     legs = payload["legs"]
#     if not isinstance(legs, list):
#         raise SpreadValidationError("Field 'legs' must be an array")
#     n = len(legs)
#     if strategy == "custom":
#         if n < 2 or n > 6:
#             raise SpreadValidationError(
#                 f"Strategy 'custom' requires 2 to 6 legs, got {n}"
#             )
#     else:
#         expected = EXPLICIT_LEG_COUNT.get(strategy)
#         if expected is not None and n != expected:
#             raise SpreadValidationError(
#                 f"Strategy '{strategy}' requires exactly {expected} legs "
#                 f"in explicit mode, got {n}"
#             )
#     for idx, leg in enumerate(legs):
#         if not isinstance(leg, dict):
#             raise SpreadValidationError(f"Field 'legs[{idx}]' must be an object")
#         for field in EXPLICIT_LEG_REQUIRED_FIELDS:
#             if field not in leg:
#                 raise SpreadValidationError(f"Field 'legs[{idx}].{field}' is required")
#         if leg["side"] not in VALID_SIDES:
#             raise SpreadValidationError(...)
#         if leg["right"] not in VALID_RIGHTS:
#             raise SpreadValidationError(...)
#         # old scalar strike positive check (strike used to be a bare number):
#         strike = leg["strike"]
#         if not isinstance(strike, (int, float)) or isinstance(strike, bool) or strike <= 0:
#             raise SpreadValidationError(
#                 f"Field 'legs[{idx}].strike' must be a positive number, got: {strike!r}"
#             )
#         ratio = leg["ratio"]
#         if not isinstance(ratio, int) or isinstance(ratio, bool) or ratio < 1:
#             raise SpreadValidationError(...)
#     # butterfly N-2N-N ratio check (strategy-specific geometry — gone):
#     if strategy == "butterfly" and len(legs) == 3:
#         r0, r1, r2 = legs[0]["ratio"], legs[1]["ratio"], legs[2]["ratio"]
#         if r0 != r2 or r1 != 2 * r0:
#             raise SpreadValidationError(
#                 f"Strategy 'butterfly' requires N-2N-N ratio ..., got {r0}-{r1}-{r2}"
#             )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def validate_spread_payload(payload: dict) -> None:
    """Validate a spread order payload.

    Returns None on success. Raises SpreadValidationError on the FIRST
    violation encountered, with a message that names the offending field
    so the user can fix it without guessing.

    The validator never modifies the input dict.
    """
    if not isinstance(payload, dict):
        raise SpreadValidationError("Payload must be a JSON object (dict)")

    # 1. Required top-level fields present.
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        _check_required(payload, field)

    # 2. Broker supports spreads at all.
    broker = payload["broker"]
    if not isinstance(broker, str) or not broker:
        raise SpreadValidationError("Field 'broker' must be a non-empty string")
    if not broker_supports_spreads(broker):
        raise SpreadValidationError(
            f"Broker '{broker}' does not support spreads (v1 supports IB only)"
        )

    # 3. strategy_type is a FREE LABEL now (no closed allow-list — the legs
    #    drive validation). If present it must simply be a string.
    strategy_type = payload.get("strategy_type")
    if strategy_type is not None and not isinstance(strategy_type, str):
        raise SpreadValidationError("Field 'strategy_type' must be a string label")

    # 4. Side ∈ {buy, sell}.
    side = payload["side"]
    if side not in VALID_SIDES:
        raise SpreadValidationError(
            f"Field 'side' has invalid value '{side}' — "
            f"expected one of: {', '.join(VALID_SIDES)}"
        )

    # 5. Quantity is a positive integer.
    quantity = payload["quantity"]
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise SpreadValidationError(
            f"Field 'quantity' must be a positive integer, got: {quantity!r}"
        )

    # 6. Top-level expiration.
    _validate_expiration(payload["expiration"])

    # 7. Safety block (validated before legs so its max_legs is trusted by the
    #    leg-count range check).
    _validate_safety(payload.get("safety"))

    # 8. Legs: per-leg selectors + relative-leg topology + 2..max range.
    _validate_legs(payload, broker)

    # 9. Pricing: mode + slippage + signed max_net + manual limit_price.
    _validate_pricing(payload["pricing"])

    # 10. Time in force (optional, default DAY).
    _validate_time_in_force(payload)

    # 11. Multi-account fan-out entries.
    _validate_multiple_accounts(payload)

    # 12. Thin tp / sl / exit shape checks.
    _validate_tp_sl("tp", payload.get("tp"))
    _validate_tp_sl("sl", payload.get("sl"))
    _validate_exit(payload.get("exit"))


# ---------------------------------------------------------------------------
# SUPERSEDED entry-point body (kept, not deleted). The old flow gated on a
# closed strategy allow-list, forked on legs_mode (auto vs explicit), and
# required a single 'manage' blob. All three are replaced above.
# ---------------------------------------------------------------------------
#
# def validate_spread_payload(payload):
#     ...
#     # The fixed strategy list is superseded. strategy_type is a free label
#     # validated by the legs, not against a closed list.
#     strategy = payload["strategy"]
#     if strategy not in VALID_STRATEGIES:
#         raise SpreadValidationError(...)
#     supported = get_supported_spread_strategies(broker)
#     if strategy not in supported:
#         raise SpreadValidationError(...)
#     ...
#     # There is no auto vs explicit split anymore. The payload always has one
#     # legs list.
#     legs_mode = payload["legs_mode"]
#     if legs_mode not in VALID_LEGS_MODES:
#         raise SpreadValidationError(...)
#     if legs_mode == "auto":
#         _validate_auto_block(strategy, payload)
#     else:
#         _validate_explicit_legs(strategy, payload)
#     ...
#     # The single manage blob is replaced by separate tp/sl/exit/safety blocks.
#     manage = payload["manage"]
#     if not isinstance(manage, (str, dict)):
#         raise SpreadValidationError(
#             "Field 'manage' must be a preset name (string) or a dict spec"
#         )
#     if isinstance(manage, str) and not manage.strip():
#         raise SpreadValidationError(
#             "Field 'manage' must be a non-empty string preset name"
#         )
