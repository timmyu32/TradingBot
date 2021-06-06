import shrimpy
import pandas as pd


class BackTest:
        def __init__(self, public_key, secret_key, exchange, baseAsset, quoteAsset, interval, startTime) -> None:
            self.public_key = public_key
            self.secret_key = secret_key
            self.exchange = exchange
            self.baseAsset = baseAsset
            self.quoteAsset = quoteAsset
            self.interval = interval
            self.startTime = startTime
            self.client = shrimpy.ShrimpyApiClient(self.public_key, self.secret_key)
            

        def getStableAssets(self):
            tradeList = self.client.get_trading_pairs(self.exchange)
            stables = []
            for item in tradeList:
                if item['quoteTradingSymbol'] == 'USD':
                    stables.append( [item['baseTradingSymbol'], item['quoteTradingSymbol']] )
            
            return stables

            

        def write_candle_data(self):
            candles = self.client.get_candles(
                self.exchange,
                self.baseAsset,
                self.quoteAsset,
                self.interval,
                start_time= self.startTime
            )

            # create lists to hold our different data elements
            dates = []
            open_data = []
            high_data = []
            low_data = []
            close_data = []

            # convert from the Shrimpy candlesticks to the plotly graph objects format
            for candle in candles:
                dates.append(candle['time'])
                open_data.append(candle['open'])
                high_data.append(candle['high'])
                low_data.append(candle['low'])
                close_data.append(candle['close'])

            data = {'Dates': dates,
                    'Open Data': open_data,
                    'Close Data': close_data,
                    'Low Data': low_data,
                    'High Data': high_data
                    }

            df = pd.DataFrame(data)
            df.to_csv("{}{}Data.csv".format(self.baseAsset, self.quoteAsset), index = False)
