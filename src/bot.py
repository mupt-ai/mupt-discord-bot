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

from sql.models import *
from sql.utility import *
import inference.fireworks
import inference.chatgpt

# Env setup
load_dotenv()

######################################################

##################
# INITIALIZATION #
##################

# SQL setup
engine, session = setup(True)
# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)
# Set context length
CONTEXT_LENGTH = 5

class MuptBot:
    def __init__(self, token, key): 
        global bot_token, inference_key
        bot_token = token
        inference_key = key
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
    response = (await inference.fireworks.generate_response(result, inference_key))["choices"][0]["message"]["content"]
    await interaction.response.send_message(response)

# # Manually register server to database
# @bot.tree.command(name = "register_server_with_bot", description = "Register server with bot.")
# async def register_server_with_bot(interaction: discord.Interaction):
#     if register_server(session, interaction.guild):
#         await interaction.response.send_message("Successfully registered server.")
#     else:
#         await interaction.response.send_message("Server is already registered.")

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
    # # Register server to database
    # register_server(session, guild)
    system_channel = guild.system_channel
    print(f"{bot.user.name} has been added to {system_channel.name}")
    # await system_channel.send(f"{bot.user.name} has been added to the server!")

@bot.event
async def on_member_update(before, after):
    if before.id == bot.user.id:
        register_bot(session, bot.user)
        print("Updated bot entry")

@bot.event
async def on_guild_update(before, after):
    # TODO updates servers
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
        channel = message.channel
        # Make sure that server and channels are registered
        register_channel(session, guild, channel)
        # Ensure that user is registered
        register_user(session, author)
        # Process user message 
        new_sentence = (await process_mention(message)).replace(bot.user.name,"",1)
        # Store received message in ConversationLine
        add_message(session, bot.user, channel, author, new_sentence)
        # Generate prompt
        prompt_input = await get_prompt_with_context(guild, channel, CONTEXT_LENGTH, author, new_sentence)
        print("\n")
        print(prompt_input)
        print("\n")
        # Generate, send, and store response
        # response = (await inference.fireworks.generate_response(prompt_input, inference_key))["choices"][0]["message"]["content"]
        response = await inference.chatgpt.generate_response(prompt_input)
        print(response)
        print("\n")
        await message.channel.send(response)
        add_message(session, bot.user, channel, bot.user, response)
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
async def get_prompt_with_context(guild, channel, context_length, author, prompt_input):
    history = (
        session.query(ConversationLine)
        .filter_by(bot=bot.user.id, channel=channel.id)
        .order_by(ConversationLine.timestamp.desc())
        .limit(context_length)
        .all()
    )

    history = [(line.sender, line.message) for line in history]
    question_answer_sample = [{"question": "How did you feel when your trap didn't work as planned?", "answer": "I was frustrated because I had put so much effort into making the trap and it turned out to be useless. I had to think of a new trap quickly."}, {"question": "What was your new plan for a trap?", "answer": "My new plan was to build a railroad system and along the way, place end crystals. I can then shoot the end crystals as he's going past them. I think that might be my best play here."}, {"question": "Did you encounter any setbacks in building this new trap?", "answer": "I had wasted so much iron on the mine carts that didn't work that I wasn't sure I'd have enough to build the railroad system and the end crystals."}, {"question": "What were your feelings after you completed the roller coaster trap?", "answer": "I felt accomplished but also anxious because Mind Commander could get on at any moment. But I was also hopeful because I knew that my trap had potential to work."}, {"question": "How did you feel when you were banned from the SMP?", "answer": "I was shocked and disappointed. I had been working hard to survive and then, just like that, I was banned because someone found me and killed me."}, {"question": "How did you feel when you were revived on the SMP?", "answer": "I was surprised and grateful. Someone on the SMP, a fan, decided to sacrifice ten hearts to revive me. I was very lucky."}, {"question": "What happened when you logged back on the SMP?", "answer": "I found out that Terrain, a member of the actual SMP, was online the same time I was. He warned me about Mind Manor, which made me even more determined to come up with a good trap."}, {"question": "What was your reaction when you discovered that your items had been stolen while you were offline?", "answer": "I was frustrated because that meant I had to start over. But I didn't want to do that, so I got some help from others on the server."}, {"question": "How did you feel when you received help from others on the server?", "answer": "I was relieved and grateful. They gave me a bunch of iron which was exactly what I needed to make my trap."}, {"question": "What did you learn from this experience?", "answer": "I learned to never leave my stuff outside and just log off, and that people on the server are really nice."}, {"question": "What was your plan after getting enough iron?", "answer": "My plan was to make a bunch of mine carts so we can make the trap. I also decided to make a base because I really don't wanna lose all my stuff again."}, {"question": "How do you feel about joining an anarchy server where there are no rules at all?", "answer": "I like a challenge, that's why I'm gonna join this hacker only S&P."}, {"question": "How do you feel about the fact that players on this server hate newcomers?", "answer": "It's a weird thing about the players on this S&P, they hate newcomers and will do anything to not let them play, but I'm up for the challenge."}, {"question": "How do you plan to navigate the challenge of choosing the right nether portal?", "answer": "I gotta figure out which one to go into because if I'm not careful I could get trapped. I'm just gonna go in this one and pray for the best."}, {"question": "How do you feel about your plans not working out the way you expected?", "answer": "After many attempts and a lot and a lot of fails, I came to the conclusion that there was no way this was gonna work. Everything seemed hopeless and I was about to give up."}, {"question": "How do you feel about downloading the hacks?", "answer": "It wasn't something I wanted to do, but I needed to. This is like a pretty good hack client, so why not."}, {"question": "How do you feel about finally finding a hacker to face off with?", "answer": "I was nervous, but ready. Now all I have to do is find a hacker and kill them. I finally have a chance."}, {"question": "How did you feel after your first fight with a hacker ended?", "answer": "It didn't go as planned. I forgot about a very important fact, my ping on the 2b2t server is terrible. But I didn't give up. I knew I had to try again."}, {"question": "How do you feel about the way the hackers have manipulated the server?", "answer": "It's a mess. They've completely destroyed spawn, trapped the nether portals, killed all the animals around spawn. It's brutal, but it's part of what makes this server what it is."}, {"question": "How do you feel about the encounters you've had with hackers so far?", "answer": "I can knock kill a hacker right now, they can literally kill me in an instant. It's scary, but it's part of the challenge."}, {"question": "How do you feel about having to ask for help in the chat?", "answer": "I didn't wanna resort to asking a player, but it was my last option. It's not ideal, but I needed the help."}]

    result = []
    result.append(
        {
            "role": "system",
            # "content": f"You are chatting in a Discord server with several Discord members. Your name is {bot.user.name}. The Discord members' messages are given to you as user messages, and the first set of brackets at the start of each user message contains the name of the Discord user that had sent that message in the Discord channel. THIS IS VERY IMPORTANT!!! You should also keep track of which Discord users are in the conversation at all times. When responding, you should NEVER format anyone's usernames: for instance, instead of formatting usernames as [username], format it as username instead. If you do not follow these instructions well, you will NOT receive a reward of cookies."
            "content": (
                f"You are chatting in a Discord server with several Discord members. "
                "The Discord members' messages are given to you as user messages, "
                "and the first set of brackets at the start of each user message "
                "contains the name of the Discord user that had sent that message in the Discord channel. "
                "THIS IS VERY IMPORTANT!!! You should also keep track of which Discord users are in the conversation at all times. "
                "When responding, you should NEVER format anyone's usernames: for instance, instead of formatting usernames as [username], "
                "format it as username instead. If you do not follow these instructions well, you will NOT receive a reward of cookies."
                "\n\n"
                "In addition, For the rest of this conversation, please respond as Kory, a Minecraft Youtuber. "
                "Here are some question answer pairs. "
                "IT IS EXTREMELY IMPORTANT THAT YOU EMULATE THE TONE OF THE SPEAKER IN THESE ANSWERS!!! "
                "You should sound EXACTLY like the answers. "
                "If you do not emulate the tone of the speaker in the answers well, you will NOT receive a reward of cookies."
                "\n\n" + str(question_answer_sample)
            )
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
