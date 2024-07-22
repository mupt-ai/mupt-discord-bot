import openai
from openai import OpenAI

async def generate_response(prompt_input):

    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages = prompt_input
    )

    return response.choices[0].message.content
    