from enum import Enum

class Broker(Enum):
    TRADOVATE = "TRADOVATE"
    TRADESTATION = "TRADESTATION"
    MATCHTRADER = "MATCHTRADER"
    TRADELOCKER = "TRADELOCKER"
    PROJECTX = "PROJECTX"
    RITHMIC = "RITHMIC"
    BINANCE = "BINANCE"
    BYBIT = "BYBIT"
    IB = "IB"

class OrderType(Enum):
    MKT = "MKT"
    LMT = "LMT"
    STP = "STP"
    STPLMT = "STPLMT"

class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"

class InstrumentType(Enum):
    STOCK = "STOCK"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"
    FOP = "FOP"
    OPT = "OPT"
    CRYPTO = "CRYPTO"
    EQUITY_CFD = "EQUITY_CFD"
    FOREX = "FOREX"
    CFD = "CFD"
    FOREXCFD = "FOREXCFD"
    PRED = "PRED"