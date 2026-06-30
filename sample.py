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
