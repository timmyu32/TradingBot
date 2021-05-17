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
    HELPER AND WRAPPER METHODS
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
    USEFUL CLIENT->SERVER METHODS
    '''
    
    def place__market_order(self, orderType, volume):
        #krake_request wrapper 
        #places either marker buy or sell order @ specified volume

        # Construct the request and print the result
        resp = self.kraken_request('/0/private/AddOrder', {
            "nonce": str(int(1000*time.time())),
            "ordertype": "market",
            "type": orderType,
            "volume": volume,
            "pair": "ADAUSD"
        })
        try:
            print(resp.json()['result']['descr']['order'])
        except Exception as e:
            print(e)


    def get_cash_balance(self, ticker='ZUSD'):
        #retrive cash balance of account

        resp = self.kraken_request('/0/private/Balance', {
            "nonce": str(int(1000*time.time()))
        })

        #print(resp.json())
        retVal =float(resp.json()['result'][ticker]) 

        return retVal