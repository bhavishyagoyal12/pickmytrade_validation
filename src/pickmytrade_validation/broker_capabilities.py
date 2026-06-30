from enum import Enum
from .enums import Broker, InstrumentType

# Define capabilities mapping
CAPABILITIES = {
    Broker.TRADOVATE: {
        "trailing": True,
        "trail_stop": True,
        "trail_trigger": True,
        "trail_freq": True,
        "breakeven": True,
        "options": False,
        "update_tp_sl": True,
        "advance_tp_sl": True,
        "stop_orders": True,
        "allowed_inst_types": [InstrumentType.FUTURES.value]
    },
    Broker.RITHMIC: {
        "trailing": False,
        "trail_stop": False,
        "trail_trigger": False,
        "trail_freq": False,
        "breakeven": True,
        "options": False,
        "update_tp_sl": False,
        "advance_tp_sl": True,
        "stop_orders": False,
        "allowed_inst_types": [InstrumentType.FUTURES.value]
    },
    Broker.IB: {
        "trailing": False,
        "trail_stop": False,
        "trail_trigger": False,
        "trail_freq": False,
        "breakeven": False,
        "options": True,
        "update_tp_sl": False,
        "advance_tp_sl": True,
        "stop_orders": False,
        "allowed_inst_types": [
            InstrumentType.STOCK.value,
            InstrumentType.FUTURES.value,
            InstrumentType.OPTIONS.value,
            InstrumentType.FOP.value,
            InstrumentType.OPT.value
        ]
    },
    Broker.TRADESTATION: {
        "trailing": True,
        "trail_stop": True,
        "trail_trigger": True,
        "trail_freq": True,
        "breakeven": True,
        "options": True,
        "update_tp_sl": False,
        "advance_tp_sl": True,
        "stop_orders": False,
        "allowed_inst_types": [
            InstrumentType.STOCK.value,
            InstrumentType.FUTURES.value,
            InstrumentType.OPTIONS.value
        ]
    },
    Broker.TRADELOCKER: {
        "trailing": True,
        "trail_stop": True,
        "trail_trigger": True,
        "trail_freq": True,
        "breakeven": True,
        "options": True,
        "update_tp_sl": False,
        "advance_tp_sl": False,
        "stop_orders": False,
        "allowed_inst_types": [
            InstrumentType.CRYPTO.value,
            InstrumentType.EQUITY_CFD.value,
            InstrumentType.FOREX.value
        ]
    },
    Broker.PROJECTX: {
        "trailing": False,
        "trail_stop": False,
        "trail_trigger": False,
        "trail_freq": False,
        "breakeven": False,
        "options": True,
        "update_tp_sl": False,
        "advance_tp_sl": False,
        "stop_orders": False,
        "allowed_inst_types": [
            InstrumentType.STOCK.value,
            InstrumentType.FUTURES.value,
            InstrumentType.OPTIONS.value,
            InstrumentType.FOP.value
        ]
    },
    Broker.BINANCE: {
        "trailing": False,
        "trail_stop": False,
        "trail_trigger": False,
        "trail_freq": False,
        "breakeven": False,
        "options": True,
        "update_tp_sl": False,
        "advance_tp_sl": False,
        "stop_orders": False,
        "allowed_inst_types": [
            InstrumentType.STOCK.value,
            InstrumentType.FUTURES.value,
            InstrumentType.OPTIONS.value,
            InstrumentType.FOP.value
        ]
    },
    Broker.MATCHTRADER: {
        "trailing": False,
        "trail_stop": False,
        "trail_trigger": False,
        "trail_freq": False,
        "breakeven": False,
        "options": True,
        "update_tp_sl": False,
        "advance_tp_sl": False,
        "stop_orders": False,
        "allowed_inst_types": [
            InstrumentType.CFD.value,
            InstrumentType.FOREX.value,
            InstrumentType.FOREXCFD.value,
            InstrumentType.PRED.value
        ]
    },
    Broker.BYBIT: {
        "trailing": False,
        "trail_stop": False,
        "trail_trigger": False,
        "trail_freq": False,
        "breakeven": False,
        "options": True,
        "update_tp_sl": False,
        "advance_tp_sl": False,
        "stop_orders": False,
        "allowed_inst_types": [
            InstrumentType.STOCK.value,
            InstrumentType.FUTURES.value,
            InstrumentType.OPTIONS.value,
            InstrumentType.FOP.value
        ]
    }
}

def _get_broker(broker) -> Broker:
    if isinstance(broker, Broker):
        return broker
    if isinstance(broker, str):
        try:
            return Broker(broker.upper())
        except ValueError:
            pass
    raise ValueError(f"Invalid broker: {broker}")

def get_broker_capabilities(broker) -> dict:
    try:
        b = _get_broker(broker)
        return CAPABILITIES.get(b, {})
    except ValueError:
        return {}

def broker_supports_trailing(broker) -> bool:
    return get_broker_capabilities(broker).get("trailing", False)

def broker_supports_trail_stop(broker) -> bool:
    return get_broker_capabilities(broker).get("trail_stop", False)

def broker_supports_trail_trigger(broker) -> bool:
    return get_broker_capabilities(broker).get("trail_trigger", False)

def broker_supports_trail_freq(broker) -> bool:
    return get_broker_capabilities(broker).get("trail_freq", False)

def broker_supports_breakeven(broker) -> bool:
    return get_broker_capabilities(broker).get("breakeven", False)

def broker_supports_options(broker) -> bool:
    return get_broker_capabilities(broker).get("options", False)

def broker_supports_update_tp_sl(broker) -> bool:
    return get_broker_capabilities(broker).get("update_tp_sl", False)

def broker_supports_advance_tp_sl(broker) -> bool:
    return get_broker_capabilities(broker).get("advance_tp_sl", False)

def broker_supports_stop_orders(broker) -> bool:
    return get_broker_capabilities(broker).get("stop_orders", False)

def get_allowed_inst_types(broker) -> list:
    return get_broker_capabilities(broker).get("allowed_inst_types", [])
