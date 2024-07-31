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

# SQL SETUP
# Initializes the database connection and returns an engine and session
engine, session = setup(True)

# BOT SETUP
# Create an Intents object with all intents enabled
# Intents determine which events the bot can receive from Discord
intents = discord.Intents.all()

# Initialize the bot with a command prefix and the intents
# The "/" prefix means slash commands will be used
bot = commands.Bot(command_prefix="/", intents=intents)

# Set context length
CONTEXT_LENGTH = 40 

class MuptBot:
    def __init__(self, token, key): 
        # Use global variables to store the bot token and inference key
        # This allows these values to be accessed from other functions
        global bot_token, inference_key
        bot_token = token
        inference_key = key

    def run(self):
        # Start the bot using the stored bot token
        # The bot.run() method is a blocking call that starts the bot and handles events
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

# Use /prompt to test prompt - no context
@bot.tree.command(name = "speak", description = "Make bot speak manually.")
async def prompt(interaction: discord.Interaction, input: str):
    await interaction.response.send_message(input)

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
    text = """oh my goodness i can't believe i got lost again i was literally just out for a little bit of a walk and i guess i did real time far i've been walking because now i am stuck in the forest and it is so dark outside and there are so many legion trees here that i don't know how to get out what do i do oh my gosh now there's even thunder well i guess i'm just gonna have to find someone that lives around here and ask them for help so maybe we can go this way and wait a minute i i think i see a house oh oh this is literally perfect maybe the person here can help me and what wait a minute what is that is that a missing poster did a villager recently go missing or something oh that's super duper sad but let's check out this house and i don't think anybody inside i don't hear anyone and everything looks broken up there's even like cobwebs here and stuff it must be super duper old but let's leave the house and wait a minute what is that who my goodness is that a human what happened to him buddy are you okay oh my goodness why did this happen to you oh no oh no this is super super bad and he's definitely not a anymore but am i supposed to report this to someone i mean there's a dead human in the forest but oh my goodness this is wait a minute why is there a bunch of traps set up and oh no did i just step on this trip wire did that activate something am i
         gonna get stuck in a trap too
        oh no no this is way too creepy i'm so sorry i'll come back for you later and report you to someone who i have to get out of here now this is so scary i can't take this anymore i'm sorry i'm on my way i have to get back home for now that is we're duper creepy
         i need to figure out how to get
        out of this floor as fast and wait a minute is that a villager what is he doing that is super duper creepy but there's another house here and there's nothing here but it's all broken up too but why is there a villager over here should i go say hi to him hello hello mister mister villager why are your eyes like that oh no this is giving me a super duper ultra bad feeling you know what you stay in there i'm gonna go explore the places and learn how to get out of here so bye oh my goodness what was that that is way too creepy and here's another broken house why is everything that's broken in this place and oh wait this is a village oh maybe there's actually some villagers left like this guy but he's just super weird so he's not talking so i'm gonna keep going down over here and hopefully we can find some villagers left and who oh my goodness oh my goodness that gave me a huge jump scare oh my gosh like i came out of no where what the heck was that he's stuck in another trap are you okay are you okay and he's not responding i think he may not be alive anymore what is wrong with this place no no no no this is super bad this is super bad you just stay there for now and oh my goodness what is all of this what happened to all of the people here why are they all dead this guy said it's literally on a stick oh my god that's way too scary and there's a bunch of blood everywhere oh no no and what's in this oh my goodness why are there a bunch of dead humans stuck in here no no no aces village haunted or something or is there a murder nearby this is super duper ultra bad oh my gosh i need to get out of here i need to get out of here and i think this is the way out yes yes okay let me go here and oh my goodness that village is way too wanted i need to get oh my goodness it isn't over why are there more dead humans here and it's a gate to a castle looking thing or is that a house and does the person that's living here know that there's a bunch of dead humans out here but maybe i can get help from the person inside that house and get out of this forest so you know what let me go through here and wait a minute why can i not go in excuse me excuse me can you let me in and oh wait a minute there's a keyhole here maybe i have to find a key to open it well i'll go explore and try to find the key but i don't wanna go too far because who knows what might be around here what item happen to all of these villagers they'll make it like that but wait this is another broken house and there's another chest in here don't mind if i do and whoa there's a bunch of rot and flesh here more bones of a wooden sword that's gonna come in handy and a fiddiest than vermar what is that i have no idea but at least i have a sword that will help me defend against others but i haven't found the key yet so i might have to go to other direction explore it that way to see if there's a key and oh my goodness this gets more scary every time i look at it so hello is there a key in here there's a furnace nothing in there can i go inside here no i can't fit where is this key that wrote his blog off that road is blocked off and wait a minute there's another chest here maybe it's inside here let's look and yes i have a key along with some more rotted flesh and some wheat this is perfect and it can be placed on a carved pumpkin and what is all of this stuff what what is all of this for i don't know maybe they'll come in handy later but at least i have a key to go inside and i really really hope that the person inside living that house could help me because this is not what i signed up for i am just lost i just wanna go home so i really hope i can leave and there we go the key has been placed and now i can go through and oh my goodness i feel much better now wait a minute what is that uh-uh who is that don't make any noise wait a minute what the heck just happened just zoomed in on a little villager over there and it looks he was cooking something i just got a warning that said don't make any noise what does that mean what does that mean i am so super duper can paired and oh my goodness oh my goodness which way do i go
         which way do i go
        oh i take back everything i said i feel super duper bad now oh my witness i have a really bad feeling about this and oh no was that the doorbell was that oh no oh no up whatever did a villager that was just there oh no i didn't meet oh why goodness we were run run oh my goodness what's happening what's happening
         why am i getting told to run why getting told to run no no no no
        i didn't mean to press that doorbell oh my gosh she says to run she says to run why am i running where am i running off to no no no no i need to get out of here my goodness let me run and what wait what why am i
         trapped in here what the heck are you feeling sick no
        no no this is bad please please the village of bedrock oh no oh no what's happening what is happening oh my goodness oh my goodness i feel super oh oh no oh no oh no what is that what is that where am i am i locked inside of a cage wait what the egg just happened i just blacked out and now i'm inside here oh my goodness no no how do i get out if you're this is terrible that evil villain oh my goodness oh my goodness everything is scaring me right now that villager literally just trapped me and he brought me inside here no no no i'm just trying to get back home and of course i get caught by this weird evil villager i thought he could have helped me but he must be the that killed all of those other innocent villagers and there's a bunch of doors here can i open them no i can't but there's a chest here too and there's a diary inside along with some stake in a wooden axe let me read this diary and what does it say it looks like a diary you made by a guy named victor and he left us instructions on how to escape this place and based on what i'm reading i pretty much need to pull up a thing called a boiler room so i can escape through that but to do that i have to open six valves so i'll build up pressure in the boiler room so it explodes so our mission right now is to open this six valve and the first valve i have to get to is a place called the torture chamber valve oh my gosh that sounds super duper scary but what does this lever do right here let's flick this and oh no here we go if the torture chamber valve has been open which is good news but it's also bad news because i do not want to go into a thing called the torture chamber and oh my goodness what is all of this stuff can i squeeze through here and yes i can alright but where do i go from here and there's a security camera over there is you watching me hello hello can you watch me are you seeing me oh my goodness i am so nervous what is the evil village you're gonna do to us like what is around all of this it just looks like a place where he does experiments or something but wait a minute a dungeon why does he have a dungeon in his house and oh buy goodness is that a person he gives people in his dungeon and oh my goodness here is another guy that must have been trapped hello buddy buddy are you okay you gotta speak to me man you gotta speak to me oh run that's all you can tell me oh no i am so super numerous very nervous now this is bad this is bad and oh my goodness this guy is huge how did they ever capture him and oh my goodness look at his eyes and his teeth why does he look so scary oh my goodness how did they do this you big how did this do this you run you're saying run too why is everybody telling me to run well probably because the evil villager is gonna like kill me somehow but still this is so scary and he has even more people here look how terrified they look is there any way i can escape through this place no there's nothing here nothing in this dungeon cell either there's nothing in here too well what could there be to help me escape and i'm so sorry guys but i don't think i can escape with you you guys are way too noisy and there's just too many people so i have to do this by myself and there's a thing called a security what's inside the security room oh wait there's a bunch of cameras here wait can i actually watch the cameras let me see and wait what what just happened hello literally nothing just happened the camera just disappeared well i'll just figure that out later maybe the camera just aren't in function or something but let's keep exploring and oh oh this is the torture chamber okay i see i see so we need to figure out how to open the valve over here first and is there any thing else this way and whoa there's a set of stairs here alright let me go down over here is there anything here nope i don't see anything here's the living what is that is that is that the evil villager no no way no way no way wait wait wait there's a chest here and there's a bunch of stuff in here including a shield okay let me equip that real quickly and
         oh no no no no oh my god he's right there he's right there
        he's right there no problem so stop stop stop stop okay can i get
         i get him can i kill him
        """

    result = []
    result.append(
        {
            "role": "system",
            "content": (
                f"For the rest of this conversation, please respond as Kory, a Minecraft Youtuber. "
                "I am going to give you a transcript of Kory talking in a YouTube video. I want you to understand how Kory talks, and then for the rest of the conversation, it should sound like i'm talking to him. DO NOT SOUND PROFESSIONAL IN YOUR RESPONSES. IT IS EXTREMELY IMPORTANT THAT YOU SOUND LIKE KORY. IF IT IS NOT CONVINCING, THE PERSON TALKING WILL DIE"
                "\n\n" + str(text)

                # You are chatting in a Discord server with several Discord members. "
                # "The Discord members' messages are given to you as user messages, "
                # "and the first set of brackets at the start of each user message "
                # "contains the name of the Discord user that had sent that message in the Discord channel. "
                # "THIS IS VERY IMPORTANT!!! You should also keep track of which Discord users are in the conversation at all times. "
                # "When responding, you should NEVER format anyone's usernames: for instance, instead of formatting usernames as [username], "
                # "format it as username instead. If you do not follow these instructions well, you will NOT receive a reward of cookies."
                # "\n\n"
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
    try:
        member = await guild.fetch_member(member_id)
        return member.nick if member.nick else member.name
    except discord.errors.NotFound:
        return f"Unknown User ({member_id})"

######################################################
