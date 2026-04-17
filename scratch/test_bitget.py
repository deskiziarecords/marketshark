import os
import ccxt
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    key = os.getenv("BITGET_API_KEY")
    secret = os.getenv("BITGET_API_SECRET") or os.getenv("BITGET_SECRET")
    pw = os.getenv("BITGET_PASSPHRASE")
    is_demo = os.getenv("BITGET_IS_DEMO", "True").lower() == "true"

    if not key or not secret or not pw:
        print("[FAIL] Missing credentials in .env")
        return

    try:
        exchange = ccxt.bitget({
            'apiKey': key,
            'secret': secret,
            'password': pw,
        })
        if is_demo:
            exchange.set_sandbox_mode(True)
        
        balance = exchange.fetch_balance()
        print(f"[SUCCESS] Connected to Bitget! Balance: {balance['total']}")
    except Exception as e:
        print(f"[FAIL] Connection error: {e}")

if __name__ == "__main__":
    test_connection()
