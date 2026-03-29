# PickMyTrade Validation Package

A strictly typed alert JSON validation and description engine used by PickMyTrade.

## Features
- **Strictly Typed Hook**: Validates that fields like `quantity` are numbers and `token` are strings.
- **Broker Capabilities Mapping**: Enforces broker-specific constraints (e.g. Rithmic doesn't support STP, Binance uses CRYPTO/FUTURE).
- **Human-Readable Descriptions**: Generates a natural language summary of what the alert JSON will do.
- **Placeholder Support**: Validates and describes TradingView placeholders like `{{strategy.market_position}}`.

## Installation

```bash
pip install git+https://github.com/bhavishyagoyal12/pickmytrade_validation.git
```

## Usage

```python
from pickmytrade_validation import validate_and_describe_alert_json

payload = {
    "token": "your_token",
    "symbol": "ES",
    "quantity": 2,
    "data": "BUY",
    "platform": "RITHMIC",
    "inst_type": "FUT"
}

result = validate_and_describe_alert_json(payload)
if not result["error"]:
    print(result["description"])
else:
    print(f"Error: {result['invalid_fields']}")
```
