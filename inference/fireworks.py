import os
import fireworks
import fireworks.client


fireworks.client.api_key = os.environ["FIREWORKS_CLIENT_API_KEY"]

async def generate_response(prompt: str):
    context_message = ""
    response_generator = fireworks.client.ChatCompletion.create(
        model="accounts/fireworks/models/mistral-7b-instruct-4k",
        messages=[
            {
            "role": "user",
            "content": prompt,
            }
        ],
        stream=True,
        n=1,
        max_tokens=1000,
        temperature=0.1,
        top_p=0.9, 
        stop=[],
    )
    
    response = ""

    for chunk in response_generator:
        if chunk.choices[0].delta.content is not None:
            response += chunk.choices[0].delta.content
    
    return response