import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the src root directory (two levels up)
src_root = os.path.dirname(os.path.dirname(current_dir))
# Now can import bot.py using the absolute path
sys.path.append(src_root)

from bot import MuptBot  # Import the MuptBot class from bot.py

# Load environment variables
load_dotenv()

# OpenAI API key setup
client = OpenAI(
  api_key=os.environ.get("MUPT_OPENAI_API_KEY"),
)

###########################
# BOT-SPECIFIC PARAMETERS #
###########################

token = os.environ["MUPT_BOT_TOKEN"]
context_length = os.environ["GENERAL_CONTEXT_LENGTH"]
prompt = ""

###########################

# Bot setup and run
bot = MuptBot(token, context_length, prompt, False)
bot.run()