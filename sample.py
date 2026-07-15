import sys
import os

# Add src to python path dynamically
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.pickmytrade_validation import validate_and_describe_tradovate_alert_json

# Test cases data
TEST_CASES = [
    {
        "name": "User Payload 1 (Valid Tradovate Alert with Placeholders)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "",
            "symbol": "NQ1!",
            "date": "{{timenow}}",
            "data": "buy",
            "quantity": 1,
            "risk_percentage": 0,
            "price": "{{close}}",
            "stp_limit_stp_price": 0,
            "update_tp": False,
            "update_sl": False,
            "breakeven_offset": 0,
            "token": "3tBtKt1tWtStNtPtUt9tQt4tA",
            "pyramid": False,
            "same_direction_ignore": False,
            "reverse_order_close": True,
            "order_type": "MKT",
            "advance_tp_sl": [
                {
                    "quantity": 1,
                    "tp": 0,
                    "percentage_tp": 0,
                    "dollar_tp": 1,
                    "sl": 0,
                    "percentage_sl": 0,
                    "dollar_sl": 1,
                    "breakeven": 0,
                    "breakeven_offset": 1,
                    "trail": 0,
                    "trail_stop": 0,
                    "trail_trigger": 0,
                    "trail_freq": 0
                }
            ],
            "multiple_accounts": [
                {
                    "token": "3tBtKt1tWtStNtPtUt9tQt4tA",
                    "account_id": "DEMO6376471",
                    "risk_percentage": 0,
                    "quantity_multiplier": 1
                }
            ]
        }
    },
    {
        "name": "User Payload 2 (Valid Tradovate Alert with No Advance TP/SL)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "",
            "symbol": "NQ1!",
            "date": "{{timenow}}",
            "data": "buy",
            "quantity": 1,
            "risk_percentage": 0,
            "price": "{{close}}",
            "stp_limit_stp_price": 0,
            "update_tp": False,
            "update_sl": False,
            "breakeven_offset": 0,
            "token": "3tBtKt1tWtStNtPtUt9tQt4tA",
            "pyramid": False,
            "same_direction_ignore": False,
            "reverse_order_close": True,
            "order_type": "MKT",
            "multiple_accounts": [
                {
                    "token": "3tBtKt1tWtStNtPtUt9tQt4tA",
                    "account_id": "DEMO6376471",
                    "risk_percentage": 0,
                    "quantity_multiplier": 1
                }
            ]
        }
    },
    {
        "name": "TP Mutual Exclusivity Violation (tp & dollar_tp both active)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "tp": 10.0,
            "dollar_tp": 100.0,
            "token": "valid_token"
        }
    },
    {
        "name": "SL Mutual Exclusivity Violation (sl & percentage_sl both active)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "sl": 15.0,
            "percentage_sl": 1.5,
            "token": "valid_token"
        }
    },
    {
        "name": "Quantity and Risk Percentage Mutual Exclusivity Violation",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 2,
            "risk_percentage": 1,
            "token": "valid_token"
        }
    },
    {
        "name": "Token Key is Empty String",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "token": "   "
        }
    },
    {
        "name": "Trailing Stop Requirements Failure (trail=1 but missing trail_stop)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "sl": 10.0,
            "trail": 1,
            "trail_trigger": 5.0,
            "trail_freq": 1.0,
            "token": "valid_token"
        }
    },
    {
        "name": "Multiple Accounts Violation (neither risk_percentage nor quantity_multiplier set)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "token": "valid_token",
            "multiple_accounts": [
                {
                    "token": "valid_token",
                    "account_id": "ACC1",
                    "risk_percentage": 0,
                    "quantity_multiplier": 0
                }
            ]
        }
    },
    {
        "name": "Advance TP/SL Violation (missing SL field in advance block)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "token": "valid_token",
            "advance_tp_sl": [
                {
                    "quantity": 1,
                    "tp": 10.0
                }
            ]
        }
    },
    {
        "name": "Limit Order Missing Price Check",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "LMT",
            "token": "valid_token"
        }
    },
    {
        "name": "Market Order Omit Price Check (Should Pass)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token"
        }
    },
    {
        "name": "Update TP Success (update_tp is true and tp is non-zero)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "update_tp": True,
            "tp": 10.5,
            "token": "valid_token"
        }
    },
    {
        "name": "Update TP Violation (update_tp is true but tp is zero)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "update_tp": True,
            "tp": 0,
            "token": "valid_token"
        }
    },
    {
        "name": "Update TP Violation (update_tp is true but tp is missing)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "update_tp": True,
            "token": "valid_token"
        }
    },
    {
        "name": "Update SL Success (update_sl is true and sl is non-zero)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "update_sl": True,
            "sl": 5.0,
            "token": "valid_token"
        }
    },
    {
        "name": "Update SL Violation (update_sl is true but sl is zero)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "update_sl": True,
            "sl": 0,
            "token": "valid_token"
        }
    },
    {
        "name": "Update SL Violation (update_sl is true but sl is missing)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "update_sl": True,
            "token": "valid_token"
        }
    },
    {
        "name": "Breakeven Offset Violation (offset >= breakeven)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "breakeven": 10.0,
            "breakeven_offset": 12.0,
            "token": "valid_token"
        }
    },
    {
        "name": "Breakeven Offset Success (offset < breakeven)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "breakeven": 10.0,
            "breakeven_offset": 5.0,
            "token": "valid_token"
        }
    },
    {
        "name": "Breakeven Zero Offset Success (offset is 0)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "breakeven": 10.0,
            "breakeven_offset": 0.0,
            "token": "valid_token"
        }
    },
    {
        "name": "Extra Key Violation (invalid top-level key)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "invalid_top_key": "hello"
        }
    },
    {
        "name": "Extra Key Violation (invalid nested key in advance_tp_sl)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "advance_tp_sl": [
                {
                    "quantity": 1,
                    "tp": 10.0,
                    "sl": 5.0,
                    "invalid_nested_key": "world"
                }
            ]
        }
    },
    {
        "name": "Extra Key Violation (invalid nested key in multiple_accounts)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "multiple_accounts": [
                {
                    "token": "valid_token",
                    "account_id": "ACC1",
                    "quantity_multiplier": 1.0,
                    "invalid_acc_key": "xyz"
                }
            ]
        }
    },
    {
        "name": "Flat/Close Alert with Valid full_closed and comment (Should Pass)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "CLOSE",
            "token": "valid_token",
            "full_closed": True,
            "comment": "closing position due to target reached"
        }
    },
    {
        "name": "Flat/Close Alert with Invalid full_closed Type (Should Fail)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "CLOSE",
            "token": "valid_token",
            "full_closed": "yes",
            "comment": "closing"
        }
    },
    {
        "name": "Flat/Close Alert with Invalid comment Type (Should Fail)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "CLOSE",
            "token": "valid_token",
            "full_closed": False,
            "comment": 12345
        }
    },
    {
        "name": "Ignored Extra Keys (created_first, main_token_type, reverse_action, tif, by_socket, watch_user, main_order_id should be ignored) (Should Pass)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "created_first": "2026-07-09",
            "main_token_type": "demo",
            "reverse_action": True,
            "tif": "GTC",
            "by_socket": True,
            "watch_user": "user123",
            "main_order_id": "ord567"
        }
    },
    {
        "name": "Payload without Multiple Accounts (Should Pass)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token"
        }
    },
    {
        "name": "Payload with Empty Multiple Accounts Violation (Should Fail)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "multiple_accounts": []
        }
    },
    {
        "name": "Top-level Account ID Valid (Should Pass)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "account_id": "ACC123"
        }
    },
    {
        "name": "Top-level Account ID Empty Violation (Should Fail)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "account_id": "   "
        }
    },
    {
        "name": "Top-level Duplicate Position Allow Valid (Should Pass)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "duplicate_position_allow": True
        }
    },
    {
        "name": "Top-level Duplicate Position Allow Invalid Type Violation (Should Fail)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "duplicate_position_allow": "yes"
        }
    },
    {
        "name": "Multiple Accounts and Valid Quantity (Should Pass)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "multiple_accounts": [
                {
                    "token": "valid_token",
                    "account_id": "ACC1",
                    "quantity_multiplier": 1.0
                }
            ]
        }
    },
    {
        "name": "Multiple Accounts and Both Quantity and Risk Percentage Zero Violation (Should Fail)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 0,
            "risk_percentage": 0,
            "order_type": "MKT",
            "token": "valid_token",
            "multiple_accounts": [
                {
                    "token": "valid_token",
                    "account_id": "ACC1",
                    "quantity_multiplier": 1.0
                }
            ]
        }
    },
    {
        "name": "Multiple Accounts and Both Quantity and Risk Percentage Missing Violation (Should Fail)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "order_type": "MKT",
            "token": "valid_token",
            "multiple_accounts": [
                {
                    "token": "valid_token",
                    "account_id": "ACC1",
                    "quantity_multiplier": 1.0
                }
            ]
        }
    },
    {
        "name": "Breakeven with Stop Loss Valid (Should Pass)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "breakeven": 10.5,
            "sl": 5.0
        }
    },
    {
        "name": "Breakeven with Dollar TP Valid (Should Pass)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "breakeven": 10.5,
            "dollar_tp": 100.0
        }
    },
    {
        "name": "Breakeven without Stop Loss or Dollar TP Violation (Should Fail)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "breakeven": 10.5
        }
    },
    {
        "name": "Placeholder with {{ in data (Should Pass)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "{{strategy.order.action}}",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token"
        }
    },
    {
        "name": "Placeholder with {{ in data Violation (Should Fail)",
        "allow_placeholders": False,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "{{strategy.order.action}}",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token"
        }
    },
    {
        "name": "Placeholder with {{ in order_type (Should Pass)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "{{strategy.order.type}}",
            "token": "valid_token"
        }
    },
    {
        "name": "Top-level None Value Violation (Should Fail)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": None,
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token"
        }
    },
    {
        "name": "Nested None Value in advance_tp_sl Violation (Should Fail)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "advance_tp_sl": [
                {
                    "quantity": 1,
                    "tp": None,
                    "sl": 5.0
                }
            ]
        }
    },
    {
        "name": "Nested None Value in multiple_accounts Violation (Should Fail)",
        "allow_placeholders": True,
        "payload": {
            "strategy_name": "Test Strategy",
            "symbol": "ES",
            "date": "2026-06-30",
            "data": "BUY",
            "quantity": 1,
            "order_type": "MKT",
            "token": "valid_token",
            "multiple_accounts": [
                {
                    "token": None,
                    "account_id": "ACC1",
                    "quantity_multiplier": 1.0
                }
            ]
        }
    }
]

def run_tests():
    print("=" * 80)
    print("RUNNING PICKMYTRADE VALIDATION LIBRARY TEST SUITE (TRADOVATE ONLY)")
    print("=" * 80)
    
    passed_count = 0
    failed_count = 0
    
    for idx, tc in enumerate(TEST_CASES, 1):
        print(f"\n[Test {idx}] {tc['name']}")
        print("-" * 50)
        
        payload = tc["payload"]
        allow_placeholders = tc["allow_placeholders"]
        
        # Execute validation using only validate_and_describe_tradovate_alert_json
        res = validate_and_describe_tradovate_alert_json(payload, allow_placeholders=allow_placeholders)
        
        print("Input Payload:")
        import pprint
        pprint.pprint(payload, indent=2, width=120)
        print("\nValidation Result:")
        print(f"  Error: {res['error']}")
        if res['invalid_fields']:
            print(f"  Invalid Fields: {res['invalid_fields']}")
        if res['description']:
            print(f"  Description/Message: {res['description']}")
            
        # Basic heuristic to check if result matched expectation
        should_fail = "Violation" in tc["name"] or "Failure" in tc["name"] or "Empty" in tc["name"] or "Missing" in tc["name"]
        if res["error"] == should_fail:
            print("Status: PASSED")
            passed_count += 1
        else:
            print("Status: FAILED")
            failed_count += 1
            
    print("\n" + "=" * 80)
    print(f"TEST RUN COMPLETED: {passed_count} PASSED, {failed_count} FAILED")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
