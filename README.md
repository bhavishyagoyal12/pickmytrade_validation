# PickMyTrade Validation

Open-source alert JSON validation library used by [PickMyTrade](https://pickmytrade.trade) — a TradingView-to-broker automation platform that connects TradingView alerts to brokers like Rithmic, Tradovate, Interactive Brokers, TradeStation, Binance, Bybit, and more.

This package validates and describes webhook alert payloads before they reach the execution layer. It catches misconfigurations early so traders avoid rejected or unintended orders.

## What it does

- **Validates alert JSON structure** — checks required fields, data types, and allowed values for every supported broker.
- **Enforces broker-specific rules** — for example, Rithmic only supports MKT and LMT orders; ProjectX only supports futures; Tradovate supports pyramiding and multi-target TP/SL.
- **Generates human-readable descriptions** — translates raw JSON into plain English so you can confirm what an alert will do before it fires.
- **Handles TradingView placeholders** — validates `{{strategy.market_position}}`, `{{close}}`, and other dynamic values used in TradingView alert messages.

## Supported Brokers

| Broker | Instrument Types | Trailing Stop | Options |
|---|---|---|---------|
| Rithmic | FUT, FOP | Yes | Yes     |
| Interactive Brokers | STK, FUT, OPT, FOP, CASH | Yes | Yes     |
| Tradovate | FUT | Yes | No       |
| TradeStation | STOCKS, FUTURES, OPTIONS | Yes | Yes     |
| Tradier | STK, OPT | No | Yes     |
| TradeLocker | EQUITY_CFD, FOREX, CRYPTO | Yes | No      |
| ProjectX (TopstepX) | FUT | Yes | No      |
| Binance | CRYPTO, FUTURES | Yes | No      |
| Bybit | CRYPTO, FUTURES | Yes | No      |
| MatchTrader | CFD, FOREX | Yes | No      |

## Installation

```bash
pip install git+https://github.com/bhavishyagoyal12/pickmytrade_validation.git
```

## Quick Start



## API Reference

### `validate_and_describe_alert_json(payload, raw_payload=None, allow_placeholders=True)`

**Parameters:**
- `payload` (dict) — The alert JSON to validate.
- `allow_placeholders` (bool) — Set to `False` to reject TradingView `{{...}}` placeholders and require explicit values.

**Returns a dict with:**
- `error` (bool) — `True` if validation failed.
- `invalid_fields` (list) — Fields present but with invalid values.
- `warnings` (list) — Non-blocking issues (e.g., broker ignoring unsupported parameters).
- `description` (str) — Human-readable summary of what the alert will do.


## FAQ

### What is PickMyTrade?

[PickMyTrade](https://pickmytrade.trade) is a trading automation platform that connects TradingView alerts to live broker accounts. When a TradingView strategy generates a signal, PickMyTrade receives the webhook and places the corresponding order on your broker — supporting futures, stocks, options, crypto, and forex across multiple brokers.

Learn more at [pickmytrade.trade](https://pickmytrade.trade) or [pickmytrade.io](https://pickmytrade.io). Full documentation is available at [docs.pickmytrade.trade](https://docs.pickmytrade.trade) and [docs.pickmytrade.io](https://docs.pickmytrade.io).

### How does this validation package fit into PickMyTrade?

This package is the first layer of defense in the PickMyTrade pipeline. It validates the alert JSON payload structure and broker compatibility before any order is sent to a broker API. This prevents malformed alerts from reaching the execution layer.

### Does this package execute trades?

No. This is a read-only validation and description library. It does not connect to any broker API or place orders. It only checks whether an alert JSON is valid and describes what it would do.

### Which TradingView placeholders are supported?

- **Quantity:** `{{strategy.market_position_size}}`, `{{strategy.order.contracts}}`
- **Side/Action:** `{{strategy.market_position}}`, `{{strategy.order.action}}`
- **Price fields (tp, sl, price):** Any `{{...}}` placeholder including `{{close}}`, `{{open}}`, `{{plot("name")}}`
- **Date:** `{{timenow}}`, `{{time}}`

### Can I use this outside of PickMyTrade?

Yes. This package is open-source and has zero dependencies. If you're building TradingView webhook integrations and need to validate alert payloads against broker-specific rules, you can use it standalone.

### What order types are supported?

- **MKT** — Market order
- **LMT** — Limit order (requires `price`)
- **STP** — Stop order (requires `price`, not supported on all brokers)
- **STPLMT** — Stop-limit order (requires `price`, not supported on all brokers)

## License

MIT
