class Coin:
    def __init__(self, base):
        self.Volume = 0
        self.DCA_VOLUME = 0
        self.HOLDING = False
        self.buySignals = {'dates':[],
            'prices': []  
            }
        
        self.sellSignals = {'dates':[],
            'prices': []  
            }

        self.DCAbuySignals = {'dates':[],
            'prices': []  
            }

        self.DCAsellSignals = {'dates':[],
            'prices': []  
            }
        
        