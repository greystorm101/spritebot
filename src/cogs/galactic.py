import asyncio
import os
from discord.ext.commands import Bot, Cog, Context, has_any_role, hybrid_command
from discord import Message, Thread, User, utils, Member
import discord
import logging

logger = logging.getLogger(__name__)
from cogs.utils import is_former_spriter, update_former_spriter_cache

FORMER_SPRITER_ROLE_ID = None

FILEPACK_DIR = "./datadir/"

TEAM_GALACTIC_MEMBERS = []

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
                help ="Join the nobel cause of team galactic!",
                brief = "Joins team galactic")
    async def join_team_galactic(self, ctx: Context):
        users_id = ctx.author.id
        if is_team_galactic(users_id):
            await ctx.send(f"You are already a proud member of Team Galactic, {ctx.author.mention}! ")
            return
        try:
            update_galactic_members(int(users_id))
            print(TEAM_GALACTIC_MEMBERS)
        except BaseException as e:
            print(e)
            await ctx.send("Something went wrong with joining.")
            return
        file = discord.File(os.path.join(os.getcwd(), "src", "data", "Team_galactic_logo.png"))
        await ctx.send(f"Welcome to Team Galactic, {ctx.author.mention}!", file=file)

    @Cog.listener()
    async def on_message(self, message: Message):
        if "galactic" in message.content.lower() and not message.author.bot:
            if is_team_galactic(message.author.id):
                file = discord.File(os.path.join(os.getcwd(), "src", "data", "grunts.png"))
                await message.reply(f"Everything is for everyone, and for the good of Team Galactic!", file=file)

    # @has_any_role("Sprite Manager", "Bot Manager", "Creator")
    # @hybrid_command(name="cyrus-remove-grunt", pass_context=True,
    #             help ="Lets cyrus boot a grunt from team galactic",
    #             brief = "Boots a team galactic member")
    # async def cyrus_boot(self, ctx: Context, name: User = None):
    #     former_spriter = ctx.guild.get_member(name.id)
        
        
def is_team_galactic(id:int):
    return id in TEAM_GALACTIC_MEMBERS

def update_galactic_members(id: int):
    former_spriters_fd = open(os.path.join(FILEPACK_DIR, "galactic-members.txt"), "a")
    former_spriters_fd.write(f"{id}\n")
    former_spriters_fd.close()
    TEAM_GALACTIC_MEMBERS.append(int(id))

def remove_from_galactic(id:int):
    pass

def load_env_vars(env: str):
    galactic_file = os.path.join(FILEPACK_DIR, "galactic-members.txt")
    if not os.path.isfile(galactic_file):
        fd = open(os.path.join(FILEPACK_DIR, "galactic-members.txt"), "w+")
        fd.write("")
        fd.close()

    fd = open(os.path.join(FILEPACK_DIR, "galactic-members.txt"), "r")
    for id in fd.readlines():
        try:
            TEAM_GALACTIC_MEMBERS.append(int(id))
        except BaseException:
            pass


async def setup(bot:Bot):
    await bot.add_cog(Galactic(bot))
