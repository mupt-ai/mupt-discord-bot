'''bot.py

    Base code for mupt-bot.
'''

import os
import re
import asyncio
from dataclasses import dataclass
from collections import defaultdict 

from sqlalchemy     import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

import discord
from discord.ext    import commands, tasks
from discord        import app_commands
from discord.utils  import get

from sql.utility    import *
from inference.fireworks    import *

######################################################

# Bot Token and Temporary IDs
BOT_TOKEN = "MTE4ODcxNTY3NjIxMTM1MTYwMg.GB-B9f.aMYBmQA7X870YdC3ZihzvNkfe9iWHZ0kFVI5MI"
CHANNEL_ID = 1188808620704546906
GUILD_ID = 1188610711434317934

######################################################

# SQL setup
Base = declarative_base()
engine = connect_with_connector()
sql_session = sessionmaker(bind=engine)

# Create tables
Base.metadata.create_all(engine)

######################################################

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

######################################################

##################
# Slash commands #
##################

@bot.tree.command(name = "prompt", description = "bazinga")
async def prompt(interaction: discord.Interaction, input: str):
    response = await generate_response_fireworks(input)
    await interaction.response.send_message(response)

######################################################

# Start up
@bot.event
async def on_ready():
    print("CChatBot is online.")
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} command(s)")
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send("Mupt-bot is online.")

# Response to ping
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if bot.user.mention in message.content:
        new_sentence = await process_mention(message)
        response = await generate_response_fireworks(new_sentence)
        print(new_sentence)
        await message.channel.send(response)
    # Process other commands if needed
    await bot.process_commands(message)

# Convert mentions (User: '<@ID>', Role: '<@&ID>') to output text
async def process_mention(message):
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
    return new_sentence

# Replace user IDs with corresponding usernames
async def replace_user_ids(match, message, isUser = True):
    # print(match)
    numeric_id = match.group(1)
    # print(numeric_id)
    user_id = int(numeric_id)
    # print(user_id)
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

@bot.command()
async def create_channel(ctx):
    guild = ctx.guild
    member = ctx.author
    # admin_role = get(guild.roles, name="Admin")
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True),
        # admin_role: discord.PermissionOverwrite(read_messages=True)
    }
    channel = await guild.create_text_channel('secret', overwrites=overwrites)
    await channel.send(f"Hello")


######################################################

bot.run(BOT_TOKEN)

######################################################
