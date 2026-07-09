"""Pure-function gate validator for option-spread payloads.

Used by /v3/add-option-spread to validate inbound payloads BEFORE any DB
write or broker dispatch. This is a cheap, dict-walking sanity check at
the API boundary; deeper typed access is provided by SpreadOrderDTO
(Pydantic) at the business-logic layer (Task 1.3).

NOTE: This validator never modifies the input dict. Each violation raises
SpreadValidationError immediately on the first problem found, with a
message that names the offending field so a TradingView user looking at
a webhook 400 response can fix their alert.
"""
import datetime
from .broker_capabilities import (
    broker_supports_spreads,
    get_supported_spread_strategies,
    get_max_spread_legs,
)



# ---------------------------------------------------------------------------
# Schema reference (condensed from OPTION_SPREADS_API_AND_STRATEGIES.md §2)
# ---------------------------------------------------------------------------

REQUIRED_TOP_LEVEL_FIELDS = (
    "token", "broker", "strategy", "underlying", "side",
    "expiration", "legs_mode", "quantity", "pricing", "manage",
)

VALID_STRATEGIES = (
    "vertical", "iron_condor", "iron_butterfly", "butterfly",
    "calendar", "diagonal", "straddle", "strangle", "custom",
)

VALID_SIDES = ("buy", "sell")

VALID_LEGS_MODES = ("auto", "explicit")

VALID_EXPIRATION_MODES = ("dte", "date", "alias")

VALID_EXPIRATION_ALIASES = (
    "weekly", "monthly", "quarterly",
    "this_friday", "next_friday", "next_monthly", "0dte",
)

VALID_PRICING_MODES = ("mid", "smart", "manual", "market")

VALID_RIGHTS = ("call", "put")

# Per-strategy required fields when legs_mode == "auto".
AUTO_REQUIRED_FIELDS = {
    "vertical":       ("right", "short_delta", "wing_width"),
    "iron_condor":    ("short_call_delta", "short_put_delta",
                       "call_wing_width", "put_wing_width"),
    "iron_butterfly": ("center_strike_method", "wing_width"),
    "butterfly":      ("right", "center_strike_method", "wing_width"),
    "calendar":       ("strike_method", "right", "front_dte", "back_dte"),
    "diagonal":       ("front_delta", "back_delta", "back_dte", "right"),
    "straddle":       ("strike_method",),
    "strangle":       ("call_delta", "put_delta"),
    # "custom" intentionally absent — must use explicit legs_mode.
}

# Per-strategy explicit-mode leg counts.
# `custom` accepts a range (2..6).
EXPLICIT_LEG_COUNT = {
    "vertical":       2,
    "iron_condor":    4,
    "iron_butterfly": 4,
    "butterfly":      3,
    "calendar":       2,
    "diagonal":       2,
    "straddle":       2,
    "strangle":       2,
}

EXPLICIT_LEG_REQUIRED_FIELDS = ("side", "right", "strike", "ratio")


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


def _validate_expiration(expiration) -> None:
    if not isinstance(expiration, dict):
        raise SpreadValidationError(
            "Field 'expiration' must be an object with a 'mode' key"
        )

    mode = expiration.get("mode")
    if mode is None:
        raise SpreadValidationError(
            "Field 'expiration.mode' is required (one of: "
            + ", ".join(VALID_EXPIRATION_MODES) + ")"
        )
    if mode not in VALID_EXPIRATION_MODES:
        raise SpreadValidationError(
            f"Field 'expiration.mode' has invalid value '{mode}' — "
            f"expected one of: {', '.join(VALID_EXPIRATION_MODES)}"
        )

    if mode == "dte":
        if "dte" not in expiration:
            raise SpreadValidationError(
                "Field 'expiration.dte' is required when expiration.mode == 'dte'"
            )
        dte = expiration["dte"]
        if not isinstance(dte, int) or isinstance(dte, bool) or dte < 0:
            raise SpreadValidationError(
                f"Field 'expiration.dte' must be a non-negative integer, got: {dte!r}"
            )

    elif mode == "date":
        if "date" not in expiration:
            raise SpreadValidationError(
                "Field 'expiration.date' is required when expiration.mode == 'date'"
            )
        date_val = expiration["date"]
        if not isinstance(date_val, str):
            raise SpreadValidationError(
                f"Field 'expiration.date' must be a YYYY-MM-DD string, got: {date_val!r}"
            )
        try:
            datetime.date.fromisoformat(date_val)
        except ValueError:
            raise SpreadValidationError(
                f"Field 'expiration.date' is not a valid ISO date (YYYY-MM-DD): "
                f"'{date_val}'"
            )

    elif mode == "alias":
        if "alias" not in expiration:
            raise SpreadValidationError(
                "Field 'expiration.alias' is required when expiration.mode == 'alias'"
            )
        alias = expiration["alias"]
        if alias not in VALID_EXPIRATION_ALIASES:
            raise SpreadValidationError(
                f"Field 'expiration.alias' has invalid value '{alias}' — "
                f"expected one of: {', '.join(VALID_EXPIRATION_ALIASES)}"
            )


def _validate_auto_block(strategy: str, payload: dict) -> None:
    if "auto" not in payload:
        raise SpreadValidationError(
            "Field 'auto' is required when legs_mode == 'auto'"
        )
    auto = payload["auto"]
    if not isinstance(auto, dict):
        raise SpreadValidationError("Field 'auto' must be an object")

    if strategy == "custom":
        # Custom must use explicit legs; reject auto for custom.
        raise SpreadValidationError(
            "Strategy 'custom' does not support legs_mode == 'auto' — "
            "use legs_mode == 'explicit' with a legs[] array"
        )

    required = AUTO_REQUIRED_FIELDS.get(strategy, ())
    for field in required:
        if field not in auto:
            raise SpreadValidationError(
                f"Field 'auto.{field}' is required for strategy '{strategy}'"
            )


def _validate_explicit_legs(strategy: str, payload: dict) -> None:
    if "legs" not in payload:
        raise SpreadValidationError(
            "Field 'legs' is required when legs_mode == 'explicit'"
        )
    legs = payload["legs"]
    if not isinstance(legs, list):
        raise SpreadValidationError("Field 'legs' must be an array")

    n = len(legs)

    # Leg-count gate per strategy.
    if strategy == "custom":
        if n < 2 or n > 6:
            raise SpreadValidationError(
                f"Strategy 'custom' requires 2 to 6 legs, got {n}"
            )
    else:
        expected = EXPLICIT_LEG_COUNT.get(strategy)
        if expected is not None and n != expected:
            raise SpreadValidationError(
                f"Strategy '{strategy}' requires exactly {expected} legs "
                f"in explicit mode, got {n}"
            )

    # Per-leg required-field gate.
    for idx, leg in enumerate(legs):
        if not isinstance(leg, dict):
            raise SpreadValidationError(
                f"Field 'legs[{idx}]' must be an object"
            )
        for field in EXPLICIT_LEG_REQUIRED_FIELDS:
            if field not in leg:
                raise SpreadValidationError(
                    f"Field 'legs[{idx}].{field}' is required"
                )

        # Light value sanity (kept narrow — deep type checking is Task 1.3's job).
        if leg["side"] not in VALID_SIDES:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].side' has invalid value "
                f"'{leg['side']}' — expected one of: {', '.join(VALID_SIDES)}"
            )
        if leg["right"] not in VALID_RIGHTS:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].right' has invalid value "
                f"'{leg['right']}' — expected one of: {', '.join(VALID_RIGHTS)}"
            )
        strike = leg["strike"]
        if not isinstance(strike, (int, float)) or isinstance(strike, bool) or strike <= 0:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].strike' must be a positive number, got: {strike!r}"
            )
        ratio = leg["ratio"]
        if not isinstance(ratio, int) or isinstance(ratio, bool) or ratio < 1:
            raise SpreadValidationError(
                f"Field 'legs[{idx}].ratio' must be an integer >= 1, got: {ratio!r}"
            )

    # Strategy-specific structural ratio checks. A butterfly is defined by
    # the N-2N-N ratio: without the doubled middle leg the trade is a bull
    # spread + naked call, not a butterfly. Silently accepting 1-1-1 would
    # route a wrong-shape order to the broker.
    if strategy == "butterfly" and len(legs) == 3:
        r0, r1, r2 = legs[0]["ratio"], legs[1]["ratio"], legs[2]["ratio"]
        if r0 != r2 or r1 != 2 * r0:
            raise SpreadValidationError(
                f"Strategy 'butterfly' requires N-2N-N ratio "
                f"(outer:middle:outer = 1:2:1 or 2:4:2 etc.), "
                f"got {r0}-{r1}-{r2}"
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

    # 2. Broker is supported for spreads at all.
    broker = payload["broker"]
    if not isinstance(broker, str) or not broker:
        raise SpreadValidationError(
            "Field 'broker' must be a non-empty string"
        )
    if not broker_supports_spreads(broker):
        raise SpreadValidationError(
            f"Broker '{broker}' does not support spreads (v1 supports IB only)"
        )

    # 3. Strategy is one of the v1 universe AND is in the broker's allow list.
    strategy = payload["strategy"]
    if strategy not in VALID_STRATEGIES:
        raise SpreadValidationError(
            f"Field 'strategy' has invalid value '{strategy}' — "
            f"expected one of: {', '.join(VALID_STRATEGIES)}"
        )
    supported = get_supported_spread_strategies(broker)
    if strategy not in supported:
        raise SpreadValidationError(
            f"Strategy '{strategy}' is not supported on broker '{broker}'. "
            f"Supported strategies: {supported}"
        )

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

    # 6. legs_mode ∈ {auto, explicit}.
    legs_mode = payload["legs_mode"]
    if legs_mode not in VALID_LEGS_MODES:
        raise SpreadValidationError(
            f"Field 'legs_mode' has invalid value '{legs_mode}' — "
            f"expected one of: {', '.join(VALID_LEGS_MODES)}"
        )

    # 7. Expiration: mode dispatch and per-mode field check.
    _validate_expiration(payload["expiration"])

    # 8 / 9. legs_mode-specific block.
    if legs_mode == "auto":
        _validate_auto_block(strategy, payload)
    else:  # explicit
        _validate_explicit_legs(strategy, payload)

    # Cross-check explicit leg count does not exceed broker's max.
    if legs_mode == "explicit":
        max_legs = get_max_spread_legs(broker)
        n = len(payload["legs"])
        if max_legs and n > max_legs:
            raise SpreadValidationError(
                f"Broker '{broker}' supports a maximum of {max_legs} legs "
                f"per spread, got {n}"
            )

    # 10. Pricing mode.
    _validate_pricing(payload["pricing"])

    # 'manage' field — presence already ensured above. v1 accepts either a
    # string preset name or a dict (full schema deferred to dispatcher).
    manage = payload["manage"]
    if not isinstance(manage, (str, dict)):
        raise SpreadValidationError(
            "Field 'manage' must be a preset name (string) or a dict spec"
        )
    if isinstance(manage, str) and not manage.strip():
        raise SpreadValidationError("Field 'manage' must be a non-empty string preset name")