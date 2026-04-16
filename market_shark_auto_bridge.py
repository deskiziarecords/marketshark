import os
import sys
import time
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Fix import paths for src/ directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(CURRENT_DIR, "src")
sys.path.insert(0, SRC_DIR)

try:
    from vector_db import query_similar
    from reward_system import log_trade, get_adaptive_threshold
    from tokenizer import tokenize_candle
    from broker_bitget import BitgetBroker
except ImportError as e:
    print(f" Import Error: {e}")
    sys.exit(1)

# --- MODULE: MOCK BROKER (THE BRIDGE ENDPOINT) ---
class MockBroker:
    """
    A simulated broker interface for testing the bridge.
    In production, this would be replaced with MetaTrader5, XM, or OANDA API.
    """
    def __init__(self, balance=10000):
        self.balance = balance
        self.open_trades = []
        print(f" [BROKER] Initialized with balance: ${balance}")

    def submit_order(self, side, size, price, sl, tp, stealth=True):
        order_id = len(self.open_trades) + 1
        print(f" [BROKER] EXECUTE {side} | Size: {size:.2f} | Price: {price} | SL: {sl} | TP: {tp} | Stealth: {stealth}")
        self.open_trades.append({
            "id": order_id,
            "side": side,
            "size": size,
            "entry_price": price,
            "sl": sl,
            "tp": tp,
            "timestamp": datetime.now()
        })
        return order_id

# --- MODULE: THE 7-λ RISK GATE (VETO AUTHORITY) ---
class MS_RiskGate:
    def evaluate(self, market_data: dict, confidence: float, side: str) -> bool:
        """
        λ-series risk filters (Simplified implementation)
        """
        # λ6: Displacement Veto - Microstructure Conflict
        # If the candle is strongly bullish but the intent is SELL, veto.
        body = market_data['close'] - market_data['open']
        rng = market_data['high'] - market_data['low']
        body_ratio = abs(body) / (rng if rng > 0 else 0.0001)
        
        dir_actual = "BUY" if body > 0 else "SELL"
        if body_ratio > 0.75 and dir_actual != side:
            print(f" [RISK] λ6 VETO: Displacement Conflict (Body Ratio: {body_ratio:.2f})")
            return False 

        # λ1: Phase Entrapment - Volatility check (Placeholder)
        # In real scenario, use ATR or Volume integral
        return confidence > 0.65 

# --- MODULE: AUTO-TRADE ORCHESTRATOR ---
class MarketSharkAutoTrader:
    def __init__(self, broker_client):
        self.risk = MS_RiskGate()
        self.broker = broker_client
        self.token_history = ""
        self.last_price = 0.0

    def process_candle(self, ohlcv: dict):
        """
        Main loop logic for the bridge.
        """
        # 1. Tokenize the incoming candle
        token = tokenize_candle(
            ohlcv['open'], ohlcv['high'], ohlcv['low'], ohlcv['close']
        )
        self.token_history = (self.token_history + token)[-30:] # Keep last 30 tokens
        self.last_price = ohlcv['close']

        print(f" [BRIDGE] New Candle: {token} | Stream: ...{self.token_history[-10:]}")

        if len(self.token_history) < 5:
            return # Wait for more data

        # 2. Query Memory via Vector DB
        matches = query_similar(self.token_history, n_results=5)
        if not matches:
            return

        best_match = matches[0]
        # Calculate Confidence: (WinRate * 0.7) + (Similarity * 0.3)
        confidence = (best_match['win_rate'] * 0.7) + (best_match['similarity'] * 0.3)
        
        # Adaptive threshold from reward system
        threshold = get_adaptive_threshold(pattern=best_match['pattern'], base=0.72)
        
        intent = "BUY" if best_match.get("avg_rr", 0) > 0 else "SELL"
        
        print(f" [BRIDGE] Match: {best_match['pattern']} | Conf: {confidence:.2f} | Target: {intent} | Thresh: {threshold:.2f}")

        # 3. Apply 7-λ Veto Strategy
        authorized = self.risk.evaluate(ohlcv, confidence, intent)
        
        if authorized and confidence >= threshold:
            # 4. Stealth Execution
            sl_pips = 8
            tp_pips = 16
            
            # SL/TP calculation
            pip_val = 0.0001
            sl_price = ohlcv['close'] - (sl_pips * pip_val) if intent == "BUY" else ohlcv['close'] + (sl_pips * pip_val)
            tp_price = ohlcv['close'] + (tp_pips * pip_val) if intent == "BUY" else ohlcv['close'] - (tp_pips * pip_val)
            
            size = self._kelly_sizing(confidence)
            
            self.broker.submit_order(
                side=intent,
                size=size,
                price=ohlcv['close'],
                sl=round(sl_price, 5),
                tp=round(tp_price, 5),
                stealth=True
            )
            
            # Log initiated trade (as placeholder for later outcome logging)
            log_trade({
                "pattern": best_match['pattern'],
                "tokens": self.token_history,
                "direction": intent,
                "entry_price": ohlcv['close'],
                "confidence": confidence,
                "status": "OPEN"
            })

    def _kelly_sizing(self, confidence):
        # Sizing = Confidence * Stability * 0.02 (2% cap)
        return min(confidence * 0.02, 0.05)

# --- BOOTSTRAP: RUNNING THE BRIDGE ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MarketShark Auto-Bridge")
    parser.add_argument("--live", action="store_true", help="Connect to Bitget for live data/execution")
    args = parser.parse_args()

    print("""
    SHARK BRIDGE ACTIVATED
    Connecting Token Stream -> Vector DB -> Risk Gate -> Broker
    """)
    
    if args.live:
        print(" [MODE] LIVE BITGET CONNECTION")
        # In a real scenario, use python-dotenv here
        key = os.getenv("BITGET_API_KEY")
        secret = os.getenv("BITGET_SECRET")
        pw = os.getenv("BITGET_PASSPHRASE")
        
        if not key or not secret:
            print(" [ERROR] Missing Bitget credentials! Set BITGET_API_KEY, BITGET_SECRET, and BITGET_PASSPHRASE.")
            sys.exit(1)
            
        broker = BitgetBroker(api_key=key, secret=secret, passphrase=pw, is_demo=True)
        trader = MarketSharkAutoTrader(broker)
        
        symbol = os.getenv("BITGET_SYMBOL", "BTC/USDT")
        
        while True:
            print(f"\n [LIVE] Fetching latest {symbol} candle...")
            df = broker.get_latest_candles(symbol=symbol, timeframe="1m", limit=1)
            if df is not None and not df.empty:
                trader.process_candle(df.iloc[0].to_dict())
            
            # Wait for next minute
            time.sleep(60)
    else:
        print(" [MODE] SIMULATION (CSV)")
        broker = MockBroker()
        trader = MarketSharkAutoTrader(broker)
        
        # Load some sample data to simulate a stream
        csv_path = os.path.join(CURRENT_DIR, "data", "eurusd_1min_tokenized.csv")
        if os.path.exists(csv_path):
            print(f" [BRIDGE] Simulating live stream from {csv_path}...")
            df = pd.read_csv(csv_path).tail(50)
            for _, row in df.iterrows():
                trader.process_candle(row.to_dict())
                time.sleep(0.1) # Simulate time gap
        else:
            print(" [ERROR] No data found to simulate stream. Please run tokenize_candles.py first.")
