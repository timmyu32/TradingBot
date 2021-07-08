# TradingBot
## Python Kraken Trading Bot
Uses techical analysis to execute buy and sell orders on thru Kraken's API
Strategy:
  BUYS
  
  
  -If RSI crosses above 30 or 35 and price hits low bollinger band within last 6 candles
     -execute limit buy order... if order is not filled within 15 seconds,    
       -cancel limit order and execute market order
  
  SELLS
  
  
    -If RSI crosses below 65 and price hits high bolligner band within last 6 candles
      -execute limit sell order... if order is not filled within 15 seconds,    
       -cancel limit order and execute market order
       -If SMA50 < SMA200... sell 100% of the position
       -If SMA200 < SMA50... sell 60% of the position and set trailing stop loss for remaining 40%
   
   Libraries involved
    
    -pandas
    -pandas_ta (Technical analysis)
    -numoy
    -requests
    -urllib.parse
    -hashlib
    -hmac
    -plotly
    -discord
