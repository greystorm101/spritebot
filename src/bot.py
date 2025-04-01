import argparse
import discord
from discord.ext.commands import Bot

import os
from os.path import join, dirname
from dotenv import load_dotenv

description = '''An example bot to showcase the discord.ext.commands extension
module.

There are a number of utility commands being showcased here.'''

parser = argparse.ArgumentParser()
parser.add_argument("-p", '--prod', dest='prod', action='store_true')
parser.add_argument("-l", '--local', dest='local', action='store_true')

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
        await self.tree.sync()

# If running locally, select the correct config file to run with
if args.local:
    print("Running with local config")
    if args.prod:
        dotenv_path = join(dirname(__file__), 'config', '.env.prod')
        
    else:
        dotenv_path = join(dirname(__file__), 'config', '.env.dev')
# Cluster always runs with mount at /config/.env
else:
    dotenv_path = join('/config', '.env')

print(dotenv_path)
load_dotenv(dotenv_path)

bot_key = os.environ.get("BOT_SECRET")

this_bot = SpriteBot(command_prefix='!',
                     description=description,
                     intents=intents,
                     is_prod=args.prod,
                     initial_extensions=["cogs.chansey", "cogs.contest",  "cogs.eraser", "cogs.klefki", "cogs.smeargle", "cogs.zigzag"])
this_bot.run(bot_key)