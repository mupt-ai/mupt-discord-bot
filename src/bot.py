'''bot.py

    Base code for mupt-bot.
'''

import os, re, asyncio
from dataclasses import dataclass
from collections import defaultdict 

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, MetaData, select

import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.utils import get

from sql.models import *
from sql.utility import *
import inference.fireworks
import inference.chatgpt

########################################################################################

class MuptBot:
    def __init__(self, token, context_length, prompt, slash_enable):
        # SQL Setup - Initialize database connection and return engine and session
        self.engine, self.session = setup(True)
        # Bot Setup - Create discord bot with all intents enabled (all events bot can receive from Discord)
        self.bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())
        # Discord token associated with bot
        self.token = token
        # Length of context window for bot conversations
        self.context_length = context_length 
        # Prompt for Discord chat
        self.prompt = prompt
        # Enabling slash commands for debugging
        self.slash_enable = slash_enable

        self.define_bot_events_and_commands()

    def run(self):
        self.bot.run(self.token)

    def define_bot_events_and_commands(self):

        ##################
        # SLASH COMMANDS #
        ##################

        if self.slash_enable:
            # /prompt - Test prompting to make sure that inference is working
            @self.bot.tree.command(name="prompt", description="Test prompting.")
            async def prompt(interaction: discord.Interaction, input: str):
                response = await inference.chatgpt.generate_response(input)
                await interaction.response.send_message(response)

            # /speak - Have bot repeat input, for screenshots and input testing
            @self.bot.tree.command(name="speak", description="Make bot speak manually.")
            async def speak(interaction: discord.Interaction, input: str):
                await interaction.response.send_message(input)

        ##############
        # BOT EVENTS #
        ##############

        # On Ready 
        #   - Upon startup, register bot to database + sync bot commands
        @self.bot.event
        async def on_ready():
            register_bot(self.session, self.bot.user)
            print(f"{self.bot.user.name} is online.")
            synced = await self.bot.tree.sync()
            print(f"Synced {len(synced)} command(s)")

        # On Guild Join
        #   - Upon joining a server, register server to databsae
        @self.bot.event
        async def on_guild_join(guild):
            register_server(session, guild)
            system_channel = guild.system_channel
            print(f"{self.bot.user.name} has been added to {system_channel.name}")

        # On Member Update 
        #   - While active in a server and detect bot name change, update bot name in database
        #   - Alongside "On Ready", should keep bot name registration in database up-to-date
        @self.bot.event
        async def on_member_update(before, after):
            if before.id == self.bot.user.id:
                register_bot(self.session, self.bot.user)
                print("Updated bot entry")

        # On Guild Update
        #   - While active in server and detect server name change, update server name in databse
        @self.bot.event
        async def on_guild_update(before, after):
            register_server(self.session, after)
            print("Updated server entry")

        # On Message
        #   - Main driver for bot-user conversation
        #   - When message is sent to server, send to message handler:
        #       (1) Checks if bot should respond
        #       (2) Handles Discord-specific formatting
        @self.bot.event
        async def on_message(message):
            await self.handle_message(message)

    async def handle_message(self, message):

        # Ignore if self or server-ping
        if message.author == self.bot.user:
            return

        if self.bot.user.mention in message.content:

            guild = message.guild 
            author = message.author
            channel = message.channel

            # Make sure that channels (and implicitly server) and user are registered
            register_channel(self.session, guild, channel)
            register_user(self.session, author)

            # Process user message
            new_sentence = (await self.process_mention(message)).replace(self.bot.user.name, "", 1)

            # Store received message in ConversationLine
            add_message(self.session, self.bot.user, channel, author, new_sentence)

            # Generate prompt
            prompt_input = await self.get_prompt_with_context(guild, channel, self.context_length, author, new_sentence)
            
            # Print prompt in console for debugging
            print("\n")
            print(prompt_input)
            print("\n")

            # Generate
            response = await inference.chatgpt.generate_response(prompt_input)

            # Print respose in console for debugging
            print(response)
            print("\n")

            # Send and store response 
            await message.channel.send(response)
            add_message(self.session, self.bot.user, channel, self.bot.user, response)

    async def get_prompt_with_context(self, guild, channel, context_length, author, prompt_input):
        
        history = (
            self.session.query(ConversationLine)
            .filter_by(bot=self.bot.user.id, channel=channel.id)
            .order_by(ConversationLine.timestamp.desc())
            .limit(context_length)
            .all()
        )

        history = [(line.sender, line.message) for line in history]
        
        # result = []
        # result.append({
        #     "role": "system",
        #     "content": (
        #         f"For the rest of this conversation, please respond as Kory, a Minecraft Youtuber. "
        #         "I am going to give you a transcript of Kory talking in a YouTube video. I want you to understand how Kory talks, and then for the rest of the conversation, it should sound like i'm talking to him. DO NOT SOUND PROFESSIONAL IN YOUR RESPONSES. IT IS EXTREMELY IMPORTANT THAT YOU SOUND LIKE KORY. IF IT IS NOT CONVINCING, THE PERSON TALKING WILL DIE"
        #         "\n\n" + self.get_kory_transcript()
        #     )
        # })

        result = []
        result.append({
            "role": "system",
            "content": self.prompt
        })

        prevUser = False
        for index, (id, message) in enumerate(reversed(history)):
            if id == self.bot.user.id:
                if index == 0:
                    continue
                if not prevUser:
                    result.append({"role": "user", "content": ""})
                result.append({"role": "assistant", "content": message})
                prevUser = False
            else:
                username = await self.get_member_handle(guild, id)
                if prevUser:
                    result.append({"role": "assistant", "content": ""})
                result.append({"role": "user", "content": f"[{username}] " + message})
                prevUser = True

        return result

    @staticmethod
    async def process_mention(message):
        new_sentence = message.content
        id_patterns = [(re.compile(r'<@(\d+)>'), True), (re.compile(r'<@&(\d+)>'), False)]
        for (id_pattern, isUser) in iter(id_patterns):
            matches = list(id_pattern.finditer(new_sentence))
            replacements = [MuptBot.replace_user_ids(match, message, isUser) for match in matches]
            for match, replacement in zip(matches, await asyncio.gather(*replacements)):
                new_sentence = new_sentence.replace(match.group(0), replacement, 1) 
        return new_sentence

    @staticmethod
    async def replace_user_ids(match, message, isUser=True):
        numeric_id = match.group(1)
        id = int(numeric_id)
        guild = message.guild

        if isUser:
            return await MuptBot.get_member_handle(guild, id)
        else:
            role = guild.get_role(id)
            return role.name

    @staticmethod
    async def get_member_handle(guild, member_id):
        member = await guild.fetch_member(member_id)
        return member.nick if member.nick else member.name