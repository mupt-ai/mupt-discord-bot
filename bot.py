import datetime
import os
import re
import asyncio
from dataclasses import dataclass

import discord
from discord.ext import commands, tasks
from discord import app_commands

import fireworks.client

# should be stored in environment variable
BOT_TOKEN = "MTE4ODcxNTY3NjIxMTM1MTYwMg.GB-B9f.aMYBmQA7X870YdC3ZihzvNkfe9iWHZ0kFVI5MI"
# channel that bot should hop into
CHANNEL_ID = 1188808620704546906
# server / guild of particular interest - not necessarily used
SERVER_ID = 1188610711434317934

fireworks.client.api_key = "cXt9k0GwjRCbtiAwvt40T3wvCnOEFI7MBY0mbvxhnJoA1d8c"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print("CChatBot is online.")
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} command(s)")

    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("CChatBot is online.")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mention in message.content:
        new_sentence = message.content
        # regular user, then role
        user_id_patterns = [(re.compile(r'<@(\d+)>'), True), (re.compile(r'<@&(\d+)>'), False)]

        for (user_id_pattern, isUser) in iter(user_id_patterns):
            # Find all matches in parallel
            matches = list(user_id_pattern.finditer(new_sentence))

            replacements = [replace_user_ids(match, message, isUser) for match in matches]

            # Replace in the sentence
            for match, replacement in zip(matches, await asyncio.gather(*replacements)):
                new_sentence = new_sentence.replace(match.group(0), replacement, 1)
        
        response = await generate_response_fireworks(new_sentence)
        await message.channel.send(response)

    # Process other commands if needed
    await bot.process_commands(message)

# Function to replace user IDs with corresponding usernames
async def replace_user_ids(match, message, isUser = True):
    print(match)
    numeric_id = match.group(1)
    print(numeric_id)
    user_id = int(numeric_id)
    print(user_id)

    if message.guild:
        guild_id = message.guild.id
        guild = bot.get_guild(guild_id)

        if isUser:
            member = await guild.fetch_member(user_id)
            nickname = member.nick
        else:
            role = discord.utils.get(guild.roles, id=user_id)
            return role.name

    if nickname:
        return nickname
    else:
        user = await bot.fetch_user(user_id)
        return user.name

@bot.tree.command(name = "prompt", description = "bazinga")
async def prompt(interaction: discord.Interaction, input: str):
    response = await generate_response_fireworks(input)
    await interaction.response.send_message(response)

async def generate_response_fireworks(prompt: str):
    print(prompt)
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
        max_tokens=150,
        temperature=0.1,
        top_p=0.9, 
        stop=[],
    )
    
    response = ""

    for chunk in response_generator:
        if chunk.choices[0].delta.content is not None:
            response += chunk.choices[0].delta.content
    
    return response

######################################################

bot.run(BOT_TOKEN)

######################################################
