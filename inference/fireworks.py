import requests
import os
import json

fireworks_key = os.environ["FIREWORKS_CLIENT_API_KEY"]
url = "https://api.fireworks.ai/inference/v1/chat/completions"

async def generate_response(prompt_input):
    payload = {
        "messages": prompt_input,
        "temperature": 1,
        "top_p": 1,
        "n": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "stream": False,
        "max_tokens": 1000,
        "stop": None,
        "prompt_truncate_len": 1500,
        "model": "accounts/fireworks/models/mistral-7b-instruct-4k"
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {fireworks_key}"
    }

    response = requests.post(url, json=payload, headers=headers)

    print('\n')
    print(response.text)
    print('\n')

    return json.loads(response.text)