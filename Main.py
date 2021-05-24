from pandas_ta.momentum.rsi import rsi
import OOPBT
import APIWrapper
#^not sure why VSCode doesn't like this
from datetime import datetime as dt
from datetime import timedelta as td
import pandas as pd
import numpy as np
import pandas_ta as ta
import time

import plotly.graph_objects as go

from twilio.rest import Client


KRAKEN_API_KEY = 'vyjca5FUjXUvnvpqS6Iezyw+ZBSXf1UPToVRjCGjoF7RqoJal7WtvtQD'
KRAKEN_PRIVATE_KEY = 'tUXJOW3qQTWFZ6cVEfsWbkIjUf3sN8NDc0TT0hqgi5G6taJRkdkK6f9DIQsFLyJaYmnWVIp/pR+QoImXT2kY+w=='

SHRIMPY_API_KEY = '3a4300561ac89b86c65ee1e08ebc8902883f4125731bcbf130e892508dc5d207'
SHRIMPY_PRIVATE_KEY = 'e5b516c157eca763f6d6131d8fb019d57ad3fc54fd6a421607bf686924b028fe466349f698d5bc6feaeb4f37d42b5fbd005b78ee730b505d3a4c1672af431a08'

TWILIO_SID = 'AC75f515664ec0cf34898d40c656e1eaf8'
TWILIO_TOKEN = 'f5f2d66cb157d1696d4e43715811384d'

VOLUME = 0

#buy and sell signals dictionary
buySignals = {'dates':[],
            'prices': []  
            }

sellSignals = {'dates':[],
            'prices': []  
            }

accountValue = {'dates':[],
                'value':[]
            }

def bblow(bbdf, cdf):
    retval = False
    for i in range(1,6):
        if bbdf['BBL_20_2.0'].iloc[-1 * i]  >= cdf[-1 * i]:
            print('PRICE DIPPED BELOW LOW BBAND WITHIN LATEST 5 CANDLES')
            print(i)
            print("Low Band= ",round(bbdf['BBL_20_2.0'].iloc[-1 * i], 5), "Candle  Low = ", cdf[-1 * i])
            return True
    return retval

def bbhigh(bbdf, cdf):
    retval = False
    for i in range(1,6):
        if bbdf['BBU_20_2.0'].iloc[-1 * i]  <= cdf[-1 * i]:
            print('PRICE GOT ABOVE HIGH BBAND WITHIN LATEST 5 CANDLES')
            print(i)
            print("High Band= ",round(bbdf['BBU_20_2.0'].iloc[-1 * i], 5) , "Candle High = ", cdf[-1 * i])

            return True
    return retval
holding = False
def rsi_cross(rsidf):
    retval = False
    print('rsi_cross = ', rsidf.iloc[-1])
    if not holding:
        if rsidf.iloc[-1] >= 30:
            if rsidf.iloc[-2] < 30:
                retval = True
    else:
        if rsidf.iloc[-1] >= 70:
                retval = True
    print(retval)
    return retval



client = APIWrapper.Kraken(KRAKEN_API_KEY, KRAKEN_PRIVATE_KEY)
text_client = Client(TWILIO_SID, TWILIO_TOKEN)
accountValue['value'].append(client.get_cash_balance())
accountValue['dates'].append(dt.now())


if __name__ == "__main__":
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
                'ADA',
                'USD',
                '1m',
                startTime=start
                )
        
        #write last 150 candles to a CSV
        #consider taking this out? Not sure if this needs to be saved to an external file
        #probably more efficient to have backtestCSV as a dataframe 
        backTestCSV.write_candle_data()

        df = pd.read_csv('{}{}Data.csv'.format("ADA", "USD"))
        print("CURRENT CANDLE DATA\n{}\n".format(df.iloc[-1]))
        
        datesF = np.array(df['Dates'])
        high_dataF = np.array(df['High Data'])
        low_dataF = np.array(df['Low Data'])
        close_dataF = np.array(df['Close Data'])
        print('CURRENT PRICE = {}\n'.format(close_dataF[-1]))
        open_dataF = np.array(df['Open Data'])

        #create bollinger bands dataframe
        bbandsDF = ta.bbands(close=df['Close Data'], length=20, std=2.0)
        #create SMA (100 and 20)
        sma50DF = ta.sma(close=df['Close Data'], length=20)
        sma200DF = ta.sma(close=df['Close Data'], length=100)
        #macd---not being used in current algo, could be used to look for 
        #buys when not im GOLDEN CROSS, need further testing
        macdDF = ta.macd(close=df['Close Data'])
        #rsi
        rsiDF = ta.rsi(close=df['Close Data'])
        

        
        print("INDICATOR DATA")
        print("SMA20         {}".format(round(sma50DF.iloc[-1], 4)))
        print("Upper BBand   {}".format(round( bbandsDF['BBU_20_2.0'].iloc[-1], 4)))
        print("Lower BBand   {}".format(round( bbandsDF['BBL_20_2.0'].iloc[-1], 4)))
        print("RSI          {}\n".format(round( rsiDF.iloc[-1], 4)))

        if low_dataF[-1] <= bbandsDF['BBL_20_2.0'].iloc[-1]:
            print("Lowt price below lower band\n")
        elif high_dataF[-1] >= bbandsDF['BBU_20_2.0'].iloc[-1]:
            print("High price above upper band\n")
        else:
            print("Current price within bands\n")


       
        
        #Strategey Rules
        #must be in a GOLDEN CROSS 50 SMA OVER 200 SMA
        #must be not holding to buy
        #must be holding to sell

        accountSize = client.get_cash_balance() #account size from Kraken API
        riskRate = 0.75


        #if sma50DF.iloc[-1] > sma200DF.iloc[-1]:
        #print("In GOLDEN CROSS")
        if bblow(bbandsDF, low_dataF):
            if rsi_cross(rsiDF):
                #if current price is below LOW bband
                #buy signals ... holding must be False
                if not holding:
                    buySignals['dates'].append(datesF[-1])
                    buySignals['prices'].append(close_dataF[-1])
                    holding = True
                    print("Buy signal at {}\n{}".format(buySignals['prices'][-1], buySignals['dates'][-1]))
                    '''
                    PLACE MARKET BUY ORDER
                    '''
                    VOLUME = round(accountSize * riskRate / close_dataF[-1], 5)
                    sms = client.place__market_order("buy", VOLUME)
                    text_client.messages.create(to="+15086638436", from_="+15107564670", 
                        body=sms)

        elif holding and buySignals['prices'][-1] < close_dataF[-1]:
            #if you are holding and price of position is below clandle close     
            if bbhigh(bbandsDF, high_dataF) and rsi_cross(rsiDF):
                #if current price is above HIGH bband
                #sell signals ... holding must be True
                sellSignals['dates'].append(datesF[-1])
                sellSignals['prices'].append(close_dataF[-1])
                holding = False
                print("Sell signal at {}\n{}".format(sellSignals['prices'][-1], sellSignals['dates'][-1]))
                '''
                PLACE MARKET SELL ORDER
                '''
                sms = client.place__market_order("sell", VOLUME)
                text_client.messages.create(to="+15086638436", from_="+15107564670", 
                    body=sms)
                accountValue['value'].append(client.get_cash_balance())
                accountValue['dates'].append(dt.now())

                #save profit to graph
                fig2 = go.Figure()
                fig2.add_scatter(x= accountValue['dates'], y= accountValue['value'], mode='lines+markers')
                fig2.write_html("ADAUSD-Profit-Chart.html")

            else:
                pass   
        else:
            pass
            #print("No signal at candle...")
            #print(df.iloc[-1])                       

        #else:
        #    print("Not in golden cross\n")
        #    pass
        print('5 seconds sleep')
        print("------------------------------------")
        time.sleep(5)
        #sleep for 5 seconds
