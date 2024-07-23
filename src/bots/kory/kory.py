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

from bots.kory.kory_character_prompt import compile_base_prompt 

from training_material.context import character_context 
from training_material.sample_sentences import selected_sentence_samples

token = os.environ["KORY_BOT_TOKEN"]
context_length = os.environ["GENERAL_CONTEXT_LENGTH"]
prompt = compile_base_prompt(character_context, selected_sentence_samples)

###########################

# Bot setup and run
bot = MuptBot(token, context_length, prompt)
bot.run()