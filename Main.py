import Runner

KRAKEN_API_KEY = 'vyjca5FUjXUvnvpqS6Iezyw+ZBSXf1UPToVRjCGjoF7RqoJal7WtvtQD'
KRAKEN_PRIVATE_KEY = 'tUXJOW3qQTWFZ6cVEfsWbkIjUf3sN8NDc0TT0hqgi5G6taJRkdkK6f9DIQsFLyJaYmnWVIp/pR+QoImXT2kY+w=='

SHRIMPY_API_KEY = '974d5cfba2f2e60c553e29ac6a354b37594763b0a6db3e638553119f7ddfc506'
SHRIMPY_PRIVATE_KEY = '11df961500dfd9f5751c13e6bad12f64786c932e0a2bff216bb2b4c7bb53d625b87f389be9d426e989fbece2b21b1d991c6d3895aa4b256a7e7a1796d103628a'

WEBHOOK_URL = "https://discord.com/api/webhooks/848349527961894983/cMQyhqpHEtGjcRETKtw3yp4OK__4xsL3aEjJfKizjlckU_HCT540SysZLEq1GOWIOVGL"
if __name__ == "__main__":
    CryptoBot = Runner.BotRunner('ADA',
                                'USD',
                                KRAKEN_API_KEY,
                                KRAKEN_PRIVATE_KEY,
                                SHRIMPY_API_KEY,
                                SHRIMPY_PRIVATE_KEY,
                                WEBHOOK_URL,
                                )

    CryptoBot.run()


        
