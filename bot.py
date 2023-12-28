'''bot.py

    Base code for mupt-bot.
'''

import os, re, asyncio
from dataclasses import dataclass
from collections import defaultdict 

from sqlalchemy     import Column, Integer, String, DateTime, ForeignKey, MetaData

import discord
from discord.ext    import commands, tasks
from discord        import app_commands
from discord.utils  import get

from sql.models import *
from sql.utility import *
import inference.fireworks

######################################################

# Bot Token
BOT_TOKEN = "MTE4ODcxNTY3NjIxMTM1MTYwMg.GB-B9f.aMYBmQA7X870YdC3ZihzvNkfe9iWHZ0kFVI5MI"

######################################################

##################
# INITIALIZATION #
##################

# SQL setup
engine, session = setup(True)

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

######################################################

##################
# SLASH COMMANDS #
##################

# Use /prompt to test prompt - untracked
@bot.tree.command(name = "prompt", description = "Test prompting.")
async def prompt(interaction: discord.Interaction, input: str):
    response = await inference.fireworks.generate_response(input)
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
        # Make sure that server is registered
        register_server(session, message.guild)
        # Ensure that user is registered
        register_user(session, message.author)
        # Send response
        new_sentence = await process_mention(message)
        # Store message in ConversationLine
        add_message(session, bot.user, message.guild, message.author, new_sentence)
        # Generate and store response
        response = await inference.fireworks.generate_response(new_sentence)
        await message.channel.send(response)
        add_message(session, bot.user, message.guild, bot.user, response)
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

# Get nickname of member, member username otherwise
def get_member_nickname(member: discord.member.Member):
    nick = member.nick
    if not nick:
        return member.name
    return nick

######################################################

# Run the bot
bot.run(BOT_TOKEN)

######################################################
