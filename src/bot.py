import discord
from discord.ext.commands import Bot

import os
from os.path import join, dirname
from dotenv import load_dotenv
# from cogs.zigzag import find_old_threads

description = '''An example bot to showcase the discord.ext.commands extension
module.

There are a number of utility commands being showcased here.'''

cogs_directory = os.path.join(os.getcwd(), "cogs") 


intents = discord.Intents.default()
intents.members = True
intents.message_content = True

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
        for extension in self.initial_extensions:
            await self.load_extension(extension)



dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
bot_key = os.environ.get("BOT_SECRET")

bot = SpriteBot(command_prefix='!', description=description, intents=intents, initial_extensions=["cogs.zigzag"])
bot.run(bot_key)

