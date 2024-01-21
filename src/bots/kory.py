import os
import sys

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the src root directory (one level up)
src_root = os.path.dirname(current_dir)
# Now can import bot.py using the absolute path
sys.path.append(src_root)

from bot import MuptBot

token = os.environ["KORY_BOT_TOKEN"]
key = os.environ["FIREWORKS_CLIENT_API_KEY"]
bot = MuptBot(token, key)
bot.run()