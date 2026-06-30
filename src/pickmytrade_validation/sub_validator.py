from .enums import Broker, OrderType, Side, InstrumentType
from .rules import ORDER_REQUIREMENTS

def check_raw_payload(d, raw_payload, broker):
    if raw_payload:
        clean_str = str(raw_payload).strip()
        if clean_str and (not clean_str.startswith("{") or not clean_str.endswith("}")):
            return True, {
                "error": True,
                "missing_fields": [],
                "invalid_fields": ["Raw JSON payload padding"],
                "warnings": [],
                "description": "Invalid JSON format: There are extra characters outside the JSON object. Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
            }
    if 'quantity' not in d and 'symbol' not in d:
        return True, {
            "error": True,
            "missing_fields": [],
            "invalid_fields": ["Raw JSON payload"],
            "warnings": [],
            "description": "Invalid JSON format: There are extra characters outside the JSON object. Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
        }
    return False, None


def check_type(value, expected_type):
    if expected_type == "str":
        return isinstance(value, str)
    elif expected_type == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    elif expected_type == "float":
        if isinstance(value, bool):
            return False
        try:
            float(value)
            return True
        except Exception:
            return False
    elif expected_type == "bool":
        return isinstance(value, bool)
    elif expected_type == "list":
        return isinstance(value, list)
    return False


def is_active_value(val):
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0 and val != 0.0
    if isinstance(val, str):
        val_str = val.strip()
        if val_str == "" or val_str == "0" or val_str == "0.0":
            return False
        return True
    return bool(val)


def validate_dict(data, schema, prefix="", broker=None, allow_placeholders=False):
    errors = []
    
    # Mutual exclusivity checks for TP
    tp_fields = ('tp', 'percentage_tp', 'dollar_tp')
    active_tps = [f for f in tp_fields if f in data and is_active_value(data[f])]
    if len(active_tps) > 1:
        errors.append(f"{prefix}Only one TP value can be set (choose either tp, percentage_tp, or dollar_tp)")

    # Mutual exclusivity checks for SL
    sl_fields = ('sl', 'percentage_sl', 'dollar_sl')
    active_sls = [f for f in sl_fields if f in data and is_active_value(data[f])]
    if len(active_sls) > 1:
        errors.append(f"{prefix}Only one SL value can be set (choose either sl, percentage_sl, or dollar_sl)")

    # Mutual exclusivity and presence checks for quantity and risk_percentage
    if "quantity" in schema and "risk_percentage" in schema:
        qty_risk_fields = ('quantity', 'risk_percentage')
        active_qty_risk = [f for f in qty_risk_fields if f in data and is_active_value(data[f])]
        if len(active_qty_risk) > 1:
            errors.append(f"{prefix}Only one of quantity or risk_percentage can be set. Please use any one.")
        elif len(active_qty_risk) == 0:
            errors.append(f"{prefix}Either quantity or risk_percentage is required")

    for field, expected_type in schema.items():
        if field == "symbol":
            if field not in data:
                errors.append(f"{prefix}symbol value is missing")
                continue
            # Fall through to check type if present

        elif field == "account_id" and 'account_id' in data and data['account_id'] == "":
            errors.append(f"{prefix}account_id value is missing")
            continue

        elif field == "token" and 'token' in data and str(data['token']).strip() == "":
            errors.append(f"{prefix}token value is empty")
            continue

        elif field in ('trail', 'trail_trigger', 'trail_stop', 'trail_freq'):
            trail_val = data.get('trail', 0)
            if trail_val == 0 or trail_val is None:
                continue
            if field == 'trail':
                if trail_val == 1:
                    has_sl = any(is_active_value(data.get(sl_field)) for sl_field in ('sl', 'percentage_sl', 'dollar_sl'))
                    if not has_sl:
                        errors.append(f"{prefix}sl is missing for trail")
                    
                    for tf in ('trail_stop', 'trail_trigger', 'trail_freq'):
                        if not is_active_value(data.get(tf)):
                            errors.append(f"{prefix}{tf} is missing for trail")
                else:
                    errors.append(f"{prefix}wrong value in trail")
                continue
            else:
                continue

        elif field in ('breakeven', 'breakeven_offset'):
            if data.get('breakeven', 0) == 0 or data.get('breakeven') is None:
                continue

        elif field in ("option_type", "expiry_date", "order_strike"):
            ins_type_val = (data.get('ins_type') or data.get('inst_type') or "").upper()
            if ins_type_val not in (InstrumentType.OPTIONS.value, InstrumentType.OPT.value, InstrumentType.FOP.value):
                continue

        elif field == "order_type" and 'order_type' not in data:
            continue

        elif field == 'price':
            # Price is now unconditionally required if in schema
            pass

        elif field == 'stp_limit_stp_price':
            order_type = (data.get('order_type') or '').upper()
            required_fields = ORDER_REQUIREMENTS.get(order_type, ())
            if field not in required_fields and field not in data:
                continue

        elif field in ('pyramid', 'gtd_in_second', 'risk_percentage', 'quantity_multiplier', 'tp', 'sl', 'dollar_tp', 'dollar_sl', 'percentage_tp', 'percentage_sl') and field not in data:
            continue

        if field not in data:
            errors.append(f"{prefix}{field} is missing")
            continue

        value = data[field]
        if allow_placeholders:
            err = isinstance(value, str) and "{{" in value and "}}" in value
            if not err:
                if not check_type(value, expected_type):
                    et = 'numeric' if expected_type in ['int', 'float'] else expected_type
                    et = 'true/false' if expected_type == 'bool' else et
                    errors.append(f"{prefix}{field} supports {et} value only")
        else:
            if not check_type(value, expected_type):
                et = 'numeric' if expected_type in ['int', 'float'] else expected_type
                et = 'true/false' if expected_type == 'bool' else et
                errors.append(f"{prefix}{field} supports {et} value only")
    return errors


def validate_payload(payload, ALL_FIELDS, ADVANCE_TP_SL_FIELDS, MULTIPLE_ACCOUNT_FIELDS, broker, allow_placeholders=False):
    errors = []
    # Top-level validation
    errors.extend(validate_dict(payload, ALL_FIELDS, broker=broker, allow_placeholders=allow_placeholders))
    # advance_tp_sl validation
    advance_tp_sl = payload.get("advance_tp_sl")
    if isinstance(advance_tp_sl, list):
        for idx, item in enumerate(advance_tp_sl):
            prefix = f"advance_tp_sl[{idx}]."
            errors.extend(
                validate_dict(
                    item,
                    ADVANCE_TP_SL_FIELDS,
                    prefix=prefix, broker=broker, allow_placeholders=allow_placeholders
                )
            )
            # Custom validation for advance_tp_sl item
            has_tp = any(is_active_value(item.get(f)) for f in ('tp', 'percentage_tp', 'dollar_tp'))
            if not has_tp:
                errors.append(f"{prefix}Either tp, percentage_tp, or dollar_tp is required")
                
            has_sl = any(is_active_value(item.get(f)) for f in ('sl', 'percentage_sl', 'dollar_sl'))
            if not has_sl:
                errors.append(f"{prefix}Either sl, percentage_sl, or dollar_sl is required")
                
    # multiple_accounts validation
    multiple_accounts = payload.get("multiple_accounts")
    if not isinstance(multiple_accounts, list) or len(multiple_accounts) == 0:
        errors.append("multiple_accounts must contain at least one account")
    else:
        for idx, item in enumerate(multiple_accounts):
            prefix = f"multiple_accounts[{idx}]."
            errors.extend(
                validate_dict(
                    item,
                    MULTIPLE_ACCOUNT_FIELDS,
                    prefix=prefix, allow_placeholders=allow_placeholders
                )
            )
            # Custom validation for multiple_accounts data
            token = item.get("token")
            if token is None or str(token).strip() == "":
                errors.append(f"{prefix}token value is empty")
                
            risk_pct = item.get("risk_percentage")
            qty_mult = item.get("quantity_multiplier")
            if not is_active_value(risk_pct) and not is_active_value(qty_mult):
                errors.append(f"{prefix}Either risk_percentage or quantity_multiplier is required")
    return errors


def checking_ins_type(payload, broker, allow_placeholders=False):
    errors = []
    ins_type = (payload.get("ins_type") or payload.get("inst_type") or "").upper()
    
    # Normalize broker to Broker enum
    if isinstance(broker, str):
        try:
            broker = Broker(broker.upper())
        except ValueError:
            pass

    if broker == Broker.TRADESTATION:
        valid_ins_types = [InstrumentType.STOCK.value, InstrumentType.FUTURES.value, InstrumentType.OPTIONS.value]
    elif broker == Broker.IB:
        valid_ins_types = [
            InstrumentType.STOCK.value,
            InstrumentType.FUTURES.value,
            InstrumentType.OPTIONS.value,
            InstrumentType.FOP.value,
            InstrumentType.OPT.value
        ]
    elif broker == Broker.TRADELOCKER:
        valid_ins_types = [InstrumentType.CRYPTO.value, InstrumentType.EQUITY_CFD.value, InstrumentType.FOREX.value]
    elif broker == Broker.MATCHTRADER:
        valid_ins_types = [
            InstrumentType.CFD.value,
            InstrumentType.FOREX.value,
            InstrumentType.FOREXCFD.value,
            InstrumentType.PRED.value
        ]
    else:
        valid_ins_types = [
            InstrumentType.STOCK.value,
            InstrumentType.FUTURES.value,
            InstrumentType.OPTIONS.value,
            InstrumentType.FOP.value
        ]
        
    if ins_type not in valid_ins_types:
        errors.append(
            f"Invalid ins type: '{ins_type}'. Valid options are: {', '.join(valid_ins_types)}"
        )
    return errors


def checking_data_type(payload, broker, allow_placeholders=False):
    errors = []
    side_val = (payload.get("data") or "").upper()
    valid_sides = [s.value for s in Side]
    if side_val not in valid_sides:
        errors.append(
            f"Invalid data type: '{side_val}'. Valid options are: {', '.join(valid_sides)}"
        )
    return errors


def checking_order_type(payload, broker, allow_placeholders=False):
    errors = []
    order_type = (payload.get("order_type") or "").upper()
    if order_type == "":
        return []
    
    # Normalize broker to Broker enum
    if isinstance(broker, str):
        try:
            broker = Broker(broker.upper())
        except ValueError:
            pass

    if broker == Broker.TRADOVATE:
        valid_order_types = [o.value for o in OrderType]
    else:
        valid_order_types = [OrderType.MKT.value, OrderType.LMT.value]
        
    if order_type not in valid_order_types:
        errors.append(
            f"Invalid order_type: '{order_type}'. Valid options are: {', '.join(valid_order_types)}"
        )
    return errors
