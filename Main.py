import Runner

KRAKEN_API_KEY = ###
KRAKEN_PRIVATE_KEY = ###

SHRIMPY_API_KEY = ###
SHRIMPY_PRIVATE_KEY = ###

WEBHOOK_URL = "https://discord.com/api/webhooks/####'
if __name__ == "__main__":
    CryptoBot = Runner.BotRunner(#base,
                                #quote,
                                KRAKEN_API_KEY,
                                KRAKEN_PRIVATE_KEY,
                                SHRIMPY_API_KEY,
                                SHRIMPY_PRIVATE_KEY,
                                WEBHOOK_URL,
                                )

    CryptoBot.run()


        
