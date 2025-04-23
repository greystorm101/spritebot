import asyncio
import os
from discord.ext.commands import Bot, Cog, Context, command, has_any_role, hybrid_command

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from discord import ForumTag, Interaction, TextChannel, TextStyle, Thread, Attachment, User, Message, app_commands
from discord.ui import Modal, TextInput
import discord
from cogs.utils import clean_pokemon_string, raw_pokemon_name_to_id

from google_auth_oauthlib.flow import Flow

SPRITEGALLERY_CHANNEL_ID = None
GUIDELINES_THREAD_ID = None
GUIDELINES_THREAD = None
MAX_NUM_ERROR_THREADS = 5

FILEPACK_NAME = "curpack.txt"
FILEPACK_DIR = "./datadir/"

error_tags = {}

class Unown(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.most_recent_date = None
        load_env_vars(bot)

    # @Cog.listener()
    # async def on_message_edit(self, message: Message):
    #     pass

    # @Cog.listener()
    # async def on_message(self, message: Message):
    #     """
    #     Listen for an error thread to be created, and react depending on the content in the thread
    #     """
    #     await asyncio.sleep(2) # We run into an error sometimes if we read or send the message too fast after thread was created
    #     author = message.author
    #     if message.channel.id == SPRITEGALLERY_CHANNEL_ID and not author.bot:
    #         await message.channel.send(author.id)
    #         print(message.content)

            # error_channel = self.bot.get_channel(ERROR_CHANNEL_ID)
            # GUIDELINES_THREAD = error_channel.get_thread(GUIDELINES_THREAD_ID)
            # tags = [tag.name for tag in thread.applied_tags]
            # message = f"Hey {thread.owner.mention},\nThanks for your sprite error submission. While you wait for a Chansey to start reviewing this ticket, "\
            #           f"please make sure you've read through {GUIDELINES_THREAD.jump_url}."

            # if ("float" in thread.name) or ("align" in thread.name) or ("off center" in thread.name):
            #     message += "\n\nA reminder that floating sprites in-game are **not** sprite errors"

            # # Ensure fusion ids included in title, and there should be 2 if its a misnumber
            # if not valid_ids_in_title(thread):
            #     problem = True
            #     message += "\n\n### Please make sure you include the relevant pokemon's ids in your post title.\nThis not only speeds up the process for our volunteers, "\
            #                 "but it also helps others search for issues that have already been reported."
                
            #     if "Misnumbered" in tags:
            #         message+="\n**Since this report is a misnumbering issue, please make sure to include the sprite's current ID and correct ID**"
                
            #     # Try to fix title if we can parse pokemon names from the title
            #     ids_to_add = ids_to_add_to_title(thread)
            #     if len(ids_to_add) != 0:
            #         ids_in_thread_name = thread.name + ' [' + ''.join(ids_to_add) + ']'
            #         message += "\n\nThe title has been automatically edited to include my best guess at what the ids should be, but please make sure these are accurate and complete."
            #         await thread.edit(name=ids_in_thread_name)

            # if ("Visual error" in tags) or ("Needs fixing!" in tags):
            #     if len(thread.starter_message.mentions) == 0:
            #         problem = True
            #         message+="\n\n### Remember to tag the original fusion artist if you are reporting an error on a sprite that is not yours."
        
            # await thread.send(content = message)

    @has_any_role("Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="entries", pass_context=True,
             help ="Run with `MM/YY` to start at a certain date. Run with `reset` to start with 2 weeks ago",
             brief = "Finds old threads")
    @app_commands.describe(start_message_id="Message to start with (non-inclusive)", end_message_id= "Message to end with (non-inclusive)")
    async def scrape_entries(self, ctx: Context, start_message_id:str, end_message_id:str):
        """Find the oldest threads with a given tag. Main Zigzag command"""
        # Parse args and determine start date
        
        # await self.google_auth(ctx)
        gallery_channel= self.bot.get_channel(SPRITEGALLERY_CHANNEL_ID)

        start_message: Message = await gallery_channel.fetch_message(int(start_message_id))
        end_message: Message = await gallery_channel.fetch_message(int(end_message_id))

        start_time = start_message.created_at
        end_time = end_message.created_at

        flow = Flow.from_client_secrets_file(
        os.path.join(FILEPACK_DIR, "credentials.json"),
        scopes = ["https://www.googleapis.com/auth/spreadsheets"],
        redirect_uri='urn:ietf:wg:oauth:2.0:oob')

        # Tell the user to go to the authorization URL.
        auth_url, _ = flow.authorization_url(prompt='consent')
        auth_input = AuthCodeView(start_time, end_time, flow)
        message = '**This command requires authorization to make edits to google sheets.** You will need to sign in with an account that has access to the credits/dex sheets.\n'\
                  'Please go the following URL: {}\nEnter the auth code below:\n'.format(auth_url)
    
        await ctx.send(message, view=auth_input)

        # gallery_data = await scrape_gallery(gallery_channel, start_time, end_time)
        # print(gallery_data)

        # dex_entries = []

        # for gallery_post in gallery_data:
        #     dex_text = find_dex_text(gallery_post.content)
        #     if dex_text is None:
        #         continue

        #     cleaned_text = dex_text.lstrip().rstrip()
        #     file_name = gallery_post.attachments[0].filename
        #     dex_row = {"author": gallery_post.author.name, "fusion":  file_name, "entry": cleaned_text }
        #     dex_entries.append(dex_row)

        # await ctx.channel.send(dex_entries)
        return 

    async def google_auth(self, ctx: Context):
        flow = Flow.from_client_secrets_file(
        os.path.join(FILEPACK_DIR, "credentials.json"),
        scopes = ["https://www.googleapis.com/auth/spreadsheets"],
        redirect_uri='urn:ietf:wg:oauth:2.0:oob')

        # Tell the user to go to the authorization URL.
        auth_url, _ = flow.authorization_url(prompt='consent')
        msg = await ctx.channel.send('**This command requires authorization to make edits to google sheets.** You will need to sign in with an account that has access to the credits/dex sheets."\
                             "\nPlease go the following URL: {}\Once you have clicked the link, **click the checkmark reaction** to continue'.format(auth_url),
                            delete_after=30)
        # TODO: When modals are less useless we can do this https://github.com/discord/discord-api-docs/discussions/4607
        

        def check(reaction, user):
            return user == ctx.author

        await msg.add_reaction("✅")
        x = await self.bot.wait_for('reaction_add')
        await msg.delete()
        
        wait_modal = GoogleAuthModal()
        await ctx.interaction.response.send_modal(wait_modal)
        val = await wait_modal.wait()
        print(val)

        code = input('Enter the authorization code: ')
        flow.fetch_token(code=code)
        session = flow.authorized_session()
        print(session.get('https://www.googleapis.com/userinfo/v2/me').json())

async def setup(bot:Bot):
    await bot.add_cog(Unown(bot))


class AuthCodeView(discord.ui.View): 
    def __init__(self, start_time:datetime, end_time:datetime, flow: Flow):
        
        super().__init__(timeout=None)
        self.add_item(AuthCodeEnter(start_time, end_time, flow))

class AuthCodeEnter(discord.ui.Button): 
    def __init__(self, start_time:datetime, end_time:datetime, flow: Flow):
        
        self.start_time = start_time
        self.end_time = end_time
        self.flow = flow

        super().__init__(label="Enter Authorization Code")
    
    async def callback(self, interaction: discord.Interaction):
        # print(self.value)
        # pass
        # print("ok")
        wait_modal = GoogleAuthModal()
        await interaction.response.send_modal(wait_modal)
        val = await wait_modal.wait()

        # self.flow.fetch_token(code=code)
        # session = flow.authorized_session()

async def scrape_gallery(gallery_channel: TextChannel, start:datetime, end: datetime):
    """
    Determines if cache is filled with all posts between start date and end date, and if not adds them in.
    """
    print("Requested Start:{} Requested End:{} ".format(start, end))

    return [message async for message in gallery_channel.history(after=start, before=end, oldest_first=True, limit=None)]

async def google_auth(ctx: Context):
    flow = Flow.from_client_secrets_file(
    os.path.join(FILEPACK_DIR, "credentials.json"),
    scopes = ["https://www.googleapis.com/auth/spreadsheets"],
    redirect_uri='urn:ietf:wg:oauth:2.0:oob')

    # Tell the user to go to the authorization URL.
    auth_url, _ = flow.authorization_url(prompt='consent')
    msg = await ctx.send('Please go to this URL: {}\n'.format(auth_url), ephemeral=True)
    # TODO: When modals are less useless we can do this https://github.com/discord/discord-api-docs/discussions/4607
    # wait_modal = GoogleAuthModal()
    # await interaction.response.send_modal(wait_modal)
    # await wait_modal.wait()

    await msg.add_reaction(":white_check_mark:")
    
    code = input('Enter the authorization code: ')
    flow.fetch_token(code=code)
    session = flow.authorized_session()
    print(session.get('https://www.googleapis.com/userinfo/v2/me').json())

class GoogleAuthModal(Modal, title = "Google Sheets Authorization"):

    name = discord.ui.TextInput(
        label=f'Enter Google Authorization Code',
        placeholder='Auth Code...',
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Thanks for your feedback, {self.name.value}!', ephemeral=True)
        self.value = self.name.value
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)


def find_dex_text(text: str) -> str:
    # We'll allow 2 types of formatting. "Dex: dex text" and "Foo `dex text` "
    if len(text.split('`')) == 3:
        return text.split('`')[1]
    if len(text.split('Dex:')) == 2:
        return text.split('Dex:')[1]
    if len(text.split('dex:')) == 2:
        return text.split('dex:')[1]

def load_env_vars(bot: Bot):
    """ Loads in env vars based on dev or prod. Makes me cry."""
    env = bot.env
    is_dev = env == "dev"

    global SPRITEGALLERY_CHANNEL_ID
    SPRITEGALLERY_CHANNEL_ID =int(os.environ.get("SPRITEGALLERY_CHANNEL_ID"))

    # global GUIDELINES_THREAD_ID
    # GUIDELINES_THREAD_ID = os.environ.get("DEV_GUIDELINES_THREAD_ID") if is_dev else os.environ.get("GUIDELINES_THREAD_ID")
    # GUIDELINES_THREAD_ID = int(GUIDELINES_THREAD_ID)
