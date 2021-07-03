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
    Custom Methods
    '''    
    def place_order(self, pair, orderType, _type, volume , price, leverage=None) -> float:
        #krake_request wrapper 
        #places either buy or sell order @ specified volume with leverage
        # Construct the request and print the result, return the message
        if leverage != None:
            resp = self.kraken_request('/0/private/AddOrder', {
                "nonce": str(int(1000*time.time())),
                "ordertype": orderType,  #  market limit stop-loss take-profit stop-loss-limit take-profit-limit settle-position
                "type": _type, #buy or sell
                "volume": volume,
                "pair": pair,
                "price": price,
                "leverage": leverage
            })
        else:
            resp = self.kraken_request('/0/private/AddOrder', {
                "nonce": str(int(1000*time.time())),
                "ordertype": orderType,  #  market limit stop-loss take-profit stop-loss-limit take-profit-limit settle-position
                "type": _type, #buy or sell
                "volume": volume,
                "pair": pair,
                "price": price
            })
        
        print(resp.json())
        try:
            feed = resp.json()['result']['descr']['order']
            return feed
        except:
            raise Exception(resp.json()['error'])

    def get_cash_balance(self, ticker='ZUSD'):
        #retrive cash balance of account
        resp = self.kraken_request('/0/private/Balance', {
            "nonce": str(int(1000*time.time()))
        })
        if len(resp.json()['error']) != 0:
            raise Exception("Error in APIWrapper.Kraken.get_cash_balance()\n" + resp.json()['error'])
        retVal =float(resp.json()['result'][ticker]) 
        return retVal

    def has_open_positions(self):
        #returns true is there are open positions
        resp = self.kraken_request('/0/private/OpenPositions', {
        "nonce": str(int(1000*time.time())),
        "docalcs": True
        })
        if len(resp.json()['error']) != 0:
            raise Exception("Error in APIWrapper.Kraken.has_open_positions()\n" + resp.json()['error'])
        if len(resp.json()['result']) == 0:
            return False
        return True

    def has_open_orders(self):
        resp = self.kraken_request('/0/private/OpenOrders', {
        "nonce": str(int(1000*time.time())),
        "trades": True
        })
        if len(resp.json()['error']) != 0:
            raise Exception("Error in APIWrapper.Kraken.has_open_orders()\n" + resp.json()['error'])
        if len(resp.json()['result']['open']) == 0:
            return False
        else:
            return True
    
    def get_open_orders(self):
        resp = self.kraken_request('/0/private/OpenOrders', {
        "nonce": str(int(1000*time.time())),
        "trades": True
        })
        if len(resp.json()['error']) != 0:
            raise Exception("Error in APIWrapper.Kraken.get_open_orders()\n" + resp.json()['error'])
        return resp.json()['result']['open']
    
    def cancel_order(self):

        for txid in list(self.get_open_orders()):
            resp = self.kraken_request('/0/private/CancelOrder', {
            "nonce": str(int(1000*time.time())),
            "txid": txid
            })

        if len(resp.json()['error']) != 0:
            raise Exception("Error in APIWrapper.Kraken.cancel_order()\n" + resp.json()['error'])

        return resp.json()['result']

    def get_open_position(self):
        #returns json of the open position
        resp = self.kraken_request('/0/private/OpenPositions', {
        "nonce": str(int(1000*time.time())),
        "docalcs": True
        })
        if len(resp.json()['error']) != 0:
            raise Exception("Error in APIWrapper.Kraken.get_open_position()\n" + resp.json()['error'])

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
