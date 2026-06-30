import datetime
import re

from .enums import Broker
from .sub_validator import check_raw_payload, validate_payload, checking_order_type, checking_data_type, checking_ins_type


def generate_description(payload: dict) -> str:
    side = (payload.get("data") or "").upper()
    sym = payload.get("symbol", "")
    qty = payload.get("quantity")
    price = payload.get("price")
    order_type = (payload.get("order_type") or "MKT").upper()
    
    if not sym:
        return ""
        
    if side in ("CLOSE", "FLAT"):
        return f"Close position for {sym}."
        
    parts = []
    if side and qty is not None:
        parts.append(f"{side.capitalize()} {qty} {sym}")
        if order_type == "LMT" and price is not None:
            parts.append(f"at {price} Limit")
        elif order_type == "STP" and price is not None:
            parts.append(f"at {price} Stop")
        elif order_type == "STPLMT" and price is not None:
            stp_price = payload.get("stp_limit_stp_price")
            parts.append(f"at {price} Stop Limit (Stop Price: {stp_price})")
        else:
            parts.append("at Market")
            
        tp = payload.get("tp")
        sl = payload.get("sl")
        if tp:
            parts.append(f"with TP at {tp}")
        if sl:
            parts.append(f"with SL at {sl}")
            
        return " ".join(parts) + "."
    return ""


def validate_and_describe_alert_json(payload: dict, raw_payload=None, allow_placeholders: bool = True) -> dict:
    if not isinstance(payload, dict):
        return {
            "error": True,
            "missing_fields": [],
            "invalid_fields": ["payload"],
            "warnings": [],
            "description": "Payload must be a dictionary."
        }
        
    broker_str = payload.get("broker")
    if not broker_str or not isinstance(broker_str, str):
        return {
            "error": True,
            "missing_fields": ["broker"],
            "invalid_fields": [],
            "warnings": [],
            "description": "Missing or invalid broker field in payload."
        }
    
    try:
        broker = Broker(broker_str.upper())
    except ValueError:
        return {
            "error": True,
            "missing_fields": [],
            "invalid_fields": ["broker"],
            "warnings": [],
            "description": f"Invalid broker: '{broker_str}'."
        }

    is_err, err_res = check_raw_payload(payload, raw_payload, broker)
    if is_err:
        return err_res

    if broker == Broker.TRADOVATE:
        return validate_and_describe_tradovate_alert_json(payload, allow_placeholders)
    elif broker == Broker.RITHMIC:
        return validate_and_describe_rithmic_alert_json(payload, allow_placeholders)
    elif broker == Broker.IB:
        return validate_and_describe_ib_alert_json(payload, allow_placeholders)
    elif broker == Broker.TRADESTATION:
        return validate_and_describe_tradestation_alert_json(payload, allow_placeholders)
    elif broker == Broker.TRADELOCKER:
        return validate_and_describe_tradelocker_alert_json(payload, allow_placeholders)
    elif broker == Broker.PROJECTX:
        return validate_and_describe_projectx_alert_json(payload, allow_placeholders)
    elif broker == Broker.BINANCE:
        return validate_and_describe_binance_alert_json(payload, allow_placeholders)
    elif broker == Broker.MATCHTRADER:
        return validate_and_describe_matchtrader_alert_json(payload, allow_placeholders)
    elif broker == Broker.BYBIT:
        return validate_and_describe_bybit_alert_json(payload, allow_placeholders)
    
    return {
        "error": True,
        "missing_fields": [],
        "invalid_fields": ["broker"],
        "warnings": [],
        "description": f"Unsupported broker: '{broker_str}'."
    }


def validate_and_describe_tradovate_alert_json(d: dict, allow_placeholders: bool = True) -> dict:
    try:
        ALL_FIELDS = {
            "strategy_name": "str", "symbol": "str", "date": "str", "data": "str",
            "quantity": "int", "risk_percentage": "int", "price": "float", "gtd_in_second": "int",
            "stp_limit_stp_price": "float", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float", "dollar_sl": "float", "trail": "float",
            "trail_stop": "float", "trail_trigger": "float", "trail_freq": "float", "update_tp": "bool", "update_sl": "bool", "breakeven": "float",
            "breakeven_offset": "float", "token": "str", "pyramid": "bool", "same_direction_ignore": "bool", "reverse_order_close": "bool", "order_type": "str",
            "advance_tp_sl": "list", "multiple_accounts": "list"
        }
        ADVANCE_TP_SL_FIELDS = {
            "quantity": "int", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float",
            "dollar_sl": "float", "breakeven": "float", "breakeven_offset": "float", "trail": "float", "trail_stop": "float", "trail_trigger": "float",
            "trail_freq": "float"
        }
        MULTIPLE_ACCOUNT_FIELDS = {
            "token": "str", "account_id": "str", "risk_percentage": "float", "quantity_multiplier": "float"
        }
        error1 = checking_data_type(d, broker=Broker.TRADOVATE, allow_placeholders=allow_placeholders)
        error2 = checking_order_type(d, broker=Broker.TRADOVATE, allow_placeholders=allow_placeholders)
        error = validate_payload(d, ALL_FIELDS, ADVANCE_TP_SL_FIELDS, MULTIPLE_ACCOUNT_FIELDS, broker=Broker.TRADOVATE, allow_placeholders=allow_placeholders)
        if error or error1 or error2:
            return {
                "error": True, "missing_fields": [], "invalid_fields": error + error1 + error2, "warnings": [],
                "description": "Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
            }
    except Exception as e:
        return {
            "error": True, "missing_fields": [], "invalid_fields": ["Exception raised"], "warnings": [],
            "description": f"An error occurred during validation: {str(e)}"
        }
    return {
        "error": False, "missing_fields": [], "invalid_fields": [], "warnings": [], "description": generate_description(d)
    }


def validate_and_describe_rithmic_alert_json(d: dict, allow_placeholders: bool = True) -> dict:
    try:
        ALL_FIELDS = {
            "strategy_name": "str", "symbol": "str", "date": "str", "data": "str",
            "quantity": "int", "risk_percentage": "int", "price": "float",
            "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float", "dollar_sl": "float", "breakeven": "float",
            "breakeven_offset": "float", "token": "str", "reverse_order_close": "bool", "order_type": "str",
            "advance_tp_sl": "list", "multiple_accounts": "list"
        }
        ADVANCE_TP_SL_FIELDS = {
            "quantity": "int", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float",
            "dollar_sl": "float", "breakeven": "float", "breakeven_offset": "float", "trail": "float", "trail_stop": "float", "trail_trigger": "float",
            "trail_freq": "float"
        }
        MULTIPLE_ACCOUNT_FIELDS = {
            "token": "str", "account_id": "str", "risk_percentage": "float", "quantity_multiplier": "float"
        }
        error1 = checking_data_type(d, broker=Broker.RITHMIC, allow_placeholders=allow_placeholders)
        error2 = checking_order_type(d, broker=Broker.RITHMIC, allow_placeholders=allow_placeholders)
        error = validate_payload(d, ALL_FIELDS, ADVANCE_TP_SL_FIELDS, MULTIPLE_ACCOUNT_FIELDS, broker=Broker.RITHMIC, allow_placeholders=allow_placeholders)
        if error or error1 or error2:
            return {
                "error": True, "missing_fields": [], "invalid_fields": error + error1 + error2, "warnings": [],
                "description": "Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
            }
    except Exception as e:
        return {
            "error": True, "missing_fields": [], "invalid_fields": ["Exception raised"], "warnings": [],
            "description": f"An error occurred during validation: {str(e)}"
        }
    return {
        "error": False, "missing_fields": [], "invalid_fields": [], "warnings": [], "description": generate_description(d)
    }


def validate_and_describe_ib_alert_json(d: dict, allow_placeholders: bool = True) -> dict:
    try:
        ALL_FIELDS = {
            "strategy_name": "str", "symbol": "str", "date": "str", "data": "str",
            "quantity": "int", "risk_percentage": "int", "price": "float", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float", "dollar_sl": "float",
            "breakeven_offset": "float", "token": "str", "reverse_order_close": "bool", "order_type": "str", "option_type": "str",
            "advance_tp_sl": "list", "multiple_accounts": "list"
        }
        ADVANCE_TP_SL_FIELDS = {
            "quantity": "int", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float",
            "dollar_sl": "float"
        }
        MULTIPLE_ACCOUNT_FIELDS = {
            "token": "str", "account_id": "str", "risk_percentage": "float", "quantity_multiplier": "float"
        }

        error1 = checking_ins_type(d, broker=Broker.IB, allow_placeholders=allow_placeholders)
        error2 = checking_data_type(d, broker=Broker.IB, allow_placeholders=allow_placeholders)
        error3 = checking_order_type(d, broker=Broker.IB, allow_placeholders=allow_placeholders)
        error = validate_payload(d, ALL_FIELDS, ADVANCE_TP_SL_FIELDS, MULTIPLE_ACCOUNT_FIELDS, broker=Broker.IB, allow_placeholders=allow_placeholders)
        if error or error1 or error2 or error3:
            return {
                "error": True, "missing_fields": [], "invalid_fields": error + error1 + error2 + error3, "warnings": [],
                "description": "Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
            }
    except Exception as e:
        return {
            "error": True, "missing_fields": [], "invalid_fields": ["Exception raised"], "warnings": [],
            "description": f"An error occurred during validation: {str(e)}"
        }
    return {
        "error": False, "missing_fields": [], "invalid_fields": [], "warnings": [], "description": generate_description(d)
    }


def validate_and_describe_tradestation_alert_json(d: dict, allow_placeholders: bool = True) -> dict:
    try:
        ALL_FIELDS = {
            "strategy_name": "str", "symbol": "str", "date": "str", "data": "str",
            "quantity": "int", "risk_percentage": "int", "price": "float", "gtd_in_second": "int",
            "stp_limit_stp_price": "float", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float", "dollar_sl": "float", "trail": "float",
            "trail_stop": "float", "trail_trigger": "float", "trail_freq": "float", "breakeven": "float",
            "breakeven_offset": "float", "token": "str", "reverse_order_close": "bool", "order_type": "str", "inst_type": "str",
            "option_type": "str", "expiry_date": "str", "order_strike": "float", "advance_tp_sl": "list", "multiple_accounts": "list"
        }
        ADVANCE_TP_SL_FIELDS = {
            "quantity": "int", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float",
            "dollar_sl": "float"
        }
        MULTIPLE_ACCOUNT_FIELDS = {
            "token": "str", "account_id": "str", "connection_name": "str", "risk_percentage": "float", "quantity_multiplier": "float"
        }
        error1 = checking_ins_type(d, broker=Broker.TRADESTATION, allow_placeholders=allow_placeholders)
        error2 = checking_data_type(d, broker=Broker.TRADESTATION, allow_placeholders=allow_placeholders)
        error3 = checking_order_type(d, broker=Broker.TRADESTATION, allow_placeholders=allow_placeholders)
        error = validate_payload(d, ALL_FIELDS, ADVANCE_TP_SL_FIELDS, MULTIPLE_ACCOUNT_FIELDS, broker=Broker.TRADESTATION, allow_placeholders=allow_placeholders)
        if error or error1 or error2 or error3:
            return {
                "error": True, "missing_fields": [], "invalid_fields": error + error1 + error2 + error3, "warnings": [],
                "description": "Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
            }
    except Exception as e:
        return {
            "error": True, "missing_fields": [], "invalid_fields": ["Exception raised"], "warnings": [],
            "description": f"An error occurred during validation: {str(e)}"
        }
    return {
        "error": False, "missing_fields": [], "invalid_fields": [], "warnings": [], "description": generate_description(d)
    }


def validate_and_describe_tradelocker_alert_json(d: dict, allow_placeholders: bool = True) -> dict:
    try:
        ALL_FIELDS = {
            "strategy_name": "str", "symbol": "str", "date": "str", "data": "str",
            "quantity": "int", "risk_percentage": "int", "price": "float", "gtd_in_second": "int",
            "stp_limit_stp_price": "float", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float", "dollar_sl": "float", "trail": "float",
            "trail_stop": "float", "trail_trigger": "float", "trail_freq": "float", "breakeven": "float",
            "breakeven_offset": "float", "token": "str", "reverse_order_close": "bool", "order_type": "str", "inst_type": "str",
            "option_type": "str", "expiry_date": "str", "order_strike": "float", "multiple_accounts": "list"
        }
        ADVANCE_TP_SL_FIELDS = {
            "quantity": "int", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float",
            "dollar_sl": "float"
        }
        MULTIPLE_ACCOUNT_FIELDS = {
            "token": "str", "account_id": "str", "connection_name": "str", "risk_percentage": "float", "quantity_multiplier": "float"
        }
        error1 = checking_ins_type(d, broker=Broker.TRADELOCKER, allow_placeholders=allow_placeholders)
        error2 = checking_data_type(d, broker=Broker.TRADELOCKER, allow_placeholders=allow_placeholders)
        error3 = checking_order_type(d, broker=Broker.TRADELOCKER, allow_placeholders=allow_placeholders)
        error = validate_payload(d, ALL_FIELDS, ADVANCE_TP_SL_FIELDS, MULTIPLE_ACCOUNT_FIELDS, broker=Broker.TRADELOCKER, allow_placeholders=allow_placeholders)
        if error or error1 or error2 or error3:
            return {
                "error": True, "missing_fields": [], "invalid_fields": error + error1 + error2 + error3, "warnings": [],
                "description": "Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
            }
    except Exception as e:
        return {
            "error": True, "missing_fields": [], "invalid_fields": ["Exception raised"], "warnings": [],
            "description": f"An error occurred during validation: {str(e)}"
        }
    return {
        "error": False, "missing_fields": [], "invalid_fields": [], "warnings": [], "description": generate_description(d)
    }


def validate_and_describe_projectx_alert_json(d: dict, allow_placeholders: bool = True) -> dict:
    try:
        ALL_FIELDS = {
            "strategy_name": "str", "symbol": "str", "date": "str", "data": "str",
            "quantity": "int", "risk_percentage": "int", "price": "float", "gtd_in_second": "int",
            "stp_limit_stp_price": "float", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float", "dollar_sl": "float", "token": "str", "reverse_order_close": "bool", "order_type": "str",
            "option_type": "str", "expiry_date": "str", "order_strike": "float", "multiple_accounts": "list"
        }
        ADVANCE_TP_SL_FIELDS = {
            "quantity": "int", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float",
            "dollar_sl": "float"
        }
        MULTIPLE_ACCOUNT_FIELDS = {
            "token": "str", "account_id": "str", "connection_name": "str", "risk_percentage": "float", "quantity_multiplier": "float"
        }

        error1 = checking_data_type(d, broker=Broker.PROJECTX, allow_placeholders=allow_placeholders)
        error2 = checking_order_type(d, broker=Broker.PROJECTX, allow_placeholders=allow_placeholders)
        error = validate_payload(d, ALL_FIELDS, ADVANCE_TP_SL_FIELDS, MULTIPLE_ACCOUNT_FIELDS, broker=Broker.PROJECTX, allow_placeholders=allow_placeholders)
        if error or error1 or error2:
            return {
                "error": True, "missing_fields": [], "invalid_fields": error + error1 + error2, "warnings": [],
                "description": "Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
            }
    except Exception as e:
        return {
            "error": True, "missing_fields": [], "invalid_fields": ["Exception raised"], "warnings": [],
            "description": f"An error occurred during validation: {str(e)}"
        }
    return {
        "error": False, "missing_fields": [], "invalid_fields": [], "warnings": [], "description": generate_description(d)
    }


def validate_and_describe_binance_alert_json(d: dict, allow_placeholders: bool = True) -> dict:
    try:
        ALL_FIELDS = {
            "strategy_name": "str", "symbol": "str", "date": "str", "data": "str",
            "quantity": "int", "risk_percentage": "int", "price": "float", "gtd_in_second": "int",
            "stp_limit_stp_price": "float", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float", "dollar_sl": "float", "token": "str", "reverse_order_close": "bool", "order_type": "str",
            "option_type": "str", "expiry_date": "str", "order_strike": "float", "multiple_accounts": "list"
        }
        ADVANCE_TP_SL_FIELDS = {
            "quantity": "int", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float",
            "dollar_sl": "float"
        }
        MULTIPLE_ACCOUNT_FIELDS = {
            "token": "str", "account_id": "str", "connection_name": "str", "risk_percentage": "float", "quantity_multiplier": "float"
        }

        error1 = checking_data_type(d, broker=Broker.BINANCE, allow_placeholders=allow_placeholders)
        error2 = checking_order_type(d, broker=Broker.BINANCE, allow_placeholders=allow_placeholders)
        error = validate_payload(d, ALL_FIELDS, ADVANCE_TP_SL_FIELDS, MULTIPLE_ACCOUNT_FIELDS, broker=Broker.BINANCE, allow_placeholders=allow_placeholders)
        if error or error1 or error2:
            return {
                "error": True, "missing_fields": [], "invalid_fields": error + error1 + error2, "warnings": [],
                "description": "Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
            }
    except Exception as e:
        return {
            "error": True, "missing_fields": [], "invalid_fields": ["Exception raised"], "warnings": [],
            "description": f"An error occurred during validation: {str(e)}"
        }
    return {
        "error": False, "missing_fields": [], "invalid_fields": [], "warnings": [], "description": generate_description(d)
    }


def validate_and_describe_matchtrader_alert_json(d: dict, allow_placeholders: bool = True) -> dict:
    try:
        ALL_FIELDS = {
            "strategy_name": "str", "symbol": "str", "date": "str", "data": "str",
            "quantity": "int", "risk_percentage": "int", "price": "float", "gtd_in_second": "int",
            "stp_limit_stp_price": "float", "tp": "float", "percentage_tp": "float", "ins_type": "str",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float", "dollar_sl": "float", "token": "str", "reverse_order_close": "bool",
            "order_type": "str", "option_type": "str", "expiry_date": "str", "order_strike": "float", "multiple_accounts": "list"
        }
        ADVANCE_TP_SL_FIELDS = {
            "quantity": "int", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float",
            "dollar_sl": "float"
        }
        MULTIPLE_ACCOUNT_FIELDS = {
            "token": "str", "account_id": "str", "connection_name": "str", "risk_percentage": "float", "quantity_multiplier": "float"
        }
        error1 = checking_ins_type(d, broker=Broker.MATCHTRADER, allow_placeholders=allow_placeholders)
        error2 = checking_data_type(d, broker=Broker.MATCHTRADER, allow_placeholders=allow_placeholders)
        error3 = checking_order_type(d, broker=Broker.MATCHTRADER, allow_placeholders=allow_placeholders)
        error = validate_payload(d, ALL_FIELDS, ADVANCE_TP_SL_FIELDS, MULTIPLE_ACCOUNT_FIELDS, broker=Broker.MATCHTRADER, allow_placeholders=allow_placeholders)
        if error or error1 or error2 or error3:
            return {
                "error": True, "missing_fields": [], "invalid_fields": error + error1 + error2 + error3, "warnings": [],
                "description": "Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
            }
    except Exception as e:
        return {
            "error": True, "missing_fields": [], "invalid_fields": ["Exception raised"], "warnings": [],
            "description": f"An error occurred during validation: {str(e)}"
        }
    return {
        "error": False, "missing_fields": [], "invalid_fields": [], "warnings": [], "description": generate_description(d)
    }


def validate_and_describe_bybit_alert_json(d: dict, allow_placeholders: bool = True) -> dict:
    try:
        ALL_FIELDS = {
            "strategy_name": "str", "symbol": "str", "date": "str", "data": "str",
            "quantity": "int", "risk_percentage": "int", "price": "float", "gtd_in_second": "int",
            "stp_limit_stp_price": "float", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float", "dollar_sl": "float", "token": "str", "reverse_order_close": "bool",
            "order_type": "str", "option_type": "str", "expiry_date": "str", "order_strike": "float", "multiple_accounts": "list"
        }
        ADVANCE_TP_SL_FIELDS = {
            "quantity": "int", "tp": "float", "percentage_tp": "float",
            "dollar_tp": "float", "sl": "float", "percentage_sl": "float",
            "dollar_sl": "float"
        }
        MULTIPLE_ACCOUNT_FIELDS = {
            "token": "str", "account_id": "str", "connection_name": "str", "risk_percentage": "float", "quantity_multiplier": "float"
        }

        error1 = checking_data_type(d, broker=Broker.BYBIT, allow_placeholders=allow_placeholders)
        error2 = checking_order_type(d, broker=Broker.BYBIT, allow_placeholders=allow_placeholders)
        error = validate_payload(d, ALL_FIELDS, ADVANCE_TP_SL_FIELDS, MULTIPLE_ACCOUNT_FIELDS, broker=Broker.BYBIT, allow_placeholders=allow_placeholders)
        if error or error1 or error2:
            return {
                "error": True, "missing_fields": [], "invalid_fields": error + error1 + error2, "warnings": [],
                "description": "Please ensure your TradingView message strictly starts with '{' and ends with '}' and contains no extraneous text."
            }
    except Exception as e:
        return {
            "error": True, "missing_fields": [], "invalid_fields": ["Exception raised"], "warnings": [],
            "description": f"An error occurred during validation: {str(e)}"
        }
    return {
        "error": False, "missing_fields": [], "invalid_fields": [], "warnings": [], "description": generate_description(d)
    }
