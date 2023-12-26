import requests
import yaml

TOKEN = "MTE4ODcxNTY3NjIxMTM1MTYwMg.GB-B9f.aMYBmQA7X870YdC3ZihzvNkfe9iWHZ0kFVI5MI" 
APPLICATION_ID = "1188715676211351602"
URL = f"https://discord.com/api/v9/applications/{APPLICATION_ID}/commands"

with open("discord_commands.yaml", "r") as file:
    yaml_content = file.read()

commands = yaml.safe_load(yaml_content)
headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}

# Send the POST request for each command
for command in commands:
    response = requests.post(URL, json=command, headers=headers)
    command_name = command["name"]
    print(f"Command {command_name} created: {response.status_code}")
