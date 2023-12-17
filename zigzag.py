
import discord
from discord.ext.commands import has_permissions, MissingPermissions, Bot

import os
from os.path import join, dirname
from dotenv import load_dotenv

description = '''An example bot to showcase the discord.ext.commands extension
module.

There are a number of utility commands being showcased here.'''

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = Bot(command_prefix='!', description=description, intents=intents)

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


@bot.command()
async def add(ctx, left: int, right: int):
    """Adds two numbers together."""
    await ctx.send(left + right)


@bot.command(hidden=True)
@has_permissions(manage_roles=True)
async def oldest(ctx):
    """Find the oldest threads with a given tag."""
    channel= bot.get_channel(1185685268133593118) # SpritePost channel ID
    target_tag = channel.get_tag(1185685810960420874) # "Needs Feedback" tag ID

    archived_threads = channel.archived_threads(limit=100) #TODO: Only search BEFORE cached date

    old_threads = []
    
    async for thread in archived_threads:
        if target_tag in thread.applied_tags:
            old_threads.append(thread.jump_url)
    
    await ctx.send(ctx.author)
    await ctx.send(old_threads)


@bot.group()
async def cool(ctx):
    """Says if a user is cool.

    In reality this just checks if a subcommand is being invoked.
    """
    if ctx.invoked_subcommand is None:
        await ctx.send(f'No, {ctx.subcommand_passed} is not cool')


@cool.command(name='bot')
async def _bot(ctx):
    """Is the bot cool?"""
    await ctx.send('Yes, the bot is cool.')


bot_key = os.environ.get("BOT_SECRET")
bot.run(bot_key)
