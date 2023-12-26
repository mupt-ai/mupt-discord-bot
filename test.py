import fireworks.client

fireworks.client.api_key = "cXt9k0GwjRCbtiAwvt40T3wvCnOEFI7MBY0mbvxhnJoA1d8c"

response_generator = fireworks.client.ChatCompletion.create(
  model="accounts/fireworks/models/mistral-7b-instruct-4k",
  messages=[
    {
      "role": "user",
      "content": "hello",
    }
  ],
  stream=True,
  n=1,
  max_tokens=150,
  temperature=0.1,
  top_p=0.9, 
  stop=[],
)

response = ""

for chunk in response_generator:
    if chunk.choices[0].delta.content is not None:
        response += chunk.choices[0].delta.content

print(response)
