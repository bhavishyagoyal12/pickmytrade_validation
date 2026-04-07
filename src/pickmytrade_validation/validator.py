import datetime
import re

try:
    from .broker_capabilities import (
        broker_supports_trailing,
        broker_supports_trail_stop,
        broker_supports_trail_trigger,
        broker_supports_trail_freq,
        broker_supports_breakeven,
        broker_supports_update_tp_sl,
        broker_supports_options,
        broker_supports_advance_tp_sl,
        broker_supports_stop_orders,
        get_allowed_inst_types
    )
except ImportError:
    from broker_capabilities import (
        broker_supports_trailing,
        broker_supports_trail_stop,
        broker_supports_trail_trigger,
        broker_supports_trail_freq,
        broker_supports_breakeven,
        broker_supports_update_tp_sl,
        broker_supports_options,
        broker_supports_advance_tp_sl,
        broker_supports_stop_orders,
        get_allowed_inst_types
    )


def validate_and_describe_alert_json(d: dict, raw_payload: str = None, allow_placeholders: bool = True) -> dict:
    """
    Validates required fields in an alert JSON and returns a human-readable
    description of what the order will do.
    No DB writes, no order placement — purely a dry-run explainer.
    """
    if raw_payload:
        clean_str = str(raw_payload).strip()
        if clean_str and (not clean_str.startswith("{") or not clean_str.endswith("}")):
            return {
                "error": True,
                "missing_fields": [],
                "invalid_fields": ["Raw JSON payload padding"],
                "warnings": [],
                "description": "Invalid JSON format: There are extra characters outside the JSON object. Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
            }
    def is_placeholder(val):
        if not allow_placeholders:
            return False
        return isinstance(val, str) and "{{" in val and "}}" in val

    # 1. Pre-scan for malformed placeholders and strict field allowance
    placeholder_errors = []
    
    # Fields with a STRICT whitelist — only the listed exact placeholders are allowed.
    STRICT_PLACEHOLDER_FIELDS = {
        "date":     {"{{timenow}}", "{{time}}"},
        "quantity": {"{{strategy.market_position_size}}", "{{strategy.order.contracts}}"},
        "data":     {"{{strategy.market_position}}", "{{strategy.order.action}}"}
    }

    # Only these fields may accept any freely-formed {{...}} placeholder.
    # Every other field (not in either set above) rejects all placeholders.
    OPEN_PLACEHOLDER_FIELDS = {"price", "tp", "sl"}

    def check_placeholders(val, path="", k_name=""):
        if isinstance(val, dict):
            for k, v in val.items():
                check_placeholders(v, f"{path}.{k}" if path else k, k)
        elif isinstance(val, list):
            for i, v in enumerate(val):
                check_placeholders(v, f"{path}[{i}]", k_name)
        elif isinstance(val, str):
            has_double_open = "{{" in val
            has_double_close = "}}" in val
            has_single_open = "{" in val
            has_single_close = "}" in val

            if has_double_open and not has_double_close:
                placeholder_errors.append(f"{path}: contains '{{{{' but missing '}}}}'")
            elif has_double_close and not has_double_open:
                placeholder_errors.append(f"{path}: contains '}}}}' but missing '{{{{'")
            elif (has_single_open or has_single_close) and not (has_double_open and has_double_close):
                placeholder_errors.append(f"{path}: placeholders must use double curly braces {{{{}}}}")
            elif has_double_open and has_double_close and not allow_placeholders:
                placeholder_errors.append(f"{path}: Placeholders are disabled. Field '{k_name}' must be an explicit value.")
            elif is_placeholder(val):
                normalized_val = val.strip().lower()

                # Reject empty placeholders: {{}} or {{   }}
                inner = re.sub(r'\{\{|\}\}', '', normalized_val).strip()
                if not inner:
                    placeholder_errors.append(
                        f"{path}: placeholder is empty — '{{{{}}}}' has no content inside the braces"
                    )
                    return  # no further checks needed

                is_plot_placeholder = bool(
                    re.match(r'^\{\{plot_?\d+\}\}$', normalized_val) or
                    re.match(r'^\{\{plot\(.*?\)\}\}$', normalized_val)
                )

                if k_name in OPEN_PLACEHOLDER_FIELDS:
                    pass  # price, tp, sl accept any {{...}} — including plot placeholders
                elif k_name in STRICT_PLACEHOLDER_FIELDS:
                    # Exact whitelist — only the listed values are allowed
                    if normalized_val not in STRICT_PLACEHOLDER_FIELDS[k_name]:
                        placeholder_errors.append(
                            f"{path}: '{val}' is not a recognized placeholder for '{k_name}'. "
                            f"Expected one of: " + ", ".join(STRICT_PLACEHOLDER_FIELDS[k_name])
                        )
                else:
                    # Every other field — no placeholders permitted
                    placeholder_errors.append(
                        f"{path}: placeholders are not permitted in '{k_name}'"
                    )

    check_placeholders(d, k_name="root")
    if placeholder_errors:
        return {
            "error": True,
            "missing_fields": [],
            "invalid_fields": placeholder_errors,
            "warnings": [],
            "description": f"Malformed TradingView placeholders: {'; '.join(placeholder_errors)}. Ensure placeholders are properly closed."
        }

    # ------------------------------------------------------------------ #
    # 0. Strict Type Checks
    # ------------------------------------------------------------------ #
    type_errors = []
    STRING_FIELDS = {"token", "symbol", "platform", "data", "order_type", "inst_type", "option_type", "expiry_date", "account_id", "connection_name", "date"}
    NUMERIC_FIELDS = {"quantity", "risk_percentage", "price", "sl", "dollar_sl", "percentage_sl", "tp", "dollar_tp", "percentage_tp", "trail", "trail_stop", "trail_trigger", "breakeven", "order_strike"}
    BOOL_FIELDS = {"update_tp", "update_sl", "pyramid", "duplicate_position_allow", "reverse_close_enable"}

    def validate_types(obj_dict, prefix=""):
        for k, v in obj_dict.items():
            if v is None or is_placeholder(v):
                continue
            
            field_name = f"{prefix}{k}" if prefix else k
            
            if k in STRING_FIELDS:
                if not isinstance(v, str):
                    type_errors.append(f"{field_name} (expected string, got {type(v).__name__})")
            elif k in NUMERIC_FIELDS:
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    type_errors.append(f"{field_name} (expected number, got {type(v).__name__})")
            elif k in BOOL_FIELDS:
                if not isinstance(v, bool):
                    type_errors.append(f"{field_name} (expected boolean, got {type(v).__name__})")

    validate_types(d)

    # Check multiple accounts types if present
    multiple_accs_raw = d.get("multiple_accounts", [])
    if isinstance(multiple_accs_raw, list):
        for i, acc in enumerate(multiple_accs_raw):
            if isinstance(acc, dict):
                validate_types(acc, prefix=f"multiple_accounts[{i}].")

    # Check advance_tp_sl types if present
    advance_tp_sl_raw = d.get("advance_tp_sl", [])
    if isinstance(advance_tp_sl_raw, list):
        for i, acc in enumerate(advance_tp_sl_raw):
            if isinstance(acc, dict):
                validate_types(acc, prefix=f"advance_tp_sl[{i}].")

    if type_errors:
        return {
            "error": True,
            "missing_fields": [],
            "invalid_fields": type_errors,
            "warnings": [],
            "description": f"Strict type mismatch: {'; '.join(type_errors)}. Please provide the correct data types (e.g., numbers without quotes)."
        }

    # Helper to resolve placeholder vs actual value
    # If a field has a valid placeholder, we treat it as valid for now because its real value will be known at runtime.
    # ------------------------------------------------------------------ #
    # 1. Required field checks
    # ------------------------------------------------------------------ #
    missing = []

    if not d.get("token", ""):
        missing.append("token")

    if not d.get("symbol", ""):
        missing.append("symbol")

    raw_side = str(d.get("data", "")).strip().upper()
    is_close = raw_side in ("CLOSE", "FLAT")

    if not raw_side:
        missing.append("data (expected: buy / sell / long / short / close / flat)")

    if not d.get("platform", ""):
        missing.append("platform (e.g. RITHMIC, PROJECTX, IB, TRADOVATE, BINANCE)")

    if not d.get("order_type", ""):
        missing.append("order_type (e.g. MKT, LMT, STP, STOPLIMIT)")

    # For non-CLOSE orders, at least quantity>0 OR risk_percentage>0 is needed
    try:
        raw_qty = d.get("quantity", 0)
        qty = raw_qty if is_placeholder(raw_qty) else float(raw_qty or 0)
    except (ValueError, TypeError):
        qty = 0
        missing.append("quantity (must be a number)")
    try:
        raw_risk = d.get("risk_percentage", 0)
        risk_pct = 1 if is_placeholder(raw_risk) else float(raw_risk or 0)
    except (ValueError, TypeError):
        risk_pct = 0

    if not is_close and qty == 0 and risk_pct == 0:
        missing.append("quantity_or_risk_percentage (at least one must be > 0)")

    # Validate each entry in multiple_accounts if present
    multiple_accs_raw = d.get("multiple_accounts", []) or []
    _pending_acc_invalid = []  # flushed into `invalid` after it is initialized below

    # Determine top-level sizing mode (used to enforce consistency in sub-accounts)
    # risk_pct > 0 takes precedence (even if qty is also set)
    _top_uses_risk = (risk_pct > 0)
    _top_uses_qty  = (not is_placeholder(d.get("quantity", 0)) and float(d.get("quantity", 0) or 0) > 0)

    for i, acc in enumerate(multiple_accs_raw, 1):
        if not acc.get("account_id", ""):
            missing.append(f"multiple_accounts[{i}].account_id")
        if not acc.get("connection_name", ""):
            missing.append(f"multiple_accounts[{i}].connection_name")
        if not acc.get("token", ""):
            missing.append(f"multiple_accounts[{i}].token")
        try:
            _acc_risk = float(acc.get("risk_percentage", 0) or 0)
            _acc_qmul = float(acc.get("quantity_multiplier", 0) or 0)
        except (ValueError, TypeError):
            _acc_risk = 0
            _acc_qmul = 0

        if _top_uses_risk:
            # Top level uses risk_percentage (or both) → sub-account must use risk_percentage > 0, quantity_multiplier = 0
            if _acc_risk <= 0:
                _pending_acc_invalid.append(
                    f"multiple_accounts[{i}]: top-level uses 'risk_percentage' sizing, so each sub-account must also "
                    f"set 'risk_percentage' > 0 (found: {acc.get('risk_percentage', 0)})."
                )
            if _acc_qmul != 0:
                _pending_acc_invalid.append(
                    f"multiple_accounts[{i}]: 'quantity_multiplier' must be 0 when top-level uses 'risk_percentage' sizing "
                    f"(found: {acc.get('quantity_multiplier', 0)})."
                )
        elif _top_uses_qty:
            # Top level uses quantity only → sub-account must use quantity_multiplier > 0, risk_percentage = 0
            if _acc_qmul <= 0:
                _pending_acc_invalid.append(
                    f"multiple_accounts[{i}]: top-level uses 'quantity' sizing, so each sub-account must set "
                    f"'quantity_multiplier' > 0 (found: {acc.get('quantity_multiplier', 0)})."
                )
            if _acc_risk != 0:
                _pending_acc_invalid.append(
                    f"multiple_accounts[{i}]: 'risk_percentage' must be 0 when top-level uses 'quantity' sizing "
                    f"(found: {acc.get('risk_percentage', 0)})."
                )
        else:
            # Fallback (close order or placeholder) — basic check
            if _acc_risk <= 0 and _acc_qmul <= 0:
                _pending_acc_invalid.append(
                    f"multiple_accounts[{i}]: either 'risk_percentage' or 'quantity_multiplier' must be > 0. "
                    f"Both are zero or missing."
                )

    # Options-specific required fields (only when inst_type = OPT)
    inst_type = str(d.get("inst_type", "") or "").upper()
    if str(d.get("platform", "") or "").upper() == "TRADOVATE" and not inst_type:
        inst_type = "FUT"
    if inst_type == "OPT":
        if not str(d.get("option_type", "") or "").strip():
            missing.append("option_type (expected: call / put)")
        if not str(d.get("expiry_date", "") or "").strip():
            missing.append("expiry_date (e.g. T1, T2, T3, or a date)")
        try:
            strike = float(d.get("order_strike", 0) or 0)
        except (ValueError, TypeError):
            strike = 0
        if strike == 0:
            missing.append("order_strike (the strike price, e.g. 237.30)")

    # ------------------------------------------------------------------ #
    # Risk-based sizing requires a Stop Loss
    # ------------------------------------------------------------------ #
    requires_sl_for_risk = risk_pct > 0
    if not requires_sl_for_risk:
        for acc in multiple_accs_raw:
            try:
                if float(acc.get("risk_percentage", 0) or 0) > 0:
                    requires_sl_for_risk = True
                    break
            except (ValueError, TypeError):
                pass
                
    if requires_sl_for_risk and not is_close:
        has_stop_loss = False
        for sl_key in ["sl", "dollar_sl", "percentage_sl"]:
            sl_val = d.get(sl_key)
            if is_placeholder(sl_val):
                has_stop_loss = True
                break
            try:
                if float(sl_val or 0) > 0:
                    has_stop_loss = True
                    break
            except (ValueError, TypeError):
                pass
        
        if not has_stop_loss:
            missing.append("stop_loss (sl, dollar_sl, or percentage_sl must be > 0 when using risk_percentage)")

    # ------------------------------------------------------------------ #
    # Limit/Stop orders require a valid price
    # ------------------------------------------------------------------ #
    raw_otype = str(d.get("order_type", "")).strip().upper()
    if raw_otype in {"LMT", "LIMIT", "STP", "STOP", "STOPLIMIT", "STPLMT"}:
        raw_p = d.get("price", 0)
        if is_placeholder(raw_p):
            p = 1
        else:
            try:
                p = float(raw_p or 0)
            except (ValueError, TypeError):
                p = 0
        if p <= 0:
            missing.append(f"price (required and must be > 0 for {raw_otype} orders)")

    if missing:
        return {
            "error": True,
            "missing_fields": missing,
            "invalid_fields": [],
            "warnings": [],
            "description": f"Missing required field(s): {', '.join(missing)}. Please add them and try again."
        }

    # ------------------------------------------------------------------ #
    # 1b. Value validation (fields present but wrong value)
    # ------------------------------------------------------------------ #
    invalid = []
    invalid.extend(_pending_acc_invalid)  # flush deferred multiple_accounts sizing errors

    if "date" in d:
        date_val = d["date"]
        if date_val and not is_placeholder(date_val):
            try:
                datetime.datetime.strptime(str(date_val), "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                invalid.append(
                    "date: expected a placeholder (e.g. {{timenow}}) or "
                    "exact format 'YYYY-MM-DDTHH:MM:SSZ' (e.g. 2024-05-17T10:30:00Z)"
                )

    VALID_SIDES = {"BUY", "SELL", "LONG", "SHORT", "CLOSE", "FLAT"}
    if raw_side and raw_side not in VALID_SIDES and not is_placeholder(raw_side):
        invalid.append(
            f"data: '{raw_side}' is not valid — expected one of: buy, sell, long, short, close, flat, "
            f"or a valid placeholder (e.g. {{{{strategy.order.action}}}})"
        )

    VALID_PLATFORMS = {
        "RITHMIC", "PROJECTX", "IB", "TRADOVATE", "BINANCE",
        "TRADELOCKER", "TRADESTATION", "MATCHTRADER", "TRADIER", "BYBIT"
    }
    raw_platform = str(d.get("platform", "") or "").upper()
    if raw_platform and raw_platform not in VALID_PLATFORMS:
        invalid.append(
            f"platform: '{raw_platform}' is not recognised — expected one of: "
            f"{', '.join(sorted(VALID_PLATFORMS))}"
        )

    VALID_ORDER_TYPES = {"MKT", "MARKET", "LMT", "LIMIT", "STP", "STOP", "STOPLIMIT", "STPLMT"}
    raw_otype_val = str(d.get("order_type", "") or "").upper()
    if raw_otype_val and raw_otype_val not in VALID_ORDER_TYPES:
        invalid.append(
            f"order_type: '{raw_otype_val}' is not recognised — expected one of: MKT, LMT, STP, STOPLIMIT"
        )

    if risk_pct < 0 or risk_pct > 100:
        invalid.append(
            f"risk_percentage: {risk_pct} is out of range — must be between 0 and 100"
        )

    # Quantity decimal check
    _raw_qty = d.get("quantity")
    if _raw_qty is not None and not is_placeholder(_raw_qty):
        try:
            _qty = float(_raw_qty)
            if not _qty.is_integer():
                inst_type_check = str(d.get("inst_type", "") or "").upper()
                if inst_type_check in ('FUT', 'FOP', 'OPT', 'OPTIONS'):
                    invalid.append(f"quantity: '{_raw_qty}' contains decimals. Fractional sizes are not supported for {inst_type_check} instruments.")
        except (ValueError, TypeError):
            pass

    # Numeric non-negative checks for TP/SL/trail fields
    for _key in ["tp", "sl", "dollar_tp", "dollar_sl", "percentage_tp",
                 "percentage_sl", "trail_stop", "trail_trigger"]:
        _raw = d.get(_key)
        if _raw is not None and not is_placeholder(_raw):
            try:
                _val = float(_raw)
                if _val < 0:
                    invalid.append(f"{_key}: {_val} must be >= 0")
            except (ValueError, TypeError):
                invalid.append(f"{_key}: '{_raw}' must be a number")

    # trail is a boolean enable flag: only 0 or 1 is valid
    _raw_trail = d.get("trail")
    if _raw_trail is not None and not is_placeholder(_raw_trail):
        try:
            _trail_int = int(float(_raw_trail))
            if _trail_int not in (0, 1):
                invalid.append(f"trail: '{_raw_trail}' is not valid — expected 0 (disabled) or 1 (enabled).")
        except (ValueError, TypeError):
            invalid.append(f"trail: '{_raw_trail}' must be 0 or 1")

    # Trail dependency: trail_stop / trail_trigger require trail to be set
    _trail_val      = float(d.get("trail", 0) or 0)
    _trail_stop_val = float(d.get("trail_stop", 0) or 0)
    _trail_trig_val = float(d.get("trail_trigger", 0) or 0)
    _trail_freq_val = float(d.get("trail_freq", 0) or 0)
    if _trail_stop_val > 0 and _trail_val == 0:
        invalid.append(
            "trail_stop requires trail to also be set — trail_stop is the initial stop "
            "before trailing begins, so trail amount must be specified"
        )
    if _trail_trig_val > 0 and _trail_val == 0:
        invalid.append(
            "trail_trigger requires trail to also be set — trail_trigger is the activation "
            "point for trailing, so trail amount must be specified"
        )

    # Options validation: option_type, expiry_date, order_strike only for OPT/FOP
    if inst_type in ("OPT", "FOP"):
        raw_opt = str(d.get("option_type", "") or "").upper()
        if raw_opt and raw_opt not in ("CALL", "PUT"):
            invalid.append(
                f"option_type: '{raw_opt}' is not valid — expected: call or put"
            )
    else:
        # Restriction: these fields must remain at their default (empty/0) for other instruments
        _opt_val = d.get("option_type", "")
        _exp_val = d.get("expiry_date", "")
        _str_val = d.get("order_strike", 0)

        if _opt_val and not is_placeholder(_opt_val):
            invalid.append(f"option_type: '{_opt_val}' is only permitted when inst_type is OPT or FOP")
        if _exp_val and not is_placeholder(_exp_val):
            invalid.append(f"expiry_date: '{_exp_val}' is only permitted when inst_type is OPT or FOP")
        if _str_val and _str_val != 0 and not is_placeholder(_str_val):
            invalid.append(f"order_strike: '{_str_val}' is only permitted when inst_type is OPT or FOP")

    # (Boolean field strictness is now handled in validate_types above)

    # Strict Order Type enforcement
    raw_otype_check = str(d.get("order_type", "")).strip().upper()
    raw_platform    = str(d.get("platform", "") or "").upper()
    if raw_otype_check and raw_otype_check not in ("MKT", "LMT", "STP", "STPLMT"):
        invalid.append(f"order_type: '{d.get('order_type')}' is not permitted — explicitly expected MKT, LMT, STP, or STPLMT")
    elif raw_otype_check in ("STP", "STPLMT") and not broker_supports_stop_orders(raw_platform):
        invalid.append(f"{raw_platform} only supports MKT and LMT entry orders. {raw_otype_check} is not permitted.")

    # Pyramid restriction: only TRADOVATE supports the pyramid flag
    # We use safe_bool here since boolean normalization hasn't happened yet for the description block
    def get_val_safe_bool(k):
        v = d.get(k, False)
        if isinstance(v, bool): return v
        return str(v).strip().lower() in ("true", "1")

    if get_val_safe_bool("pyramid") and raw_platform != 'TRADOVATE':
        invalid.append("broker doesnot support pyramiding")

    # lmt_to_market_wait: must be a non-negative integer, only valid with order_type LMT
    _raw_lmw = d.get("lmt_to_market_wait")
    if _raw_lmw is not None and not is_placeholder(_raw_lmw):
        try:
            _lmw_f = float(_raw_lmw)
            if not _lmw_f.is_integer() or _lmw_f < 0:
                invalid.append(
                    f"lmt_to_market_wait: '{_raw_lmw}' must be a non-negative integer (seconds to wait before converting LMT to MKT)."
                )
            elif int(_lmw_f) > 0 and raw_otype_check != "LMT":
                invalid.append(
                    f"lmt_to_market_wait: '{int(_lmw_f)}' is only valid when order_type is LMT. "
                    f"Current order_type is '{raw_otype_check or '(not set)'}' — remove lmt_to_market_wait or change order_type to LMT."
                )
        except (ValueError, TypeError):
            invalid.append(f"lmt_to_market_wait: '{_raw_lmw}' must be an integer.")

    if invalid:
        return {
            "error": True,
            "missing_fields": [],
            "invalid_fields": invalid,
            "warnings": [],
            "description": f"Invalid field value(s): {'; '.join(invalid)}. Please correct them and try again."
        }

    # ------------------------------------------------------------------ #
    # 1c. Warnings (valid but suboptimal configurations)
    # ------------------------------------------------------------------ #
    warnings = []

    def check_bracket_capabilities(target_dict, prefix=""):
        _t_val = 0
        try: _t_val = float(target_dict.get("trail", 0) or 0)
        except: pass
        _ts_val = 0
        try: _ts_val = float(target_dict.get("trail_stop", 0) or 0)
        except: pass
        _tt_val = 0
        try: _tt_val = float(target_dict.get("trail_trigger", 0) or 0)
        except: pass
        _tf_val = 0
        try: _tf_val = float(target_dict.get("trail_freq", 0) or 0)
        except: pass
        _b_val = 0
        try: _b_val = float(target_dict.get("breakeven", 0) or 0)
        except: pass

        if _tt_val > 0 and _b_val > 0 and _tt_val < _b_val:
            warnings.append(
                f"{prefix}trail_trigger ({_tt_val}) is less than breakeven ({_b_val}) — "
                f"the trailing stop will surpass the breakeven level before breakeven fires, "
                f"making breakeven redundant. Consider setting trail_trigger >= breakeven."
            )

        # ---- Broker capability cross-check ----
        if raw_platform:
            trail_used = _t_val > 0 or _ts_val > 0 or _tt_val > 0 or _tf_val > 0
            if trail_used and not broker_supports_trailing(raw_platform):
                warnings.append(
                    f"{raw_platform} does not support native API trailing stops. "
                    f"The {prefix}trail/trail_stop/trail_trigger/trail_freq fields will be ignored at runtime."
                )
            else:
                if _ts_val > 0 and not broker_supports_trail_stop(raw_platform):
                    warnings.append(
                        f"{raw_platform} does not support a distinct trailing offset (trail_stop). "
                        f"The {prefix}trail_stop field will be ignored at runtime."
                    )
                if _tt_val > 0 and not broker_supports_trail_trigger(raw_platform):
                    warnings.append(
                        f"{raw_platform} does not support delayed trailing triggers. "
                        f"The {prefix}trail_trigger field will be ignored at runtime."
                    )
                if _tf_val > 0 and not broker_supports_trail_freq(raw_platform):
                    warnings.append(
                        f"{raw_platform} does not support trailing stop frequencies. "
                        f"The {prefix}trail_freq field will be ignored at runtime."
                    )

            if _b_val > 0 and not broker_supports_breakeven(raw_platform):
                warnings.append(
                    f"{raw_platform} does not support native automated breakeven. "
                    f"The {prefix}breakeven field will be ignored at runtime."
                )

    def check_redundant_parameters(target_dict, prefix=""):
        q_raw = target_dict.get("quantity", 0)
        r_raw = target_dict.get("risk_percentage", 0)
        
        q_provided = is_placeholder(q_raw)
        if not q_provided:
            try: q_provided = float(q_raw or 0) > 0
            except: pass
            
        r_provided = is_placeholder(r_raw)
        if not r_provided:
            try: r_provided = float(r_raw or 0) > 0
            except: pass
            
        if q_provided and r_provided:
            warnings.append(
                f"{prefix}Both quantity ({q_raw}) and risk_percentage ({r_raw}%) are provided. "
                f"risk_percentage takes precedence and quantity will be ignored."
            )

        tps = []
        for tp_key in ["tp", "dollar_tp", "percentage_tp"]:
            tp_raw = target_dict.get(tp_key, 0)
            if is_placeholder(tp_raw):
                tps.append(tp_key)
            else:
                try:
                    if float(tp_raw or 0) > 0: tps.append(tp_key)
                except: pass
        if len(tps) > 1:
            warnings.append(
                f"{prefix}Multiple take-profit parameters provided ({', '.join(tps)}). "
                f"Priority order is: tp > dollar_tp > percentage_tp. The highest priority parameter will be used."
            )

        sls = []
        for sl_key in ["sl", "dollar_sl", "percentage_sl"]:
            sl_raw = target_dict.get(sl_key, 0)
            if is_placeholder(sl_raw):
                sls.append(sl_key)
            else:
                try:
                    if float(sl_raw or 0) > 0: sls.append(sl_key)
                except: pass
        if len(sls) > 1:
            warnings.append(
                f"{prefix}Multiple stop-loss parameters provided ({', '.join(sls)}). "
                f"Priority order is: sl > dollar_sl > percentage_sl. The highest priority parameter will be used."
            )

        # TP == SL equality check
        tp_v = target_dict.get("tp")
        sl_v = target_dict.get("sl")
        if tp_v is not None and sl_v is not None:
            if is_placeholder(tp_v) and is_placeholder(sl_v):
                if str(tp_v).strip().lower() == str(sl_v).strip().lower():
                    invalid.append(f"{prefix}tp and sl cannot have the exact same placeholder value ('{tp_v}')")
            else:
                try:
                    _tp = float(tp_v)
                    _sl = float(sl_v)
                    if _tp > 0 and _sl > 0 and _tp == _sl:
                        invalid.append(f"{prefix}tp and sl cannot be exactly the same price ({_tp})")
                except (ValueError, TypeError):
                    pass

    check_redundant_parameters(d)

    # Validate root payload brackets
    check_bracket_capabilities(d)

    multiple_accs_raw_warn = d.get("multiple_accounts", [])
    if isinstance(multiple_accs_raw_warn, list):
        for i, acc in enumerate(multiple_accs_raw_warn):
            if isinstance(acc, dict):
                check_redundant_parameters(acc, prefix=f"multiple_accounts[{i}].")

    # Validate nested multiple target brackets
    advance_tp_sl_raw = d.get("advance_tp_sl", [])
    if isinstance(advance_tp_sl_raw, list):
        for i, acc in enumerate(advance_tp_sl_raw):
            if isinstance(acc, dict):
                check_bracket_capabilities(acc, prefix=f"advance_tp_sl[{i}].")
                check_redundant_parameters(acc, prefix=f"advance_tp_sl[{i}].")

        _update_tp_val = d.get("update_tp", False)
        _update_sl_val = d.get("update_sl", False)
        if (str(_update_tp_val).strip().lower() in ("true", "1") or str(_update_sl_val).strip().lower() in ("true", "1")) and not broker_supports_update_tp_sl(raw_platform):
            warnings.append(
                f"{raw_platform} does not support live updates to active take-profit or stop-loss brackets. "
                f"The update_tp / update_sl fields will be ignored at runtime."
            )

        if inst_type == "OPT" and not broker_supports_options(raw_platform):
            invalid.append(
                f"{raw_platform} does not support options trading. "
                f"inst_type 'OPT' cannot be used with this broker."
            )

        allowed_inst_types = get_allowed_inst_types(raw_platform)
        if allowed_inst_types is not None:
            _check_inst = inst_type if inst_type else 'None (blank)'
            if inst_type not in allowed_inst_types:
                invalid.append(
                    f"{raw_platform} strictly only supports the following instrument types: {', '.join(allowed_inst_types)}. "
                    f"inst_type '{_check_inst}' is not permitted."
                )

        if len(advance_tp_sl_raw) > 0 and raw_platform and not broker_supports_advance_tp_sl(raw_platform):
            invalid.append(
                f"{raw_platform} does not support advance_tp_sl multi-target brackets. "
                f"This feature is currently only supported on Tradovate."
            )

    if invalid:
        return {
            "error": True,
            "missing_fields": [],
            "invalid_fields": invalid,
            "warnings": [],
            "description": f"Invalid field value(s): {'; '.join(invalid)}. Please correct them and try again."
        }

    # ------------------------------------------------------------------ #
    # 2. Normalise key fields
    # ------------------------------------------------------------------ #
    SIDE_MAP = {"LONG": "BUY", "SHORT": "SELL", "FLAT": "CLOSE"}
    side = SIDE_MAP.get(raw_side, raw_side) if raw_side else "BUY"

    def is_positive(val):
        if is_placeholder(val):
            return True
        return isinstance(val, (int, float)) and val > 0

    def format_num(val):
        if is_placeholder(val):
            return str(val)
        try:
            f = float(val)
            return str(int(f)) if f.is_integer() else str(f)
        except (ValueError, TypeError):
            return str(val)

    def safe_float(key):
        val = d.get(key)
        if is_placeholder(val):
            return str(val)
        try:
            return float(val or 0)
        except (ValueError, TypeError):
            return 0
            
    symbol     = str(d.get("symbol", "")).upper()
    platform   = str(d.get("platform", "your broker")).upper() if d.get("platform") else "your broker"
    price      = safe_float("price")
    raw_otype  = str(d.get("order_type", "") or "").upper()
    ORDER_TYPE_MAP = {"MARKET": "MKT", "LIMIT": "LMT", "STOP": "STP", "STOPLIMIT": "STPLMT"}
    order_type = ORDER_TYPE_MAP.get(raw_otype, raw_otype) if raw_otype else None

    tp              = safe_float("tp")
    sl              = safe_float("sl")
    dollar_tp       = safe_float("dollar_tp")
    dollar_sl       = safe_float("dollar_sl")
    percentage_tp   = safe_float("percentage_tp")
    percentage_sl   = safe_float("percentage_sl")
    trail           = safe_float("trail")
    trail_stop      = safe_float("trail_stop")
    trail_trigger   = safe_float("trail_trigger")
    breakeven       = safe_float("breakeven")
    advance_tp_sl   = d.get("advance_tp_sl", []) or []
    multiple_accs   = d.get("multiple_accounts", []) or []
    
    def safe_bool(key, default=False):
        val = d.get(key)
        if is_placeholder(val):
            return str(val)
        if isinstance(val, bool):
            return val
        return default
        
    pyramid         = safe_bool("pyramid", False)
    reverse_close   = safe_bool("reverse_order_close", False)
    dup_allow       = safe_bool("duplicate_position_allow", True)
    connection_name = d.get("connection_name", "")
    update_tp       = safe_bool("update_tp", False)
    update_sl       = safe_bool("update_sl", False)
    # Options fields
    option_type     = str(d.get("option_type", "") or "").upper()   # CALL / PUT
    expiry_date     = str(d.get("expiry_date", "") or "")
    order_strike    = safe_float("order_strike")

    # ------------------------------------------------------------------ #
    # 3. Build description parts
    # ------------------------------------------------------------------ #
    parts = []

    # ---- Line 1: core order sentence ----------------------------------- #
    if side == "CLOSE":
        qty_str = f"{format_num(qty)} contract(s)" if is_positive(qty) else "all"
        qty_detail = f"{qty_str} contract(s)" if is_positive(qty) else "all open positions"
        line1 = f"CLOSE order on {symbol} — closes {qty_detail} via {platform}."
        if update_tp:
            line1 = f"UPDATE TP order on {symbol} via {platform}."
        elif update_sl:
            line1 = f"UPDATE SL order on {symbol} via {platform}."
    else:
        # Order type label
        if order_type in ("LMT", "STPLMT"):
            otype_label = "LIMIT"
        elif order_type in ("STP",):
            otype_label = "STOP"
        else:
            otype_label = "MARKET"

        # Quantity description
        if is_positive(risk_pct):
            qty_str = f"sized by {risk_pct}% risk"
        else:
            qty_str = f"{format_num(qty)} contract(s)"

        # Price tag (only for non-MARKET limit/stop orders)
        price_tag = f" at price {price}" if is_positive(price) and otype_label != "MARKET" else ""

        # Options: inject CALL/PUT + strike + expiry into line 1
        if inst_type == "OPT":
            opt_detail = f"{option_type} option on {symbol} (strike {order_strike}, expiry {expiry_date})"
            line1 = f"{otype_label} {side} {opt_detail} for {qty_str}{price_tag} via {platform}."
        else:
            line1 = f"{otype_label} {side} order on {symbol} for {qty_str}{price_tag} via {platform}."

        if connection_name:
            line1 = line1.rstrip(".") + f" (connection: {connection_name})."

    parts.append(line1)

    # ---- Line 2: TP / SL / trailing ------------------------------------ #
    tp_sl_parts = []

    if len(advance_tp_sl) > 0:
        # Multi-target TP/SL
        target_summaries = []
        for i, t in enumerate(advance_tp_sl, 1):
            t_qty  = t.get("quantity", 0)
            t_tp   = t.get("tp", 0)
            t_sl   = t.get("sl", 0)
            t_dtp  = t.get("dollar_tp", 0)
            t_dsl  = t.get("dollar_sl", 0)
            t_ptp  = t.get("percentage_tp", 0)
            t_psl  = t.get("percentage_sl", 0)
            t_trail = t.get("trail", 0)

            tp_desc = f"TP={t_tp}" if is_positive(t_tp) else (f"TP=${t_dtp}" if is_positive(t_dtp) else (f"TP={t_ptp}%" if is_positive(t_ptp) else "no TP"))
            sl_desc = f"SL={t_sl}" if is_positive(t_sl) else (f"SL=${t_dsl}" if is_positive(t_dsl) else (f"SL={t_psl}%" if is_positive(t_psl) else "no SL"))
            trail_desc = " trailing enabled" if int(float(t_trail or 0)) == 1 else ""
            target_summaries.append(f"Target {i}: {format_num(t_qty)}ct {tp_desc} {sl_desc}{trail_desc}")

        tp_sl_parts.append(f"Multi-target order with {len(advance_tp_sl)} TP/SL targets: {' | '.join(target_summaries)}.")

    elif int(float(trail or 0)) == 1 or is_positive(trail_stop):
        trail_parts = ["Trailing is enabled"]
        if is_positive(trail_trigger):
            trail_parts.append(f"kicks in after {trail_trigger} pts move")
        if is_positive(trail_stop):
            trail_parts.append(f"stops out at {trail_stop} pts")
        tp_sl_parts.append(f"Trailing stop: {', '.join(trail_parts)}.")
    else:
        tp_desc_parts = []
        sl_desc_parts = []

        if is_positive(tp):
            tp_desc_parts.append(f"TP at {tp}")
        if is_positive(dollar_tp):
            tp_desc_parts.append(f"TP at ${dollar_tp} profit")
        if is_positive(percentage_tp):
            tp_desc_parts.append(f"TP at {percentage_tp}%")

        if is_positive(sl):
            sl_desc_parts.append(f"SL at {sl}")
        if is_positive(dollar_sl):
            sl_desc_parts.append(f"SL at ${dollar_sl} loss")
        if is_positive(percentage_sl):
            sl_desc_parts.append(f"SL at {percentage_sl}%")

        if tp_desc_parts or sl_desc_parts:
            all_tp_sl = tp_desc_parts + sl_desc_parts
            tp_sl_parts.append(f"{', '.join(all_tp_sl)}.")
        else:
            tp_sl_parts.append("No TP or SL configured.")

    parts.append(" ".join(tp_sl_parts))

    # ---- Line 3: extra behaviour flags --------------------------------- #
    extras = []
    if len(multiple_accs) > 0:
        extras.append(f"sent to {len(multiple_accs)} accounts simultaneously")
    if raw_platform == 'TRADOVATE':
        if reverse_close and not pyramid:
            extras.append("Reverse Order Close: True, Pyramid: False -> Existing Position (Same Signal): It will be closed | Existing Position (Opposite Signal): It will be closed | New Signal: A new trade opens if not a close signal")
        elif reverse_close and pyramid:
            extras.append("Reverse Order Close: True, Pyramid: True -> Existing Position (Same Signal): It will not be closed | Existing Position (Opposite Signal): It will be closed | New Signal: A new trade opens if not a close signal")
        else:
            extras.append("Reverse Order Close: False -> Existing Position (Same Signal): It will not close the trade | Existing Position (Opposite Signal): It will not close the trade | New Signal: A new trade opens if not a close signal")
    else:
        if pyramid:
            extras.append("pyramid entries allowed")
        if reverse_close:
            extras.append("reverse order close enabled (opposite position closed first)")
    if not dup_allow:
        extras.append("duplicate positions blocked")
    if is_positive(breakeven):
        extras.append(f"breakeven move at {breakeven}")

    if extras:
        parts.append("Also: " + ", ".join(extras) + ".")

    return {
        "error": False,
        "missing_fields": [],
        "invalid_fields": [],
        "warnings": warnings,
        "description": " ".join(parts)
    }
