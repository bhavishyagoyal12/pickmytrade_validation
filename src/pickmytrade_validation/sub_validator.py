

def check_raw_payload(d,raw_payload,broker):
    if raw_payload:
        clean_str = str(raw_payload).strip()
        if clean_str and (not clean_str.startswith("{") or not clean_str.endswith("}")):
            return True,{
                "error": True,
                "missing_fields": [],
                "invalid_fields": ["Raw JSON payload padding"],
                "warnings": [],
                "description": "Invalid JSON format: There are extra characters outside the JSON object. Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
            }
    if not 'quantity' in d and not 'symbol' in d:
        return True,{
            "error": True,
            "missing_fields": [],
            "invalid_fields": ["Raw JSON payload"],
            "warnings": [],
            "description": "Invalid JSON format: There are extra characters outside the JSON object. Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
        }
    return False,None



def check_type(value, expected_type):
    if expected_type == "str":
        return isinstance(value, str)
    elif expected_type == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    elif expected_type == "float":
        try:
            float(value)
            return True
        except Exception:
            return False
        # return isinstance(value, (int, float)) and not isinstance(value, bool)
    elif expected_type == "bool":
        return isinstance(value, bool)
    elif expected_type == "list":
        return isinstance(value, list)
    return False

def validate_dict(data, schema, prefix="",broker=None,allow_placeholders=False):
    errors = []
    for field, expected_type in schema.items():
        # if broker == 'TRADOVATE':
            # not checking non required field
        if field == "account_id" and 'account_id' in data and data['account_id'] == "":
            errors.append(f"account_id value is missing")
            continue
        if (field == 'trail' or field == 'trail_trigger' or field == 'trail_stop' or field == 'trail_freq'):
            if 'trail' not in data or data['trail'] == 0:
                continue
            elif 'trail' in data:
                if data['trail'] == 1:
                    if ('sl' not in data or data['sl'] == 0) and ('percentage_sl' not in data or data['percentage_sl'] == 0) and ('dollar_sl' not in data or data['dollar_sl'] == 0):
                        errors.append(f"sl is missing for trail")
                    continue
                else:
                    errors.append(f"wrong value in trail")
                    continue

        elif (field == 'breakeven' or field == 'breakeven_offset'):
            if 'breakeven' not in data or data['breakeven'] == 0:
                continue
        elif (field == 'pyramid',field == 'gtd_in_second' or field == 'risk_percentage'or field == 'tp'or field == 'sl'or field == 'dollar_tp'or field == 'dollar_sl'or field == 'percentage_tp'or field == 'percentage_sl') and field not in data:
            continue
        elif (field == "option_type" or field == "expiry_date" or field == "order_strike"):
            if 'inst_type' not in data or data['inst_type'] != "OPTIONS":
                continue
        elif (field == "order_type") and ('order_type' not in data):
            continue

        if field not in data:
            errors.append(f"{prefix}{field} is missing")
            continue
        value = data[field]
        if allow_placeholders:
            err = isinstance(value, str) and "{{" in value and "}}" in value
            if not err:
                if not check_type(value, expected_type):
                    errors.append(
                        f"{prefix}{field} supports {expected_type} value only"
                    )

                # errors.append(
                #     f"{prefix}{field} supports {expected_type} value only"
                # )
        else:
            if not check_type(value, expected_type):
                errors.append(
                    f"{prefix}{field} supports {expected_type} value only"
                )
    return errors

def validate_payload(payload,ALL_FIELDS,ADVANCE_TP_SL_FIELDS,MULTIPLE_ACCOUNT_FIELDS,broker,allow_placeholders=False):
    errors = []
    # Top-level validation
    errors.extend(validate_dict(payload, ALL_FIELDS, broker=broker,allow_placeholders=allow_placeholders))
    # advance_tp_sl validation
    if payload.get("advance_tp_sl"):
        if isinstance(payload.get("advance_tp_sl"), list):
            for idx, item in enumerate(payload["advance_tp_sl"]):
                errors.extend(
                    validate_dict(
                        item,
                        ADVANCE_TP_SL_FIELDS,
                        prefix=f"advance_tp_sl[{idx}].",broker=broker,allow_placeholders=allow_placeholders
                    )
                )
    # multiple_accounts validation
    if isinstance(payload.get("multiple_accounts"), list):
        for idx, item in enumerate(payload["multiple_accounts"]):
            errors.extend(
                validate_dict(
                    item,
                    MULTIPLE_ACCOUNT_FIELDS,
                    prefix=f"multiple_accounts[{idx}].",allow_placeholders=allow_placeholders
                )
            )
    return errors

def checking_ins_type(payload,broker,allow_placeholders=False):
    errors = []
    order_type = payload.get("data", "").upper()
    if broker == 'TRADESTATION':
        valid_order_types = ["STOCK", "FUTURES", "OPTIONS"]
    elif broker == 'IB':
        valid_order_types = ["STOCK", "FUTURES", "OPTIONS","FOP","OPT"]
    elif broker == "TRADELOCKER":
        valid_order_types = ["CRYPTO", "EQUITY_CFD", "FOREX"]
    elif broker == "MATCHTRADER":
        valid_order_types = ["CFD", "FOREX", "FOREXCFD","PRED"]
    else:
        valid_order_types = ["STOCK", "FUTURES", "OPTIONS","FOP"]
    if order_type not in valid_order_types:
        errors.append(
            f"Invalid ins type: '{order_type}'. Valid options are: {', '.join(valid_order_types)}"
        )
    return errors

def checking_data_type(payload,broker,allow_placeholders=False):
    errors = []
    order_type = payload.get("data", "").upper()
    valid_order_types = ["BUY", "SELL", "CLOSE", "LONG", "SHORT", "FLAT"]
    if order_type not in valid_order_types:
        errors.append(
            f"Invalid data type: '{order_type}'. Valid options are: {', '.join(valid_order_types)}"
        )
    return errors

def checking_order_type(payload,broker,allow_placeholders=False):
    errors = []
    order_type = payload.get("order_type", "").upper()
    if order_type:
        return []
    if broker == 'TRADOVATE':
        valid_order_types = ["MKT", "LMT", "STP", "STPLMT"]
    else:
        valid_order_types = ["MKT", "LMT"]
    if order_type not in valid_order_types:
        errors.append(
            f"Invalid order_type: '{order_type}'. Valid options are: {', '.join(valid_order_types)}"
        )
    return errors

# def check_placeholders(val):
#     if isinstance(val, dict):
#         for k, v in val.items():
#             check_placeholders(v, f"{path}.{k}" if path else k, k)
#     elif isinstance(val, list):
#         for i, v in enumerate(val):
#             check_placeholders(v, f"{path}[{i}]", k_name)
#     elif isinstance(val, str):
#         has_double_open = "{{" in val
#         has_double_close = "}}" in val
#         has_single_open = "{" in val
#         has_single_close = "}" in val
#
#         if has_double_open and not has_double_close:
#             placeholder_errors.append(f"{path}: contains '{{{{' but missing '}}}}'")
#         elif has_double_close and not has_double_open:
#             placeholder_errors.append(f"{path}: contains '}}}}' but missing '{{{{'")
#         elif (has_single_open or has_single_close) and not (has_double_open and has_double_close):
#             placeholder_errors.append(f"{path}: placeholders must use double curly braces {{{{}}}}")
#         elif has_double_open and has_double_close and not allow_placeholders:
#             placeholder_errors.append(f"{path}: Placeholders are disabled. Field '{k_name}' must be an explicit value.")
#         elif is_placeholder(val):
#             normalized_val = val.strip().lower()
#
#             # Reject empty placeholders: {{}} or {{   }}
#             inner = re.sub(r'\{\{|\}\}', '', normalized_val).strip()
#             if not inner:
#                 placeholder_errors.append(
#                     f"{path}: placeholder is empty — '{{{{}}}}' has no content inside the braces"
#                 )
#                 return  # no further checks needed
#
#             is_plot_placeholder = bool(
#                 re.match(r'^\{\{plot_?\d+\}\}$', normalized_val) or
#                 re.match(r'^\{\{plot\(.*?\)\}\}$', normalized_val)
#             )
#
#             if k_name in OPEN_PLACEHOLDER_FIELDS:
#                 pass  # price, tp, sl accept any {{...}} — including plot placeholders
#             elif k_name in STRICT_PLACEHOLDER_FIELDS:
#                 # Exact whitelist — only the listed values are allowed
#                 if normalized_val not in STRICT_PLACEHOLDER_FIELDS[k_name]:
#                     placeholder_errors.append(
#                         f"{path}: '{val}' is not a recognized placeholder for '{k_name}'. "
#                         f"Expected one of: " + ", ".join(STRICT_PLACEHOLDER_FIELDS[k_name])
#                     )
#             else:
#                 # Every other field — no placeholders permitted
#                 placeholder_errors.append(
#                     f"{path}: placeholders are not permitted in '{k_name}'"
#                 )
