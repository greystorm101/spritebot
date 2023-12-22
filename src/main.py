import asyncio
import discord
from discord.ext.commands import has_permissions, MissingPermissions, Bot
import logging
import logging.handlers

import os
from os.path import join, dirname
from dotenv import load_dotenv
from aiohttp import ClientSession
# from cogs.zigzag import find_old_threads

description = '''An example bot to showcase the discord.ext.commands extension
module.

There are a number of utility commands being showcased here.'''

cogs_directory = os.path.join(os.getcwd(), "cogs") 


intents = discord.Intents.default()
intents.members = True
intents.message_content = True


# class SpriteBot(Bot):
#     def __init__(self):
#         super.__init__(
#             command_prefix='!',
#             description=description,
#             intents=intents
#         )

#     async def add_cogs(self):
#         """
#         """
#         for file in os.listdir(cogs_directory):
#             bot.load_extension()




dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# @bot.event
# async def on_ready():
#     print(f'Logged in as {bot.user} (ID: {bot.user.id})')
#     print('------')


# @bot.command()
# async def add(ctx, left: int, right: int):
#     """Adds two numbers together."""
#     await ctx.send(left + right)


# @bot.command(hidden=True)
# @has_permissions(manage_roles=True)
# async def oldest(ctx):
#     await find_old_threads(ctx, bot)


# @bot.group()
# async def cool(ctx):
#     """Says if a user is cool.

#     In reality this just checks if a subcommand is being invoked.
#     """
#     if ctx.invoked_subcommand is None:
#         await ctx.send(f'No, {ctx.subcommand_passed} is not cool')


# @cool.command(name='bot')
# async def _bot(ctx):
#     """Is the bot cool?"""
#     await ctx.send('Yes, the bot is cool.')


class SpriteBot(Bot):
    def __init__(
        self,
        *args,
        initial_extensions: list[str],
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.initial_extensions = initial_extensions

    async def setup_hook(self) -> None:

        # here, we are loading extensions prior to sync to ensure we are syncing interactions defined in those extensions.

        for extension in self.initial_extensions:
            print("loading")
            await self.load_extension(extension)

        # This would also be a good place to connect to our database and
        # load anything that should be in memory prior to handling events.

bot_key = os.environ.get("BOT_SECRET")


bot = SpriteBot(command_prefix='!', description=description, intents=intents, initial_extensions=["cogs.zigzag"])
bot.run(bot_key)

