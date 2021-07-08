from os import close
from re import S
from types import TracebackType
from pandas_ta.momentum.rsi import rsi
from requests.api import request
import OOPBT
import APIWrapper
from datetime import datetime as dt
from datetime import timedelta as td
import pandas as pd
import numpy as np
import pandas_ta as ta
import time

import plotly.graph_objects as go
import requests
from discord import Webhook, RequestsWebhookAdapter

class BotRunner:
    def __init__(self, base, quote, KRAKEN_API_KEY,  KRAKEN_PRIVATE_KEY, SHRIMPY_API_KEY, SHRIMPY_PRIVATE_KEY, WEBHOOK_URL, LEVERAGE=None):
        self.VOLUME = 0
        self.DCA_VOLUME = 0
        self.HOLDING = False
        self.HOLDING_LONG = False
        self.HOLDING_SHORT = False
        self.risk_rate = float(input('Risk Rate '))
        self.stop_loss = -1     #SENTINAL VALUE  (-1)
        self.stop_loss_rate = float(input("Stop loss percentanege "))
        assert self.stop_loss_rate > 0
        self.stop_loss_rate = self.stop_loss_rate /100
        self.trailing_stop = -1 #SENTINAL VALUE  (-1)
        self.trigger = -1
        self.leverage = LEVERAGE
        self.time_frame = input('Time Frame ')
        self.interval = int(self.time_frame)
        self.time_frame += 'm'
        self.save_graph = False
        
        self.base = base
        self.quote = quote
        self.pair  = base + quote
        #base_prec =  the amount of percision kraken allows on a base asset in a pair ... in BTCUSD, BTC is 8 
        #asset_prec =  the amount of percision kraken allows on a base asset in a pair ... in BTCUSD, USD is 1 
        if self.pair == 'BTCUSD':
            self.base_prec = requests.post('https://api.kraken.com/0/public/AssetPairs').json()['result']['XXBTZUSD']['lot_decimals']
            self.asset_prec = requests.post('https://api.kraken.com/0/public/AssetPairs').json()['result']['XXBTZUSD']['pair_decimals']
        else:
            try:
                self.base_prec = requests.post('https://api.kraken.com/0/public/AssetPairs').json()['result']['X' + base + 'Z' + quote]['lot_decimals']
                self.asset_prec = requests.post('https://api.kraken.com/0/public/AssetPairs').json()['result']['X' + base + 'Z' + quote]['pair_decimals']
            except:
                self.base_prec = requests.post('https://api.kraken.com/0/public/AssetPairs').json()['result'][self.pair]['lot_decimals']
                self.asset_prec = requests.post('https://api.kraken.com/0/public/AssetPairs').json()['result'][self.pair]['pair_decimals']

        self.KRAKEN_API_KEY = KRAKEN_API_KEY
        self.KRAKEN_PRIVATE_KEY = KRAKEN_PRIVATE_KEY
        self.SHRIMPY_API_KEY = SHRIMPY_API_KEY
        self.SHRIMPY_PRIVATE_KEY = SHRIMPY_PRIVATE_KEY
        self.webhook = Webhook.from_url(WEBHOOK_URL, adapter=RequestsWebhookAdapter())
        self.client = APIWrapper.Kraken(self.KRAKEN_API_KEY, self.KRAKEN_PRIVATE_KEY)
        self.backTestCSV = None

        self.buySignals = {'dates':[],
                    'prices': []  
                    }

        self.sellSignals = {'dates':[],
                    'prices': []  
                    }
        
        self.accountValue = {'dates':[],
                    'value':[]
                    }

    def write_candles(self) -> None:
        self.backTestCSV = OOPBT.BackTest(self.SHRIMPY_API_KEY,
                self.SHRIMPY_PRIVATE_KEY, 
                'coinbasepro', 
                self.base,
                self.quote,
                self.time_frame,
                startTime=str(dt.now() - (250 * td(minutes=int(self.interval)))).replace(" ", "T") +  "Z"
                )
        self.backTestCSV.write_candle_data()

    def send_message(self, msg) -> None:
        print(msg)
        self.webhook.send(msg)

    def bblow(self, bbdf, cdf) -> bool:
        #if at least one of the last 5 candles has dipped below the lower bollinger band
        retval = False
        for i in range(1,7):
            if bbdf['BBL_20_2.0'].iloc[-1 * i]  >= cdf[-1 * i]:
                print('PRICE DIPPED BELOW LOW BBAND WITHIN LATEST 6 CANDLES')
                print(i)
                return True
        return retval

    def bbhigh(self, bbdf, cdf) -> bool:
        #if at least one of the last 5 candles has peaked above the higher bollinger band
        retval = False
        for i in range(1,7):
            if bbdf['BBU_20_2.0'].iloc[-1 * i]  <= cdf[-1 * i]:
                print('PRICE GOT ABOVE HIGH BBAND WITHIN LATEST 6 CANDLES')
                print(i)
                return True
        return retval
    
    def rsi_cross2(self, rsidf) -> bool:
        retval = False
        print('rsi_cross = ', round(rsidf.iloc[-1], 2))
        if self.HOLDING_LONG:
            if rsidf.iloc[-2] <= 70:
                if rsidf.iloc[-3] > 70:
                    return True
        elif self.HOLDING_SHORT:
            if rsidf.iloc[-2] >= 31:
                if rsidf.iloc[-3] < 31:
                    return True

        print(retval)
        return retval
    
    def rsi_crossLOW(self, rsidf) -> bool:
        retval = False
        print('rsi_cross = ', round(rsidf.iloc[-1], 2))

        if rsidf.iloc[-2] >= 30:
            if rsidf.iloc[-3] < 30:
                return True
        
        if rsidf.iloc[-2] >= 35:
            if rsidf.iloc[-3] < 35:
                return True


        return retval
    
    def rsi_crossHIGH(self, rsidf) -> bool:
        retval = False
        print('rsi_cross = ', round(rsidf.iloc[-1], 2))
        
        if rsidf.iloc[-2] <= 80:
            if rsidf.iloc[-3] > 80:
                return True

        if rsidf.iloc[-2] <= 70:
            if rsidf.iloc[-3] > 70:
                return True

        if rsidf.iloc[-2] <= 65:
            if rsidf.iloc[-3] > 65:
                return True

        return retval

    def momentum(self, cdf) -> float:
        N = 10
        return (cdf[-1]/ cdf[(-1*N)]) - 1

    def bull_market(self, sma50, sma200) -> float:
        if sma50.iloc[-1] >= sma200.iloc[-1]:
            return True
        else:
            return False

    def trailStop(self, trig_price) -> float:
        if self.HOLDING_LONG:
            return round(trig_price * 0.9895, self.asset_prec)
                
        elif self.HOLDING_SHORT:
            return round(trig_price * 1.01, self.asset_prec)

    def bull_strategy(self) -> None:
    
        df = pd.read_csv('{}{}Data.csv'.format(self.base, self.quote))
        #datesF = np.array(df['Dates'])
        high_dataF = np.array(df['High Data'])
        low_dataF = np.array(df['Low Data'])
        close_dataF = np.array(df['Close Data'])
        if self.HOLDING_SHORT:
            self.send_message('CHANGE IN MARKET DIRECTION\n' + str(self.client.close_open_position(round(close_dataF[-1], 1), 'buy')))
            self.HOLDING_SHORT = False
            self.sellSignals['dates'].append(dt.now())
            self.sellSignals['prices'].append(close_dataF[-1])
        
        if self.HOLDING_LONG:
            gain = round((close_dataF[-1] - self.buySignals['prices'][-1]) / self.buySignals['prices'][-1] * 100, 2)
            print("\nCURRENT POSITIONS... ({}%)\n".format(gain))             


        def strat():
            print("------------------------------------")
            print("Current time: {}\n".format(dt.now().isoformat()))
            print("CURRENT CANDLE DATA\n{}\n".format(df.iloc[-1]))
            percentGain = round( (close_dataF[-1] - close_dataF[-2])/close_dataF[-2] * 100,  4) 
            print('CURRENT PRICE = {}...({}%)\n'.format(close_dataF[-1], percentGain))
            #open_dataF = np.array(df['Open Data'])
            #create bollinger bands dataframe
            bbandsDF = ta.bbands(close=df['Close Data'], length=20, std=2.0)
            #create SMA (200 and 50)
            sma50DF = ta.sma(close=df['Close Data'], length=50)
            sma200DF = ta.sma(close=df['Close Data'], length=200)
            #macd---not being used in current algo, could be used to look for 
            #macdDF = ta.macd(close=df['Close Data'])
            #rsi
            rsiDF = ta.rsi(close=df['Close Data'])   
            print("INDICATOR DATA")
            print("SMA50         {}".format(round(sma50DF.iloc[-1], 4)))
            print("SMA200        {}".format(round(sma200DF.iloc[-1], 4)))
            print("Upper BBand   {}".format(round( bbandsDF['BBU_20_2.0'].iloc[-1], 4)))
            print("Lower BBand   {}".format(round( bbandsDF['BBL_20_2.0'].iloc[-1], 4)))
            print("RSI           {}\n".format(round( rsiDF.iloc[-1], 4)))
            if low_dataF[-1] <= bbandsDF['BBL_20_2.0'].iloc[-1]:
                print("Low price below lower band\n")
            elif high_dataF[-1] >= bbandsDF['BBU_20_2.0'].iloc[-1]:
                print("High price above upper band\n")
            else:
                print("Current price within bands\n")
            '''
            BULL STRAT
            1.) IF golden cross
            2.) Close all open positions
            3.) Open long position on margin w/ 1% stop loss  
            4.) If price hits high BBand and RSI crosses below 70... close position
            '''
            if self.trailing_stop != -1:
                if close_dataF[-1] > self.trigger:
                    self.trigger = close_dataF[-1]
                    self.trailing_stop = self.trailStop(self.trigger)
                    #self.send_message("\tTrailing stop = {}".format(self.trailing_stop))
                print("\tTrailing stop = {}".format(self.trailing_stop))


            if sma50DF.iloc[-2] > sma200DF.iloc[-2] and sma50DF.iloc[-3] <= sma200DF.iloc[-3]:
                #if the market has just entered a golden cross...

                
                if self.HOLDING_LONG == False and self.client.has_open_positions() == False:
                    if self.leverage != None:
                        vol = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec) * self.leverage
                    else:
                        vol = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec) 
                    
                    print('Volume  = {}'.format(vol))
                    msg = self.client.place_order(pair= self.pair,
                                            orderType= 'limit',
                                            _type= 'buy',
                                            volume= vol,
                                            price= round(close_dataF[-1], self.asset_prec),
                                            leverage = self.leverage)
                    self.buySignals['dates'].append(dt.now().isoformat())
                    self.buySignals['prices'].append(round(close_dataF[-1], self.asset_prec))
                    self.send_message("long" + str(msg))
                    self.stop_loss= round(close_dataF[-1]* 0.992, self.asset_prec)
                    self.HOLDING_LONG = True
                    self.accountValue['value'].append(self.client.get_portfolio_value())
                    self.accountValue['dates'].append(dt.now()) 
            
            if self.HOLDING_LONG:
                if self.HOLDING_LONG and self.bbhigh(bbandsDF, high_dataF) and self.rsi_cross2(rsiDF) and self.trailing_stop == -1:
                    
                    if self.client.has_open_positions() and self.HOLDING_LONG:
                        
                        self.trailing_stop = self.trailStop(self.trigger)
                        self.trigger = close_dataF[-1]
                elif low_dataF[-1] <= self.trailing_stop and high_dataF[-1] >= self.trailing_stop and self.HOLDING_LONG and close_dataF[-1] <= self.trailing_stop:
                    msg = self.client.close_open_position( round(close_dataF[-1], self.asset_prec), 'sell')
                    self.accountValue['value'].append(self.client.get_portfolio_value())
                    self.accountValue['dates'].append(dt.now())
                    self.stop_loss= -1
                    self.sellSignals['dates'].append(dt.now().isoformat())
                    self.sellSignals['prices'].append(round(close_dataF[-1], self.asset_prec))
                    self.send_message(msg)
                    self.HOLDING_LONG = False
                    self.trailing_stop = -1
                    self.trigger = -1
                elif low_dataF[-1] <= self.stop_loss and high_dataF[-1] >= self.stop_loss and self.HOLDING_LONG:
                    
                    msg = self.client.close_open_position( round(close_dataF[-1], self.asset_prec), 'sell')
                    self.accountValue['value'].append(self.client.get_portfolio_value())
                    self.accountValue['dates'].append(dt.now())
                    self.stop_loss = -1
                    self.trigger = -1
                    self.HOLDING_LONG = False

            elif not self.HOLDING_LONG:
                if self.bblow(bbandsDF, low_dataF) and self.rsi_crossLOW(rsiDF):
                    if self.leverage != None:
                        vol = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec) * self.leverage
                    else:
                        vol = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec) 
                    
                    print('Volume  = {}'.format(vol))
                    msg = self.client.place_order(pair= self.pair,
                                            orderType= 'limit',
                                            _type= 'buy',
                                            volume= vol,
                                            price= round(close_dataF[-1], self.asset_prec),
                                            leverage = self.leverage)

                    self.buySignals['dates'].append(dt.now().isoformat())
                    self.buySignals['prices'].append(round(close_dataF[-1], self.asset_prec))
                    self.send_message("Bull Market bollinger long" + str(msg))
                    self.stop_loss= round(close_dataF[-1]* 0.992, self.asset_prec)
                    self.HOLDING_LONG = True
                    self.accountValue['value'].append(self.client.get_portfolio_value())
                    self.accountValue['dates'].append(dt.now()) 



            print('6 seconds sleep')
            print("------------------------------------")
        strat()

    def bear_strategy(self) -> None:
        df = pd.read_csv('{}{}Data.csv'.format(self.base, self.quote))
        #datesF = np.array(df['Dates'])
        high_dataF = np.array(df['High Data'])
        low_dataF = np.array(df['Low Data'])
        close_dataF = np.array(df['Close Data'])
        if self.HOLDING_LONG:
            self.send_message('CHANGE IN MARKET DIRECTION\n' + str(self.client.close_open_position(round(close_dataF[-1], self.asset_prec), 'sell')))
            
            print('Closed Position..........')
            self.HOLDING_LONG = False
            self.sellSignals['dates'].append(dt.now())
            self.sellSignals['prices'].append(close_dataF[-1])

        
        if self.HOLDING_SHORT:
            gain = round((close_dataF[-1] - self.buySignals['prices'][-1]) / self.buySignals['prices'][-1] * 100, 2)
            print("\nCURRENT POSITIONS... ({}%)\n".format(-1*gain))

        def strat():
            print("------------------------------------")
            print("Current time: {}\n".format(dt.now().isoformat()))
            print("CURRENT CANDLE DATA\n{}\n".format(df.iloc[-1]))
            percentGain = round( (close_dataF[-1] - close_dataF[-2])/close_dataF[-2] * 100,  4) 
            print('CURRENT PRICE = {}...({}%)\n'.format(close_dataF[-1], percentGain))
            #open_dataF = np.array(df['Open Data'])
            #create bollinger bands dataframe
            bbandsDF = ta.bbands(close=df['Close Data'], length=20, std=2.0)
            #create SMA (200 and 50)
            sma50DF = ta.sma(close=df['Close Data'], length=50)
            sma200DF = ta.sma(close=df['Close Data'], length=200)
            #macd---not being used in current algo, could be used to look for 
            #macdDF = ta.macd(close=df['Close Data'])
            #rsi
            rsiDF = ta.rsi(close=df['Close Data'])   
            print("INDICATOR DATA")
            print("SMA50         {}".format(round(sma50DF.iloc[-1], 4)))
            print("SMA200        {}".format(round(sma200DF.iloc[-1], 4)))
            print("Upper BBand   {}".format(round( bbandsDF['BBU_20_2.0'].iloc[-1], 4)))
            print("Lower BBand   {}".format(round( bbandsDF['BBL_20_2.0'].iloc[-1], 4)))
            print("RSI           {}\n".format(round( rsiDF.iloc[-1], 4)))
            if low_dataF[-1] <= bbandsDF['BBL_20_2.0'].iloc[-1]:
                print("Low price below lower band\n")
            elif high_dataF[-1] >= bbandsDF['BBU_20_2.0'].iloc[-1]:
                print("High price above upper band\n")
            else:
                print("Current price within bands\n")
            '''
            BEAR STRAT
            1.) IF not golden cross
            2.) Close all open positions
            3.) Open long short on margin w/ 1% stop loss  
            4.) If price hits low BBand and RSI crosses above 30... close position
            '''
            if self.trailing_stop != -1:
                if close_dataF[-1] < self.trigger:
                    self.trigger = close_dataF[-1]
                    self.trailing_stop = self.trailStop(self.trigger)
                    #self.send_message("\tTrailing stop = {}".format(self.trailing_stop))

                print("\tTrailing stop = {}".format(self.trailing_stop))
                
                
            if sma50DF.iloc[-3] >= sma200DF.iloc[-3] and sma50DF.iloc[-2] < sma200DF.iloc[-2]:
                
                if self.HOLDING_SHORT == False and self.client.has_open_positions() == False:
                    self.stop_loss = round(close_dataF[-1] * 1.0092, self.asset_prec)

                    if self.leverage != None:
                        vol = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec) * self.leverage
                    else:
                        vol = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec)    

                    
                    print('Volume  = {}'.format(vol))
                    msg = self.client.place_order(pair= self.pair,
                                            orderType= 'limit',
                                            _type= 'sell',
                                            volume= vol,
                                            price= round(close_dataF[-1], self.asset_prec),
                                            leverage= self.leverage)

                    self.accountValue['value'].append(self.client.get_portfolio_value())
                    self.accountValue['dates'].append(dt.now())
                    self.buySignals['dates'].append(dt.now().isoformat())
                    self.buySignals['prices'].append(round(close_dataF[-1], self.asset_prec))
                    self.send_message("short" + str(msg))
                    self.HOLDING_SHORT = True
            
            if self.HOLDING_SHORT:
                if self.HOLDING_SHORT and self.bblow(bbandsDF, low_dataF) and self.rsi_cross2(rsiDF) and self.trailing_stop == -1:
                    
                    if self.client.has_open_positions() and self.HOLDING_SHORT:
                        
                        self.trailing_stop = self.trailStop(self.trigger)
                        self.trigger = close_dataF[-1]
                elif low_dataF[-1] <= self.trailing_stop and high_dataF[-1] >= self.trailing_stop and close_dataF[-1] >= self.trailing_stop and self.HOLDING_SHORT:
                    msg = self.client.close_open_position( round(close_dataF[-1], self.asset_prec), 'buy')
                    self.accountValue['value'].append(self.client.get_portfolio_value())
                    self.accountValue['dates'].append(dt.now())
                    self.stop_loss= -1
                    self.sellSignals['dates'].append(dt.now().isoformat())
                    self.sellSignals['prices'].append(round(close_dataF[-1], self.asset_prec))
                    self.send_message(msg)
                    self.HOLDING_SHORT = False
                    self.trailing_stop = -1
                    self.trigger = -1
                elif low_dataF[-1] <= self.stop_loss and high_dataF[-1] >= self.stop_loss and self.HOLDING_SHORT:
                    
                    msg = self.client.close_open_position( round(close_dataF[-1], self.asset_prec), 'buy')
                    self.accountValue['value'].append(self.client.get_portfolio_value())
                    self.accountValue['dates'].append(dt.now())
                    self.stop_loss = -1
                    self.HOLDING_SHORT = False
            
            elif not self.HOLDING_SHORT:
                if self.bbhigh(bbandsDF, high_dataF) and self.rsi_crossHIGH(rsiDF):
                    if self.leverage != None:
                        vol = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec) * self.leverage
                    else:
                        vol = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec) 
                    
                    print('Volume  = {}'.format(vol))
                    msg = self.client.place_order(pair= self.pair,
                                            orderType= 'limit',
                                            _type= 'sell',
                                            volume= vol,
                                            price= round(close_dataF[-1], self.asset_prec),
                                            leverage = self.leverage)

                    self.buySignals['dates'].append(dt.now().isoformat())
                    self.buySignals['prices'].append(round(close_dataF[-1], self.asset_prec))
                    self.send_message("Bear Market Bollinger short" + str(msg))
                    self.stop_loss= round(close_dataF[-1]* 1.0092, self.asset_prec)
                    self.HOLDING_SHORT = True
                    self.accountValue['value'].append(self.client.get_portfolio_value())
                    self.accountValue['dates'].append(dt.now()) 


            print('6 seconds sleep')
            print("------------------------------------")
        strat()

    def algoStrat(self, sma50, sma200) -> None:
        df = pd.read_csv('{}{}Data.csv'.format(self.base, self.quote))
        high_dataF = np.array(df['High Data'])
        low_dataF = np.array(df['Low Data'])
        close_dataF = np.array(df['Close Data'])

        def strat():
            print("------------------------------------")
            print("Current time: {}\n".format(dt.now().isoformat()))
            print("CURRENT CANDLE DATA\n{}\n".format(df.iloc[-1]))
            percentGain = round( (close_dataF[-1] - close_dataF[-2])/close_dataF[-2] * 100,  4) 
            print('CURRENT PRICE = {}...({}%)\n'.format(close_dataF[-1], percentGain))
            #open_dataF = np.array(df['Open Data'])
            #create bollinger bands dataframe
            bbandsDF = ta.bbands(close=df['Close Data'], length=20, std=2.0)
            #create SMA (200 and 50)
            sma50DF = ta.sma(close=df['Close Data'], length=50)
            sma200DF = ta.sma(close=df['Close Data'], length=200)
            
            #macd---not being used in current algo, could be used to look for 
            #macdDF = ta.macd(close=df['Close Data'])
            #rsi
            rsiDF = ta.rsi(close=df['Close Data'])   
            print("INDICATOR DATA")
            print("SMA50         {}".format(round(sma50DF.iloc[-1], 4)))
            print("SMA200        {}".format(round(sma200DF.iloc[-1], 4)))
            print("Upper BBand   {}".format(round( bbandsDF['BBU_20_2.0'].iloc[-1], 4)))
            print("Lower BBand   {}".format(round( bbandsDF['BBL_20_2.0'].iloc[-1], 4)))
            print("RSI           {}\n".format(round( rsiDF.iloc[-1], 4)))
            if low_dataF[-1] <= bbandsDF['BBL_20_2.0'].iloc[-1]:
                print("Low price below lower band\n")
            elif high_dataF[-1] >= bbandsDF['BBU_20_2.0'].iloc[-1]:
                print("High price above upper band\n")
            else:
                print("Current price within bands\n")

            gain = 0
            if self.HOLDING_LONG:
                gain = round((close_dataF[-1] - self.buySignals['prices'][-1]) / self.buySignals['prices'][-1] * 100, 2)
                print("\nCURRENT POSITIONS... ({}%)\n".format(gain)) 
            elif self.HOLDING_SHORT:
                gain = round((close_dataF[-1] - self.buySignals['prices'][-1]) / self.buySignals['prices'][-1] * 100, 2) * -1
                print("\nCURRENT POSITIONS... ({}%)\n".format(gain))

            if self.trailing_stop != -1:
                if self.HOLDING_LONG:
                    if high_dataF[-1] > self.trigger:
                        self.trigger = low_dataF[-1]
                        self.trailing_stop = self.trailStop(self.trigger)
                elif self.HOLDING_SHORT:
                    if low_dataF[-1] < self.trigger:
                        self.trigger = low_dataF[-1]
                        self.trailing_stop = self.trailStop(self.trigger)
                print("\tTrailing stop = {}".format(self.trailing_stop))
            

            if not self.HOLDING_LONG and not self.HOLDING_SHORT:

                if self.bbhigh(bbandsDF, high_dataF) and self.rsi_crossHIGH(rsiDF):
                    if not self.bull_market(sma50, sma200):
                        self.stop_loss = round(close_dataF[-1] * (1 + self.stop_loss_rate), self.asset_prec)

                        if self.leverage != None:
                            vol = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec) * self.leverage
                        else:
                            vol = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec)    

                        
                        msg = self.client.place_order(pair= self.pair,
                                                orderType= 'limit',
                                                _type= 'sell',
                                                volume= vol,
                                                price= round(close_dataF[-1], self.asset_prec),
                                                leverage= self.leverage)

                        self.accountValue['value'].append(self.client.get_portfolio_value())
                        self.accountValue['dates'].append(dt.now())
                        self.buySignals['dates'].append(dt.now().isoformat())
                        self.buySignals['prices'].append(round(close_dataF[-1], self.asset_prec))
                        self.send_message("BBhigh and RSI high...short sell\n" + str(msg))
                        self.HOLDING_SHORT = True

                elif self.bblow(bbandsDF, low_dataF) and self.rsi_crossLOW(rsiDF):
                    if self.bull_market(sma50, sma200):
                        self.stop_loss= round(close_dataF[-1]* (1- self.stop_loss_rate), self.asset_prec)

                        if self.leverage != None:
                            vol = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec) * self.leverage
                        else:
                            vol = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec) 
                        
                        msg = self.client.place_order(pair= self.pair,
                                                orderType= 'limit',
                                                _type= 'buy',
                                                volume= vol,
                                                price= round(close_dataF[-1], self.asset_prec),
                                                leverage = self.leverage)
                        self.buySignals['dates'].append(dt.now().isoformat())
                        self.buySignals['prices'].append(round(close_dataF[-1], self.asset_prec))
                        self.send_message("BBlow and RSI low...long buy\n" + str(msg))
                        self.HOLDING_LONG = True
                        self.accountValue['value'].append(self.client.get_portfolio_value())
                        self.accountValue['dates'].append(dt.now()) 
            
            elif self.HOLDING_LONG and not self.HOLDING_SHORT:
                if self.bbhigh(bbandsDF, high_dataF) and self.rsi_crossHIGH(rsiDF):
                    self.trailing_stop = self.trailStop(self.trigger)
                    self.trigger = close_dataF[-1]
            elif not self.HOLDING_LONG and self.HOLDING_SHORT:
                if self.bblow(bbandsDF, low_dataF) and self.rsi_crossLOW(rsiDF):
                    self.trailing_stop = self.trailStop(self.trigger)
                    self.trigger = close_dataF[-1]
            
            if (low_dataF[-1] <= self.stop_loss and high_dataF[-1] >= self.stop_loss)  or (low_dataF[-1] <= self.trailing_stop and high_dataF[-1] >= self.trailing_stop):
                if self.HOLDING_LONG:
                    msg = self.client.close_open_position( round(close_dataF[-1], self.asset_prec), 'sell')
                    self.send_message("Closing current position...\n"+ str(msg) + "\nPosition P/L..." + str(gain) +"%")
                    self.accountValue['value'].append(self.client.get_portfolio_value())
                    self.accountValue['dates'].append(dt.now())
                    self.stop_loss= -1
                    self.sellSignals['dates'].append(dt.now().isoformat())
                    self.sellSignals['prices'].append(round(close_dataF[-1], self.asset_prec))
                    self.HOLDING_LONG = False
                    self.trailing_stop = -1
                    self.trigger = -1
                elif self.HOLDING_SHORT:
                    msg = self.client.close_open_position( round(close_dataF[-1], self.asset_prec), 'buy')
                    self.send_message("Closing current position...\n"+ str(msg) + "\nPosition P/L..." + str(gain) +"%")
                    self.accountValue['value'].append(self.client.get_portfolio_value())
                    self.accountValue['dates'].append(dt.now())
                    self.stop_loss= -1
                    self.sellSignals['dates'].append(dt.now().isoformat())
                    self.sellSignals['prices'].append(round(close_dataF[-1], self.asset_prec))
                    self.HOLDING_LONG = False
                    self.trailing_stop = -1
                    self.trigger = -1
                    
            print('6 seconds sleep')
            print("------------------------------------")

        strat()    

    def algoStrat2(self, sma50, sma200) -> None:
        self.save_graph = False
        df = pd.read_csv('{}{}Data.csv'.format(self.base, self.quote))
        high_dataF = np.array(df['High Data'])
        low_dataF = np.array(df['Low Data'])
        close_dataF = np.array(df['Close Data'])

        def strat():
            print("------------------------------------")
            print("Current time: {}\n".format(dt.now().isoformat()))
            print("CURRENT CANDLE DATA\n{}\n".format(df.iloc[-1]))
            percentGain = round( (close_dataF[-1] - close_dataF[-2])/close_dataF[-2] * 100,  4) 
            print('CURRENT PRICE = {}...({}%)\n'.format(close_dataF[-1], percentGain))
            #open_dataF = np.array(df['Open Data'])
            #create bollinger bands dataframe
            bbandsDF = ta.bbands(close=df['Close Data'], length=20, std=2.0)
            #create SMA (200 and 50)
            sma50DF = ta.sma(close=df['Close Data'], length=50)
            sma200DF = ta.sma(close=df['Close Data'], length=200)
            
            #macd---not being used in current algo, could be used to look for 
            #macdDF = ta.macd(close=df['Close Data'])
            #rsi
            rsiDF = ta.rsi(close=df['Close Data'])   
            print("INDICATOR DATA")
            print("SMA50         {}".format(round(sma50DF.iloc[-1], 4)))
            print("SMA200        {}".format(round(sma200DF.iloc[-1], 4)))
            print("Upper BBand   {}".format(round( bbandsDF['BBU_20_2.0'].iloc[-1], 4)))
            print("Lower BBand   {}".format(round( bbandsDF['BBL_20_2.0'].iloc[-1], 4)))
            print("RSI           {}\n".format(round( rsiDF.iloc[-1], 4)))
            if low_dataF[-1] <= bbandsDF['BBL_20_2.0'].iloc[-1]:
                print("Low price below lower band\n")
            elif high_dataF[-1] >= bbandsDF['BBU_20_2.0'].iloc[-1]:
                print("High price above upper band\n")
            else:
                print("Current price within bands\n")


            #P/L of current Position
            gain = 0
            if self.HOLDING_LONG:
                gain = round((close_dataF[-1] - self.buySignals['prices'][-1]) / self.buySignals['prices'][-1] * 100, 2)
                print("\nCURRENT POSITIONS... ({}%)\n".format(gain)) 
            
            #if currently in a position, reset the trailing-stop-loss at each higher-high
            if self.trailing_stop != -1:
                if self.HOLDING_LONG:
                    if high_dataF[-1] > self.trigger:
                        if self.trailing_stop > self.trailStop(self.trigger):
                            self.trigger = low_dataF[-1]
                            self.trailing_stop = self.trailStop(self.trigger)
                print("\tTrailing stop = {}".format(self.trailing_stop))
            
            #Start of the  trade strategy
            #If not in a posiion...
            #If price hits low bband and crosses low rsi point... buy and set stop loss
            if not self.HOLDING_LONG and not self.HOLDING_SHORT:
                if self.bblow(bbandsDF, low_dataF) and self.rsi_crossLOW(rsiDF):
                    self.stop_loss= round(close_dataF[-1]* (1- self.stop_loss_rate), self.asset_prec)

                    if self.leverage != None:
                        self.VOLUME = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec) * self.leverage
                    else:
                        self.VOLUME = round(self.client.get_portfolio_value() * self.risk_rate / close_dataF[-1], self.base_prec) 
                    
                    print(self.client.get_portfolio_value())
                    #if market seems to be trending down, cut order volume to 1/3 usual amount 
                    if not self.bull_market(sma50, sma200):
                        self.VOLUME = round(self.VOLUME * 0.33, self.base_prec)
                                    

                    msg = self.client.place_order(pair= self.pair,
                                            orderType= 'limit',
                                            _type= 'buy',
                                            volume= self.VOLUME,
                                            price= round(close_dataF[-1], self.asset_prec)
                                            )

                    time.sleep(15)
                    #if after 15 seconds the limit order has not been filled, replace the order with a market order
                    while self.client.has_open_orders():
                        time.sleep(5)
                        self.client.cancel_order()
                        time.sleep(5)
                        msg = self.client.place_order(pair= self.pair,
                                            orderType= 'market',
                                            _type= 'buy',
                                            volume= self.VOLUME
                                            )                       
                    #update dicts and send Discord messege
                    self.DCA_VOLUME = 0
                    self.buySignals['dates'].append(dt.now().isoformat())
                    self.buySignals['prices'].append(round(close_dataF[-1], self.asset_prec))
                    self.HOLDING_LONG = True
                    self.accountValue['value'].append(self.client.get_portfolio_value())
                    self.accountValue['dates'].append(dt.now()) 
                    self.send_message("BBlow and RSI low...long buy\n" + str(msg) +"\nAccount Value = " +str(self.accountValue['value'][-1]))
        
            elif self.HOLDING_LONG and not self.HOLDING_SHORT and self.DCA_VOLUME == 0:
                if self.bbhigh(bbandsDF, high_dataF) and self.rsi_crossHIGH(rsiDF):
                    #if breaking even break even
                    if close_dataF[-1] > self.buySignals['prices'][-1] * 1.0026:
                        #if high bband is hit and high rsi cross...
                        self.trigger = close_dataF[-1]
                        self.trailing_stop = self.trailStop(self.trigger)
                        
                        if not self.bull_market(sma50, sma200):
                            #if the market seems to be trending down, sell the entire position
                            msg = self.client.place_order(pair= self.pair,
                                                    orderType= 'limit',
                                                    _type= 'sell',
                                                    volume= self.VOLUME,
                                                    price= round(close_dataF[-1], self.asset_prec)
                                                    )

                            time.sleep(15)
                            #if after 15 seconds the limit order has not been filled, replace the order with a market order
                            while self.client.has_open_orders():
                                time.sleep(5)
                                self.client.cancel_order()
                                time.sleep(5)
                                msg = self.client.place_order(pair= self.pair,
                                                    orderType= 'market',
                                                    _type= 'sell',
                                                    volume= self.VOLUME
                                                    )
                            self.save_graph = True
                            self.VOLUME = 0
                            self.accountValue['value'].append(self.client.get_portfolio_value())
                            self.accountValue['dates'].append(dt.now())
                            self.stop_loss = -1
                            self.sellSignals['dates'].append(dt.now().isoformat())
                            self.sellSignals['prices'].append(round(close_dataF[-1], self.asset_prec))
                            self.HOLDING_LONG = False
                            self.trailing_stop = -1
                            self.trigger = -1  
                            self.send_message("Closing 100%  of current position...\n"+ str(msg) + "\nPosition P/L..." + str(gain) +"\nAccount Value = " +str(self.accountValue['value'][-1]) )
                        else:
                            #if the market seems to be trending up
                            self.VOLUME = round(self.VOLUME * 0.6, self.base_prec) 

                            msg = self.client.place_order(pair= self.pair,
                                                    orderType= 'limit',
                                                    _type= 'sell',
                                                    volume= self.VOLUME,
                                                    price= round(close_dataF[-1], self.asset_prec)
                                                    )

                            time.sleep(15)
                            #if after 15 seconds the limit order has not been filled, replace the order with a market order
                            while self.client.has_open_positions():
                                time.sleep(5)
                                self.client.cancel_order()
                                time.sleep(5)
                                msg = self.client.place_order(pair= self.pair,
                                                    orderType= 'market',
                                                    _type= 'sell',
                                                    volume= self.VOLUME
                                                    )  

                            self.send_message("Closing 60%  of current position...\n"+ str(msg) + "\nPosition P/L..." + str(gain) +"%\nTrailing-Stop @..."+ str(self.trailing_stop)  +"\nAccount Value = " +str(self.accountValue['value'][-1]))
                            self.save_graph = True
                            self.accountValue['value'].append(self.client.get_portfolio_value())
                            self.accountValue['dates'].append(dt.now())
                            self.DCA_VOLUME = 1

            if (low_dataF[-1] <= self.stop_loss and high_dataF[-1] >= self.stop_loss)  or (low_dataF[-1] <= self.trailing_stop and high_dataF[-1] >= self.trailing_stop):
                if self.HOLDING_LONG:
                    msg = self.client.place_order(pair= self.pair,
                                            orderType= 'limit',
                                            _type= 'sell',
                                            volume= self.VOLUME,
                                            price= round(close_dataF[-1], self.asset_prec)
                                            )
                    self.save_graph = True
                    self.VOLUME = 0
                    self.accountValue['value'].append(self.client.get_portfolio_value())
                    self.accountValue['dates'].append(dt.now())
                    self.stop_loss= -1
                    self.sellSignals['dates'].append(dt.now().isoformat())
                    self.sellSignals['prices'].append(round(close_dataF[-1], self.asset_prec))
                    self.HOLDING_LONG = False
                    self.trailing_stop = -1
                    self.trigger = -1
                    self.DCA_VOLUME = 0
                    self.send_message("Closing current position...\n"+ str(msg) + "\nPosition P/L..." + str(gain) +"%"  +"\nAccount Value = " +str(self.accountValue['value'][-1]))

            print('7 seconds sleep')
            print("------------------------------------")

        strat()

    def run(self):
        try:
            while True:
                self.write_candles()

                df = pd.read_csv('{}{}Data.csv'.format(self.base, self.quote))
                sma50DF = ta.sma(close=df['Close Data'], length=50)
                sma200DF = ta.sma(close=df['Close Data'], length=200)

                if self.bull_market(sma50DF, sma200DF):
                    print('\tBULL MARKET({} {})'.format(self.pair, self.time_frame))
                    #self.bull_strategy()
                else:
                    print('\tBEAR MARKET({} {})'.format(self.pair, self.time_frame))
                    #self.bear_strategy()

                self.algoStrat2(sma50DF, sma200DF)

                if self.save_graph:
                    df2 = pd.read_csv("AccountValue.csv")
                    dates = list(np.array(df2["Dates"]))
                    values = list(np.array(df2["Values"]))
                    for date in self.accountValue['dates']:
                        dates.append(date)
                    for value in self.accountValue['value']:
                        values.append(value)

                    data = {'Dates': dates,
                            'Values': values,
                            }

                    df3 = pd.DataFrame(data)
                    df3.to_csv("AccountValue.csv", index = False)


                    fig2 = go.Figure()

                    fig2.add_scatter(x= dates, y= values, mode='lines+markers')

                    fig2.write_html("AccountValue.html")
                time.sleep(7)

        except Exception as e:
            print(e)
            self.webhook.send("ERROR: " + str(e))
        
