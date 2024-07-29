import openai
from openai import OpenAI
import os

async def generate_response(prompt_input, max_tokens=None):

    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages = prompt_input,
        max_tokens = int(os.environ["GENERAL_MAX_RESPONSE_TOKENS"])
    )

    if max_tokens is not None:
        response["max_tokens"] = max_tokens

    return response.choices[0].message.content
    