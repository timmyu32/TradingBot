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


def main(base, quote):
    #example base =  ADA...quote = USD
    pair = base + quote 

    KRAKEN_API_KEY = ''
    KRAKEN_PRIVATE_KEY = ''

    SHRIMPY_API_KEY = ''
    SHRIMPY_PRIVATE_KEY = ''

    WEBHOOK_URL = ''

    webhook = Webhook.from_url(WEBHOOK_URL, adapter=RequestsWebhookAdapter())


    VOLUME = 0
    DCA_VOLUME = 0
    HOLDING = False

    #buy and sell signals dictionary
    buySignals = {'dates':[],
                'prices': []  
                }

    sellSignals = {'dates':[],
                'prices': []  
                }

    #DCA buy and sell signals dictionary            
    DCAbuySignals = {'dates':[],
                'prices': []  
                }
                
    DCAsellSignals = {'dates':[],
                'prices': []  
                }

    accountValue = {'dates':[],
                    'value':[]
                }

    def bblow(bbdf, cdf) -> bool:
        #if at least one of the last 5 candles has dipped below the lower bollinger band
        retval = False
        for i in range(1,6):
            if bbdf['BBL_20_2.0'].iloc[-1 * i]  >= cdf[-1 * i]:
                print('PRICE DIPPED BELOW LOW BBAND WITHIN LATEST 5 CANDLES')
                print(i)
                #print("Low Band= ",round(bbdf['BBL_20_2.0'].iloc[-1 * i], 5), "Candle  Low = ", cdf[-1 * i])
                return True
        return retval

    def bbhigh(bbdf, cdf) -> bool:
        #if at least one of the last 5 candles has peaked above the higher bollinger band
        retval = False
        for i in range(1,6):
            if bbdf['BBU_20_2.0'].iloc[-1 * i]  <= cdf[-1 * i]:
                print('PRICE GOT ABOVE HIGH BBAND WITHIN LATEST 5 CANDLES')
                print(i)
                #print("High Band= ",round(bbdf['BBU_20_2.0'].iloc[-1 * i], 5) , "Candle High = ", cdf[-1 * i])

                return True
        return retval
    
    def rsi_cross(rsidf) -> bool:
        retval = False
        print('rsi_cross = ', round(rsidf.iloc[-1], 2))
        if not HOLDING:
            if rsidf.iloc[-2] >= 30:
                if rsidf.iloc[-3] < 30:
                    retval = True
        else:
            if rsidf.iloc[-1] >= 70:
                    retval = True
        print(retval)
        return retval

        
    def rsi_cross2(rsidf, status) -> bool:
        retval = False
        print('rsi_cross = ', round(rsidf.iloc[-1], 2))

        if status == 'buy':
            if rsidf.iloc[-2] >= 30:
                if rsidf.iloc[-3] < 30:
                    retval = True

        elif status == 'sell':
            if rsidf.iloc[-1] >= 70:
                    retval = True
        print(retval)
        return retval


    client = APIWrapper.Kraken(KRAKEN_API_KEY, KRAKEN_PRIVATE_KEY)
    accountValue['value'].append(client.get_cash_balance())
    accountValue['dates'].append(dt.now())

    try:
        while True:
            #continuous loop to execute trades
            
            #retrieve the last 150 candles
            currentTime = dt.now()  # time in UTC
            print("------------------------------------")
            print("Current time: {}\n".format(currentTime.isoformat()))
            start = currentTime - (150 * td(minutes=15))
            start = str(start).replace(" ", "T") +  "Z"  
            
            backTestCSV = OOPBT.BackTest(SHRIMPY_API_KEY,
                    SHRIMPY_PRIVATE_KEY, 
                    'coinbasepro', 
                    base,
                    quote,
                    '1m',
                    startTime=start
                    )
            
            #write last 150 candles to a CSV
            #consider taking this out? Not sure if this needs to be saved to an external file
            #probably more efficient to have backtestCSV as a dataframe 
            backTestCSV.write_candle_data()

            df = pd.read_csv('{}{}Data.csv'.format(base, quote))
            print("CURRENT CANDLE DATA\n{}\n".format(df.iloc[-1]))
            
            datesF = np.array(df['Dates'])
            high_dataF = np.array(df['High Data'])
            low_dataF = np.array(df['Low Data'])
            close_dataF = np.array(df['Close Data'])
            percentGain = round( (close_dataF[-1] - close_dataF[-2])/close_dataF[-2] * 100,  4) 
            print('CURRENT PRICE = {}...({}%)\n'.format(close_dataF[-1], percentGain))
            if HOLDING:
                print('\t(CURRENT POSITION = %{}'.format(round(close_dataF[-1] - buySignals[-1]/ buySignals[1] * 100, 4)))

            open_dataF = np.array(df['Open Data'])

            #create bollinger bands dataframe
            bbandsDF = ta.bbands(close=df['Close Data'], length=20, std=2.0)
            #create SMA (100 and 20)
            sma50DF = ta.sma(close=df['Close Data'], length=20)
            sma200DF = ta.sma(close=df['Close Data'], length=100)
            #macd---not being used in current algo, could be used to look for 
            #buys when not im GOLDEN CROSS, need further testing
            #   macdDF = ta.macd(close=df['Close Data'])
            #rsi
            rsiDF = ta.rsi(close=df['Close Data'])
            
            print("INDICATOR DATA")
            print("SMA20         {}".format(round(sma50DF.iloc[-1], 4)))
            print("Upper BBand   {}".format(round( bbandsDF['BBU_20_2.0'].iloc[-1], 4)))
            print("Lower BBand   {}".format(round( bbandsDF['BBL_20_2.0'].iloc[-1], 4)))
            print("RSI          {}\n".format(round( rsiDF.iloc[-1], 4)))

            if low_dataF[-1] <= bbandsDF['BBL_20_2.0'].iloc[-1]:
                print("Low price below lower band\n")
            elif high_dataF[-1] >= bbandsDF['BBU_20_2.0'].iloc[-1]:
                print("High price above upper band\n")
            else:
                print("Current price within bands\n")

            #Strategey Rules
            #must be not HOLDING to buy
            #must be HOLDING to sell
            #buy when RSI crosses above 30 AND price of at one of the last 5 candles goes below lowBBand
            #sell when rsi is above 70 and one of the last 5 candles goes above highBBand
            
            riskRate = 0.5   #percent at risk in each position


            #if sma50DF.iloc[-1] > sma200DF.iloc[-1]:
            #print("In GOLDEN CROSS")
            if not HOLDING and rsi_cross(rsiDF) and bblow(bbandsDF, low_dataF):
                #if current price is below LOW bband
                #buy signals ... HOLDING must be False
                
                    buySignals['dates'].append(datesF[-1])
                    HOLDING = True
                    '''
                    PLACE MARKET BUY ORDER
                    '''                
                    accountSize = client.get_cash_balance()     #account size from Kraken API
                    VOLUME = round(accountSize * riskRate / close_dataF[-1], 5)
                    order_price = client.place__market_order(pair, "buy", VOLUME, round(close_dataF[-1] * 1.001, 5) )
                    buySignals['prices'].append(order_price)
                    msg = "Buy signal at {}\n{}".format(buySignals['prices'][-1], buySignals['dates'][-1])
                    print(msg)
                    webhook.send(msg)

            elif HOLDING and (buySignals['prices'][-1] * 1.01 < (close_dataF[-1] )):
                #if you are HOLDING and price of position is below clandle close
                if bbhigh(bbandsDF, high_dataF) and rsi_cross(rsiDF):
                    #if current price is above HIGH bband
                    #sell signals ... HOLDING must be True
                    sellSignals['dates'].append(datesF[-1])
                    HOLDING = False
                    '''
                    PLACE MARKET SELL ORDER
                    '''
                    limit_sell = client.place__market_order(pair, "sell", VOLUME, price=round(close_dataF[-1] * 0.999, 5) )
                    sellSignals['prices'].append(limit_sell)
                    msg = "Sell signal at {}\n{}".format(sellSignals['prices'][-1], sellSignals['dates'][-1])
                    print(msg)
                    webhook.send(msg)

                    accountValue['value'].append(client.get_cash_balance())
                    accountValue['dates'].append(dt.now())

                    #save profit to graph
                    fig2 = go.Figure()
                    fig2.add_scatter(x= accountValue['dates'], y= accountValue['value'], mode='lines+markers')
                    fig2.write_html(pair+"-Profit-Chart.html")

            elif HOLDING and buySignals['prices'][-1] * 0.985 > close_dataF[-1] and DCA_VOLUME==0:
                #DOLLAR COST AVERAGING
                print('seeking DCA oppurtunity')
                if bblow(bbandsDF, low_dataF):
                    if rsi_cross2(rsiDF, 'buy'):
                        #if current price is below LOW bband
                        #buy signals ... HOLDING must be False
                        '''
                        PLACE MARKET BUY ORDER
                        '''
                        accountSize = client.get_cash_balance()    #account size from Kraken API
                        DCA_VOLUME = round(accountSize  / close_dataF[-1], 5)
                        VOLUME += DCA_VOLUME
                        dca_buy = client.place__market_order(pair, "buy", DCA_VOLUME, price=round(close_dataF[-1] * 1.001, 5))
                        DCAbuySignals['prices'].append(dca_buy)
                        DCAbuySignals['dates'].append(datesF[-1])
                        msg = "DOLLAR COST AVERAGE signal at {}\n{}".format(DCAbuySignals['prices'][-1], DCAbuySignals['dates'][-1])
                        print(msg)
                        webhook.send(msg)
                            
            elif HOLDING and DCA_VOLUME != 0:
                if bbhigh(bbandsDF, high_dataF) and rsi_cross2(rsiDF, 'sell'):
                    #if current price is above HIGH bband and rsi > 70
                    if DCAbuySignals['prices'][-1] * 1.01 < close_dataF[-1] :
                        #if current price is over 1% above price at DCA
                        
                        #sell signals ... HOLDING must be True and must be after a DCA 
                        '''
                        PLACE MARKET SELL ORDER
                        '''
                        dca_sell = client.place__market_order(pair, "sell", DCA_VOLUME, price=round(close_dataF[-1] * 0.9985, 5))
                        DCAsellSignals['dates'].append(datesF[-1])
                        DCAsellSignals['prices'].append(dca_sell)
                        msg = "DCA Sell signal at {}\n{}".format(DCAsellSignals['prices'][-1], DCAsellSignals['dates'][-1])
                        print(msg)
                        webhook.send(msg)

                        accountValue['value'].append(client.get_cash_balance())
                        accountValue['dates'].append(dt.now())

                        #save profit to graph
                        fig2 = go.Figure()
                        fig2.add_scatter(x= accountValue['dates'], y= accountValue['value'], mode='lines+markers')
                        fig2.write_html(pair+"-Profit-Chart.html")
                        DCA_VOLUME = 0
            else:
                pass

            print('3 seconds sleep')
            print("------------------------------------")
            time.sleep(3)   #sleep for 5 seconds
    except Exception as e:
        print(e)
        webhook.send("ERROR: " + e)
        
if __name__ == "__main__":
    main('ADA', 'USD')
