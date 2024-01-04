import argparse
import discord
from discord.ext.commands import Bot

import os
from os.path import join, dirname
from dotenv import load_dotenv
# from cogs.zigzag import find_old_threads

description = '''An example bot to showcase the discord.ext.commands extension
module.

There are a number of utility commands being showcased here.'''

parser = argparse.ArgumentParser()
parser.add_argument("-p", '--prod', dest='prod', action='store_true')

global args
args = parser.parse_args()

cogs_directory = os.path.join(os.getcwd(), "cogs") 


intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class SpriteBot(Bot):
    def __init__(
        self,
        *args,
        is_prod : bool,
        initial_extensions: list[str],
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.initial_extensions = initial_extensions
        self.env = "prod" if is_prod else "dev"
        print("Starting bot in env {}".format(self.env))

    async def setup_hook(self) -> None:
        for extension in self.initial_extensions:
            await self.load_extension(extension)



dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

if args.prod:
    bot_key = os.environ.get("BOT_SECRET_PROD")
else:
    bot_key = os.environ.get("BOT_SECRET_DEV")


this_bot = SpriteBot(command_prefix='!',
                     description=description,
                     intents=intents,
                     is_prod=args.prod,
                     initial_extensions=["cogs.zigzag"])
this_bot.run(bot_key)