import re
from numpy import minimum, pi
import requests
import urllib.parse
import hashlib
import hmac
import base64
import time

class Kraken:
    def __init__(self, api_key, api_sec):
        #https://docs.kraken.com/rest/#section/General-Usage

        self.api_url = "https://api.kraken.com" 
        self.api_key = api_key
        self.api_sec = api_sec #private key
        
        '''
        MINIMUM ORDER SIZES OF COINS 
        '''
        self.minimun_order_size = {"ZRX": 5,
                                    "AAVE": 0.02,
                                    "GHST": 5,
                                    "ALGO": 5,
                                    "ANKR": 50,
                                    "ANT": 0.5,
                                    "REP": 0.15,
                                    "REPV2": 0.15,
                                    "AXS": 2,
                                    "BAL": 0.15,
                                    "BNT": 1,
                                    "BAT": 5,
                                    "BTC": 0.0001,
                                    "BCH": 0.01,
                                    "ADA": 5,
                                    "LINK": 0.2,
                                    "CHZ": 20,
                                    "COMP": 0.01,
                                    "ATOM": 0.3,
                                    "CQT": 1,
                                    "CRV": 2.5,
                                    "DAI": 5,
                                    "DASH": 0.03,
                                    "MANA": 7,
                                    "DOGE": 50,
                                    "EWT": 0.5,
                                    "ENJ": 2,
                                    "MLN": 0.1,
                                    "EOS": 1,
                                    "ETH": 0.004,
                                    "ETH2.S": 0.004,
                                    "ETC": 0.35,
                                    "FIL": 0.05,
                                    "FLOW": 0.2,
                                    "GNO": 0.05,
                                    "ICX": 3,
                                    "KAVA": 1,
                                    "KEEP": 10,
                                    "KSM": 0.02,
                                    "KNC": 2,
                                    "LSK": 1,
                                    "LTC": 0.03,
                                    "LPT": 0.2,
                                    "MKR": 0.002,
                                    "MINA": 0.2,
                                    "XMR": 0.02,
                                    "NANO": 1.5,
                                    "OCEAN": 5,
                                    "OMG": 0.5,
                                    "OXT": 10,
                                    "OGN": 5,
                                    "PAXG": 0.004,
                                    "PERP": 0.5,
                                    "DOT": 0.2,
                                    "MATIC": 20,
                                    "QTUM": 0.5,
                                    "RARI": 0.3,
                                    "REN": 5,
                                    "XRP": 5,
                                    "SRM": 1,
                                    "SC": 280,
                                    "SOL": 0.2,
                                    "XLM": 10,
                                    "STORJ": 3,
                                    "SUSHI": 0.5,
                                    "SNX": 0.4,
                                    "TBTC": 0.0001,
                                    "USDT": 5,
                                    "XTZ": 1,
                                    "GRT": 3.5,
                                    "SAND": 10,
                                    "TRX": 50,
                                    "UNI": 0.2,
                                    "USDC": 5,
                                    "WAVES": 0.5,
                                    "YFI": 0.00015,
                                    "ZEC": 0.035    
                                }


    '''
    Methods from Kraken Documentation
    '''
    def get_kraken_signature(self, urlpath, data):
        #taken and modified directly from kraken docs
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(base64.b64decode(self.api_sec), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    def kraken_request(self, uri_path, data):
        #taken and modified directly from kraken docs
        headers = {}
        headers['API-Key'] = self.api_key
        # get_kraken_signature() as defined in the 'Authentication' section
        headers['API-Sign'] = self.get_kraken_signature(uri_path, data)             
        req = requests.post((self.api_url + uri_path), headers=headers, data=data)
        return req

    '''
    Custom-Built Methods
    '''    
    def place_order(self, pair, orderType, _type, volume , price=None, leverage=None) -> float:
        #krake_request wrapper 
        #places either buy or sell order @ specified volume with leverage
        # Construct the request and print the result, return the message
       
        data= {
            "nonce": str(int(1000*time.time())),
            "ordertype": orderType,  #  market limit stop-loss take-profit stop-loss-limit take-profit-limit settle-position
            "type": _type, #buy or sell
            "volume": volume,
            "pair": pair,
            "price": price,
            "leverage": leverage
        }
        
        if data['price'] == None:
            data.pop('price')
        if data['leverage'] == None:
            data.pop('leverage')

        resp = self.kraken_request('/0/private/AddOrder', data)
        print(resp.json())

        if len(resp.json()['error']) != 0:
            raise Exception("Error in APIWrapper.Kraken.place_order()\n" + str(resp.json()['error']))
        retVal = resp.json()['result']['descr']['order']
        return retVal

    def get_cash_balance(self, ticker='ZUSD'):
        #retrive cash balance of account
        resp = self.kraken_request('/0/private/Balance', {
            "nonce": str(int(1000*time.time()))
        })
        if len(resp.json()['error']) != 0:
            raise Exception("Error in APIWrapper.Kraken.get_cash_balance()\n" + str(resp.json()['error']))
        retVal =float(resp.json()['result'][ticker]) 
        return retVal

    def get_portfolio_value(self):
        #retrive cash balance of account
        resp = self.kraken_request('/0/private/TradeBalance', {
            "nonce": str(int(1000*time.time())),
            "asset": "USD"
        })
        if len(resp.json()['error']) != 0:
            print(resp.json()['error'])
            raise Exception("Error in APIWrapper.Kraken.get_portfolio_value()\n" + str(resp.json()['error']))
        #print(resp.json()['result'])
        retVal = resp.json()['result']['eb']
        #print(resp.json()['result']['eb'] )
        return float(retVal)

    def get_asset_value(self, asset="ZUSD"):
        #retrive cash balance of account
        resp = self.kraken_request('/0/private/Balance', {
            "nonce": str(int(1000*time.time()))
        })
        if len(resp.json()['error']) != 0:
            print(resp.json()['error'])
            raise Exception("Error in APIWrapper.Kraken.get_asset_value()\n" + str(resp.json()['error']))
        
        if asset in resp.json()['result']:
            retVal = resp.json()['result'][asset]
            return float(retVal)
        elif 'X' + str(asset) in resp.json()['result']:
            retVal = resp.json()['result']['X' + str(asset)]
            return float(retVal)
        
        return 0

    def get_trade_balance(self):
        #retrive cash balance of account
        resp = self.kraken_request('/0/private/TradeBalance', {
            "nonce": str(int(1000*time.time())),
            "asset": "USD"
        })
        if len(resp.json()['error']) != 0:
            print(resp.json()['error'])
            raise Exception("Error in APIWrapper.Kraken.get_trade_balance()\n" + str(resp.json()['error']))
        retVal = resp.json()['result']['tb']
        print(resp.json()['result'])
        return float(retVal)

    def has_open_positions(self):
        #returns true is there are open positions
        resp = self.kraken_request('/0/private/OpenPositions', {
        "nonce": str(int(1000*time.time())),
        "docalcs": True
        })
        if len(resp.json()['error']) != 0:
            raise Exception("Error in APIWrapper.Kraken.has_open_positions()\n" + str(resp.json()['error']))
        if len(resp.json()['result']) == 0:
            return False
        return True

    def has_open_orders(self, pair):
        resp = self.kraken_request('/0/private/OpenOrders', {
        "nonce": str(int(1000*time.time())),
        "trades": True
        })
        if len(resp.json()['error']) != 0:
            raise Exception("Error in APIWrapper.Kraken.has_open_orders()\n" + str(resp.json()['error']))
        if len(resp.json()['result']['open']) == 0:
            return False
        else:
            orders = resp.json()['result']['open']
            for txid in list(orders):
                print(orders[txid]['descr'])
                if orders[txid]['descr']["pair"] == pair:
                    return True
                else:
                    return False
    
    def get_open_orders(self):
        resp = self.kraken_request('/0/private/OpenOrders', {
        "nonce": str(int(1000*time.time())),
        "trades": True
        })
        if len(resp.json()['error']) != 0:
            raise Exception("Error in APIWrapper.Kraken.get_open_orders()\n" + str(resp.json()['error']))
        return resp.json()['result']['open']
    
    def cancel_order(self, pair):
        if self.has_open_orders(pair):
            
            resp = ''
            open_orders = self.get_open_orders()
            for txid in list(open_orders):
                if open_orders[txid]['descr']["pair"] == pair:
                    resp = self.kraken_request('/0/private/CancelOrder', {
                    "nonce": str(int(1000*time.time())),
                    "txid": txid
                    })

                    if len(resp.json()['error']) != 0:
                        raise Exception("Error in APIWrapper.Kraken.cancel_order()\n" + str(resp.json()['error']))
            
            return [True, resp.json()['result']]
        return [False]
            
    def get_open_position(self):
        #returns json of the open position
        resp = self.kraken_request('/0/private/OpenPositions', {
        "nonce": str(int(1000*time.time())),
        "docalcs": True
        })
        if len(resp.json()['error']) != 0:
            raise Exception("Error in APIWrapper.Kraken.get_open_position()\n" + str(resp.json()['error']))

        return resp.json()['result']

    def close_open_position(self,price, _type_):
        #closes all open positions 
        #only to be used if all open positions are on the same asset base pair
        #if there are more than one, for loop gets the total volume to close them all thru one order
        if self.has_open_positions():
            openPos = self.get_open_position()
            openPos1 = openPos[list(openPos)[0]]
            vol = 0
            for i in range(len(list(openPos))):
                vol += float( openPos[list(openPos)[i]]['vol'] )

            retVal = self.place_order(pair= openPos1['pair'],
                            orderType= openPos1['ordertype'],
                            _type= _type_,
                            volume= vol,
                            price= price
                            #leverage= int(round(float(openPos1['cost']) / float(openPos1['margin']), 0))
                            )
            return retVal
    
    def ensure_filled_order(self, pair, _type, volume, price):
        while self.has_open_orders(pair):
            self.cancel_order(pair)
            time.sleep(5)
            self.place_order(pair,
                            'limit',
                            _type,
                            volume,
                            price
                            )
            time.sleep(10)

    def valid_volume(self, volume, base):

        if volume < self.minimun_order_size[base]:
            return self.minimun_order_size[base]
        else:
            return volume

