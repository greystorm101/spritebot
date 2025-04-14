import asyncio
import os
from discord.ext.commands import Bot, Cog, Context, has_any_role, hybrid_command, parameter
from discord import Message, Thread, User, utils, Member
import discord
import logging
import json
import random

logger = logging.getLogger(__name__)
from cogs.utils import is_former_spriter, update_former_spriter_cache

FORMER_SPRITER_ROLE_ID = None

FILEPACK_DIR = "./datadir/"
galactic_member_file = os.path.join(FILEPACK_DIR, "galactic-members.txt")
MIME_JR_ID = 641801785618726956

galactic_quotes = ["Everything is for everyone, and for the good of Team Galactic!",
                "We're trying to create a new world that's better than this one.",
                "With the power of mythical Pokémon, Cyrus will become the ruler of Sinnoh!",
                "Team Galactic is going to do something huge for everyone's sake. That's why you should keep out of Team Galactic's way!",
                "Anything that opposes Team Galactic must be crushed! Even the very thought of opposition will not be tolerated!",
                "Team Galactic will get the three legendary Pokémon of the lakes! With their power, we will create an entirely new universe!",
                "Team Galactic, take all that we need, and eliminate what we do not!",
                "Team Galactic will rule the world!",
                "We are Team Galactic, and we seek to create a world without strife!"]

global TEAM_GALACTIC_MEMBERS
TEAM_GALACTIC_MEMBERS = {}

class Galactic(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        load_env_vars(bot.env)

    @hybrid_command(name="leave-team-galactic", pass_context=True,
                help ="Hey, wait! You can't leave team galactic!",
                brief = "Leaves? team galactic")
    async def leave_team_galactic(self, ctx: Context):
        users_id = ctx.author.id
        if is_team_galactic(users_id):
            await ctx.send(f"Hey, no one leaves Team Galactic! Not without Cyrus' permission!")
        else:
            await ctx.send(f"Hey, you need to join Team Galactic first!")

    @hybrid_command(name="join-team-galactic",  pass_context=True,
                help ="Join the nobel cause of Team Galactic!",
                brief = "Joins team galactic")
    async def join_team_galactic(self, ctx: Context, referer_grunt: discord.User = parameter(default=None, description="(Optional) name of the grunt that recruited you")):
        users_id = ctx.author.id
        if is_team_galactic(users_id):
            await ctx.send(f"You are already a proud member of Team Galactic, {ctx.author.mention}! Now, go recruit more grunts!")
            return
        try:
            update_galactic_members(int(users_id))
        except BaseException as e:
            print(e)
            await ctx.send("Something went wrong with joining.")
            return
        if referer_grunt is not None:
            referer_grunt.id
        file = discord.File(os.path.join(os.getcwd(), "src", "data", "Team_galactic_logo.png"))
        message = f"Welcome to Team Galactic, {ctx.author.mention}!\n\nOur leader GreyCyrus wishes to "\
                    "create a new world, free of strife. Every grunt and fusion joining to the cause will help fix this "\
                    "incomplete world. Our dream is on the verge of becoming reality! May our hearts beat as one!"
        await ctx.send(message, file=file)

    @Cog.listener()
    async def on_message(self, message: Message):
        if "galactic" in message.content.lower() and not message.author.bot:
            if is_team_galactic(message.author.id):
                file = discord.File(os.path.join(os.getcwd(), "src", "data", "grunts.png"))
                quote = get_random_galactic_quote()
                await message.reply(quote, file=file)

    @has_any_role(MIME_JR_ID, "Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="cyrus-remove-grunt", pass_context=True,
                help ="Lets Cyrus boot a grunt from Team Galactic",
                brief = "Boots a team galactic member")
    async def cyrus_boot(self, ctx: Context, name: User = None):
        former_grunt = name.id
        remove_from_galactic(former_grunt)
        await ctx.send(f"{name} is no longer a grunt", ephemeral=True)
        
        
def is_team_galactic(id:int):
    return id in TEAM_GALACTIC_MEMBERS

def update_galactic_members(id: int):
    global TEAM_GALACTIC_MEMBERS
    TEAM_GALACTIC_MEMBERS[id] = 0
    with open(galactic_member_file, "w") as f:
        f.write(json.dumps(TEAM_GALACTIC_MEMBERS))

def remove_from_galactic(id:int):
    global TEAM_GALACTIC_MEMBERS
    del TEAM_GALACTIC_MEMBERS[id]
    with open(galactic_member_file, "w") as f:
        f.write(json.dumps(TEAM_GALACTIC_MEMBERS))

def load_env_vars(env: str):
    global TEAM_GALACTIC_MEMBERS
    if not os.path.isfile(galactic_member_file):
        fd = open(galactic_member_file, "w")
        fd.write("{}")
        fd.close()

    with open(galactic_member_file, "r") as f:
        data = json.loads(f.read())
        TEAM_GALACTIC_MEMBERS = data

def get_random_galactic_quote() -> str:
    return random.choice(galactic_quotes)


async def setup(bot:Bot):
    await bot.add_cog(Galactic(bot))
