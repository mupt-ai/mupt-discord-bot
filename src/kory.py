from bot import MuptBot
import os

token = os.environ["KORY_BOT_TOKEN"]
key = os.environ["FIREWORKS_CLIENT_API_KEY"]
bot = MuptBot(token, key)
bot.run()