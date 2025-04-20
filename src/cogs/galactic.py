import asyncio
import os
from discord.ext.commands import Bot, Cog, Context, has_any_role, hybrid_command, parameter, MissingRole
from discord import Message, Thread, User, utils, Member
import discord
import logging
import json
import random

logger = logging.getLogger(__name__)
from cogs.utils import is_former_spriter, update_former_spriter_cache

FORMER_SPRITER_ROLE_ID = None

FILEPACK_DIR = "/datadir/"
galactic_member_file = os.path.join(FILEPACK_DIR, "galactic-members.txt")
MIME_JR_ID = 641801785618726956
GRUNT_ROLE_ID = 1361797020578480369
EVIL_LEADER_ROLE_ID = 1361787890052501525

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
                brief = "Leaves(???) team galactic")
    async def leave_team_galactic(self, ctx: Context):
        if is_team_galactic(ctx.author):
            await ctx.send("Hey, no one leaves Team Galactic! Not without Cyrus' permission!")
        else:
            await ctx.send("Hey, you need to join Team Galactic first!")

    @hybrid_command(name="join-team-galactic",  pass_context=True,
                help ="Join the nobel cause of Team Galactic!",
                brief = "Join team galactic (optionally specify a recruiter)")
    async def join_team_galactic(self, ctx: Context, referrer_grunt: discord.User = parameter(default=None, description="(Optional) name of the grunt that recruited you")):
        if is_team_galactic(ctx.author):
            # This will fix a role if its missing
            await add_galactic_member(ctx, ctx.author)

            await ctx.send(f"You are already a proud member of Team Galactic, {ctx.author.mention}! Now, go recruit more grunts!")
            return
        
        message_prefix = ""
        if referrer_grunt is not None:
            if not is_team_galactic(referrer_grunt):
                await ctx.send(f"{referrer_grunt.name} is not a Team Galactic grunt. Maybe you should join Team Galactic (without specifying a referrer) and recruit *them* to our cause.")
                return
            else:
                update_members_points(referrer_grunt, 3)
                message_prefix = f"I see our loyal grunt, {referrer_grunt.mention}, has recruited you. "

        try:
            await add_galactic_member(ctx, ctx.author)
        except BaseException as e:
            print(e)
            await ctx.send("Something went wrong with joining.")
            return

        file = discord.File(os.path.join(os.getcwd(), "src", "data", "Team_galactic_logo.png"))
        message = message_prefix + f"**Welcome to Team Galactic, {ctx.author.mention}!**\n(Now a subsidiary of Team Rainbow Rocket)\n\nOur leader, Cyrus, wishes to "\
                    "create a new world, free of strife. Every pokemon, grunt, and fusion that joins the cause will help fix this "\
                    "incomplete world. Our dream is on the verge of becoming reality!\n\n"\
                    "Go forth, and bring pride to our team! You may check your points at any time with `/galactic-grunt-stats`. May our hearts beat as one!"
        await ctx.send(message, file=file)


    @hybrid_command(name="galactic-grunt-stats", pass_context=True,
                help ="Check your grunt stats for Team Galactic",
                brief = "Check your Team Galactic stats")
    async def check_grunt_stats(self, ctx: Context):
        if is_team_galactic(ctx.author):
            file = discord.File(os.path.join(os.getcwd(), "src", "data", "grunts.png"))
            await ctx.send(f"You have {TEAM_GALACTIC_MEMBERS[str(ctx.author.id)]['points']} grunt points!", file=file)
        else:
            await ctx.send("Hang on, you're not a Team Galactic grunt! Get out of here, kid!")


    @has_any_role(EVIL_LEADER_ROLE_ID, "Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="cyrus-remove-grunt", pass_context=True,
                help ="Lets Cyrus boot a grunt from Team Galactic",
                brief = "Boots a team galactic member")
    async def cyrus_boot(self, ctx: Context, name: User = None):
        try:
            await remove_from_galactic(ctx, name)
        except BaseException as e:
            print(e)
            return
        await ctx.send(f"{name} is no longer a grunt", ephemeral=True)

    @cyrus_boot.error
    async def help_cyrus_boot(_, ctx, __):
        await ctx.send("This command is for Cyrus!", ephemeral=True)


    @has_any_role(EVIL_LEADER_ROLE_ID, "Bot Manager", "Creator")
    @hybrid_command(name="cyrus-grant-points", pass_context=True,
            help ="Lets Cyrus boot a grunt from Team Galactic",
            brief = "Grants a member points")
    async def grant_grunt_points(self, ctx: Context, grunt: discord.User, points:int):
        if not is_team_galactic(grunt):
            await ctx.send(f"{grunt.mention} is not a grunt.", ephemeral=True)
        update_members_points(grunt, points)
        await ctx.send(f"{ctx.author.mention} has awarded {grunt.mention} {points} grunt points!")

    @grant_grunt_points.error
    async def help_grunt_error(_, ctx, __):
        await ctx.send("This command is for Cyrus!", ephemeral=True)

    @has_any_role(EVIL_LEADER_ROLE_ID, "Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="cyrus-lookup", pass_context=True,
                help ="Lets Cyrus see grunt stats",
                brief = "Stats for Cyrus")
    async def cyrus_stats(self, ctx: Context, grunt: discord.User=None):
        if not grunt:
            await ctx.defer()
            await ctx.send("Gathering stats...", ephemeral=True, delete_after=5)
            message = ""
            for member_id in TEAM_GALACTIC_MEMBERS:
                try:
                    member = ctx.guild.get_member(int(member_id))
                    message += f"{member.mention}:\t{TEAM_GALACTIC_MEMBERS[str(member_id)]['points']}\n"
                except BaseException as e:
                    message += f"{TEAM_GALACTIC_MEMBERS[str(member_id)]['name']}:\t{TEAM_GALACTIC_MEMBERS[str(member_id)]['points']}\n"
                if len(message) > 1500:
                    await ctx.send(message, ephemeral=True)
                    message = ""

            await ctx.send(message, ephemeral=True)
            return
        
        if is_team_galactic(grunt):
            await ctx.send(f"{TEAM_GALACTIC_MEMBERS[str(grunt.id)]}", ephemeral=True)
        else:
            await ctx.send(f"This user is not a grunt", ephemeral=True)
        
    @grant_grunt_points.error
    async def help_cyrus_stats(_, ctx, __):
        await ctx.send("This command is for Cyrus!", ephemeral=True)
        
def is_team_galactic(user: User | Member):
    return str(user.id) in TEAM_GALACTIC_MEMBERS or any([role.id == GRUNT_ROLE_ID for role in user.roles])

async def add_galactic_member(ctx: Context, user: User | Member):
    global TEAM_GALACTIC_MEMBERS
    if str(user.id) not in TEAM_GALACTIC_MEMBERS:
        TEAM_GALACTIC_MEMBERS[str(user.id)] = {"name" : user.name , "points" : 0}

    grunt_role = utils.get(ctx.guild.roles,id=GRUNT_ROLE_ID)
    await user.add_roles(grunt_role)

    with open(galactic_member_file, "w") as f:
        f.write(json.dumps(TEAM_GALACTIC_MEMBERS))

def update_members_points(user: User | Member, points: int):
    global TEAM_GALACTIC_MEMBERS
    if not is_team_galactic(user):
        return

    if not str(user.id) in TEAM_GALACTIC_MEMBERS:
        TEAM_GALACTIC_MEMBERS[str(user.id)]["name"] = user.name
        TEAM_GALACTIC_MEMBERS[str(user.id)]["points"] = 0

    TEAM_GALACTIC_MEMBERS[str(user.id)]["points"] += points
    with open(galactic_member_file, "w") as f:
        f.write(json.dumps(TEAM_GALACTIC_MEMBERS))

async def remove_from_galactic(ctx: Context, user: User | Member):
    global TEAM_GALACTIC_MEMBERS
    try:
        del TEAM_GALACTIC_MEMBERS[str(user.id)]
    except BaseException as e:
        pass
    grunt_role = utils.get(ctx.guild.roles,id=GRUNT_ROLE_ID)
    try:
        await user.remove_roles(grunt_role)
    except BaseException as e:
        pass

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
