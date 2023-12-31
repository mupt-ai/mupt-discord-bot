'''bot.py

    Base code for mupt-bot.
'''

import os, re, asyncio
from dataclasses import dataclass
from collections import defaultdict 
from dotenv import load_dotenv

from sqlalchemy     import Column, Integer, String, DateTime, ForeignKey, MetaData, select

import discord
from discord.ext    import commands, tasks
from discord        import app_commands
from discord.utils  import get

# Env setup
load_dotenv()

from sql.models import *
from sql.utility import *
import inference.fireworks

######################################################

##################
# INITIALIZATION #
##################

# SQL setup
engine, session = setup(True)
# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

class MuptBot:
    def __init__(self, token): 
        global bot_token
        bot_token = token
    def run(self):
        global bot_token
        bot.run(bot_token)

######################################################

##################
# SLASH COMMANDS #
##################

# Use /prompt to test prompt - no context
@bot.tree.command(name = "prompt", description = "Test prompting.")
async def prompt(interaction: discord.Interaction, input: str):
    result = [
        {
            "role": "user",
            "content": input 
        },
    ]
    response = (await inference.fireworks.generate_response(result))["choices"][0]["message"]["content"]
    await interaction.response.send_message(response)

# Manually register server to database
@bot.tree.command(name = "register_server_with_bot", description = "Register server with bot.")
async def register_server_with_bot(interaction: discord.Interaction):
    if register_server(session, interaction.guild):
        await interaction.response.send_message("Successfully registered server.")
    else:
        await interaction.response.send_message("Server is already registered.")

##############
# BOT EVENTS #
##############

# Start up
@bot.event
async def on_ready():
    # Make sure that bot is registered
    register_bot(session, bot.user)
    print(f"{bot.user.name} is online.")
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} command(s)")

@bot.event
async def on_guild_join(guild):
    # Register server to database
    register_server(session, guild)
    system_channel = guild.system_channel
    await system_channel.send(f"{bot.user.name} has been added to the server!")

@bot.event
async def on_member_update(before, after):
    if before.id == bot.user.id:
        register_bot(session, bot.user)
        print("Updated bot entry")

@bot.event
async def on_guild_update(before, after):
    register_server(session, after)
    print("Updated server entry")

# Respond to ping - for now, have all messages be facilitated through pings
@bot.event
async def on_message(message):
    # Ignore if self or server-ping
    if message.author == bot.user:
        return
    if bot.user.mention in message.content:
        guild = message.guild 
        author = message.author
        # Make sure that server is registered
        register_server(session, guild)
        # Ensure that user is registered
        register_user(session, author)
        # Process user message 
        new_sentence = (await process_mention(message)).replace(bot.user.name,"",1)
        # Store received message in ConversationLine
        add_message(session, bot.user, guild, author, new_sentence)
        # Generate prompt
        prompt_input = await get_prompt_with_context(message.guild, 10, author, new_sentence)
        print("\n")
        print(prompt_input)
        print("\n")
        # Generate, send, and store response
        response = (await inference.fireworks.generate_response(prompt_input))["choices"][0]["message"]["content"]
        print(response)
        print("\n")
        await message.channel.send(response)
        add_message(session, bot.user, guild, bot.user, response)
    # Process other commands if needed
    # await bot.process_commands(message)

################
# BOT COMMANDS #
################

# @bot.command()
# async def create_channel(ctx):
#     guild = ctx.guild
#     member = ctx.author
#     # admin_role = get(guild.roles, name="Admin")
#     overwrites = {
#         guild.default_role: discord.PermissionOverwrite(read_messages=False),
#         member: discord.PermissionOverwrite(read_messages=True),
#         # admin_role: discord.PermissionOverwrite(read_messages=True)
#     }
#     channel = await guild.create_text_channel('secret', overwrites=overwrites)
#     await channel.send(f"Hello")

####################
# HELPER FUNCTIONS # 
####################

# Context prefix for generating responses
# Note:
#   - Has to alternate between user and assistant messages
#   - First message in log has to be from user
async def get_prompt_with_context(guild, context_length, author, prompt_input):
    history = (
        session.query(ConversationLine)
        .filter_by(bot=bot.user.id, server=guild.id)
        .order_by(ConversationLine.timestamp.desc())
        .limit(context_length)
        .all()
    )

    history = [(line.sender, line.message) for line in history]
    result = []
    result.append(
        {
            "role": "system",
            "content": f"You are chatting in a Discord server with several Discord members. Your name is {bot.user.name}. The Discord members' messages are given to you as user messages, and the first set of brackets at the start of each user message contains the username of the Discord user that had sent that message in the Discord channel. THIS IS VERY IMPORTANT!!! You should also keep track of which Discord users are in the conversation at all times. When responding, you should NEVER format anyone's usernames: for instance, instead of formatting usernames as [username], format it as username instead. If you do not follow these instructions well, you will NOT receive a reward of cookies."
        },
    )
    prevUser = False
    for index, (id, message) in enumerate(reversed(history)):
        if id == bot.user.id:
            if index == 0:
                continue
            if not prevUser:
                result.append(
                    {
                        "role": "user",
                        "content": ""
                    }
                ) 
            result.append(
                {
                    "role": "assistant",
                    "content": message
                },
            )
            prevUser = False
        else:
            username = await get_member_handle(guild, id)
            if prevUser:
                result.append(
                    {
                        "role": "assistant",
                        "content": ""
                    }
                )
            result.append(
                {
                    "role": "user",
                    "content": f"[{username}] " + message
                },
            )
            prevUser = True

    return result

# Convert mentions (User: '<@ID>', Role: '<@&ID>') to output text
async def process_mention(message):
    new_sentence = message.content
    # regular user, then role
    id_patterns = [(re.compile(r'<@(\d+)>'), True), (re.compile(r'<@&(\d+)>'), False)]
    for (id_pattern, isUser) in iter(id_patterns):
        # Find all matches in parallel
        matches = list(id_pattern.finditer(new_sentence))
        replacements = [replace_user_ids(match, message, isUser) for match in matches]
        # Replace in the sentence
        for match, replacement in zip(matches, await asyncio.gather(*replacements)):
            new_sentence = new_sentence.replace(match.group(0), replacement, 1) 
    return new_sentence

# Replace user IDs with corresponding usernames
async def replace_user_ids(match, message, isUser = True):
    numeric_id = match.group(1)
    id = int(numeric_id)
    guild = message.guild

    if isUser:
        return await get_member_handle(guild, id)
    else:
        role = guild.get_role(id)
        return role.name

# Get nickname of member (server), member username otherwise
async def get_member_handle(guild, member_id):
    member = await guild.fetch_member(member_id)
    if member.nick:
        return member.nick
    return member.name

######################################################
