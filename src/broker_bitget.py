import ccxt
import time
import pandas as pd
from datetime import datetime

class BitgetBroker:
    """
    Bitget Broker implementation using CCXT.
    Handles live market data fetching and order execution.
    """
    def __init__(self, api_key=None, secret=None, passphrase=None, is_demo=True):
        self.exchange = ccxt.bitget({
            'apiKey': api_key,
            'secret': secret,
            'password': passphrase,
            'enableRateLimit': True,
        })
        
        if is_demo:
            # Note: CCXT supports Bitget demo trading via options
            self.exchange.set_sandbox_mode(True)
            
        print(f" [BITGET] Initialized ({'SANDBOX' if is_demo else 'LIVE'})")

    def get_latest_candles(self, symbol="BTC/USDT", timeframe="1m", limit=30):
        """
        Fetches the most recent candles from Bitget.
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f" [BITGET] Error fetching candles: {e}")
            return None

    def submit_order(self, side, size, symbol="BTC/USDT", price=None, sl=None, tp=None, stealth=True):
        """
        Executes a market or limit order on Bitget.
        """
        try:
            side = side.lower()
            # For simplicity, using market orders here as per the stealth/instant execution requirement
            print(f" [BITGET] Submitting {side.upper()} order for {size} {symbol}...")
            
            # Use market order
            params = {}
            if sl:
                params['stopLossPrice'] = sl
            if tp:
                params['takeProfitPrice'] = tp
                
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=size,
                params=params
            )
            
            print(f" [BITGET] Order Executed: {order['id']}")
            return order['id']
        except Exception as e:
            print(f" [BITGET] Execution Error: {e}")
            return None

    def get_balance(self):
        try:
            balance = self.exchange.fetch_balance()
            return balance['total']
        except Exception as e:
            print(f" [BITGET] Error fetching balance: {e}")
            return None
