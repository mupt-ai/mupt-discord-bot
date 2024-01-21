import openai
from openai import OpenAI

async def generate_response(prompt_input):

    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages = prompt_input
    )

    return response.choices[0].message.content
    