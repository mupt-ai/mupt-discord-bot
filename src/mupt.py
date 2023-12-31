from bot import MuptBot
import os

token = os.environ["MUPT_BOT_TOKEN"]
key = os.environ["FIREWORKS_CLIENT_API_KEY"]
mupt_bot = MuptBot(token, key)
mupt_bot.run()