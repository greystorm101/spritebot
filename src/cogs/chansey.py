import asyncio
import os
from discord.ext.commands import Bot, Cog, Context, command, has_any_role, hybrid_command

from datetime import datetime, timedelta
from discord import ForumTag, Thread, Attachment, ui, User
import discord
from cogs.utils import clean_pokemon_string, raw_pokemon_name_to_id

ERROR_CHANNEL_ID = None
GUIDELINES_THREAD_ID = None
GUIDELINES_THREAD = None
MAX_NUM_ERROR_THREADS = 5

FILEPACK_NAME = "curpack.txt"
FILEPACK_DIR = ""

error_tags = {}

class Chansey(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.most_recent_date = None
        load_env_vars(bot)

    @Cog.listener()
    async def on_thread_create(self, thread: Thread):
        """
        Listen for an error thread to be created, and react depending on the content in the thread
        """
        await asyncio.sleep(2) # We run into an error sometimes if we read or send the message too fast after thread was created

        if thread.parent_id == ERROR_CHANNEL_ID:
            problem = False

            error_channel = self.bot.get_channel(ERROR_CHANNEL_ID)
            GUIDELINES_THREAD = error_channel.get_thread(GUIDELINES_THREAD_ID)
            tags = [tag.name for tag in thread.applied_tags]
            message = f"Hey {thread.owner.mention},\nThanks for your sprite error submission. While you wait for a Chansey to start reviewing this ticket, "\
                      f"please make sure you've read through {GUIDELINES_THREAD.jump_url}."

            if ("float" in thread.name) or ("align" in thread.name) or ("off center" in thread.name):
                message += "\n\nA reminder that floating sprites in-game are **not** sprite errors"

            # Ensure fusion ids included in title, and there should be 2 if its a misnumber
            if not valid_ids_in_title(thread):
                problem = True
                message += "\n\n### Please make sure you include the relevant pokemon's ids in your post title.\nThis not only speeds up the process for our volunteers, "\
                            "but it also helps others search for issues that have already been reported."
                
                if "Misnumbered" in tags:
                    message+="\n**Since this report is a misnumbering issue, please make sure to include the sprite's current ID and correct ID**"
                
                # Try to fix title if we can parse pokemon names from the title
                ids_to_add = ids_to_add_to_title(thread)
                if len(ids_to_add) != 0:
                    ids_in_thread_name = thread.name + ' [' + ''.join(ids_to_add) + ']'
                    message += "\n\nThe title has been automatically edited to include my best guess at what the ids should be, but please make sure these are accurate and complete."
                    await thread.edit(name=ids_in_thread_name)

            if ("Visual error" in tags) or ("Needs fixing!" in tags):
                if len(thread.starter_message.mentions) == 0:
                    problem = True
                    message+="\n\n### Remember to tag the original fusion artist if you are reporting an error on a sprite that is not yours."
        
            await thread.send(content = message)

    @has_any_role("Chansey (sprite error fixer)", "Sprite Manager", "Bot Manager")
    @hybrid_command(name="pack", pass_context=True,
             help ="[CHANSEY] Marks an error thread to be revisited in the next pack release.",
             brief = "Packs an error thread")
    async def pack(self, ctx: Context):
        return_url = ctx.channel.jump_url
        # f = open("/datadir/curpack.txt", "a")
        f = open(f"{FILEPACK_DIR}{FILEPACK_NAME}", "a")

        f.write(f"{return_url}\n")
        f.close()
        await ctx.message.delete(delay=2)
        await ctx.send("This thread has been marked to be revisited in the next spritepack.")
        return

    @has_any_role("Chansey (sprite error fixer)", "Sprite Manager", "Bot Manager")
    @hybrid_command(name="release", pass_context=True,
             help ="[CHANSEY] Returns all threads to be revisited in this pack release",
             brief = "Returns packed threads")
    async def release(self, ctx: Context):
        try:
            f = open(f"{FILEPACK_DIR}{FILEPACK_NAME}", "r")
        except FileNotFoundError:
            await ctx.send("No threads were saved for this pack!")
            return

        # Release the hounds
        await ctx.send("Happy pack release! :partying_face: Here's the threads to revisit")

        for link in f.readlines():
            await ctx.send(link)
        f.close()
        await ctx.send("-----------------")
        await ctx.message.delete(delay=2)

        # Cleanup the file and save it off for archiving
        now = datetime.now()
        date_time = now.strftime("%m-%d-%Y-%H-%M-%S")
        os.rename(f"{FILEPACK_DIR}{FILEPACK_NAME}", f"{FILEPACK_DIR}{date_time}.txt")

        return

    @has_any_role("Chansey (sprite error fixer)", "Sprite Manager", "Bot Manager")
    @command(name="egg", pass_context=True,
             help ="[CHANSEY] Finds old error threads with unresolved tags tag. Run with `MM/DD/YY` to start at a certain date. Run with `reset` to start with 1 week ago. Add tag names to only search a subset",
             brief = "Finds old error threads")
    async def old_errors(self, ctx: Context, *args):
        """Find old error threads threads with given tags if specified."""

        await check_and_load_cache(self.bot)

        # Parse args and determine start date
        if args is not None:
            self.target_tags = []
            for arg in args:
                if len(arg.split('/')) == 3:
                    try:
                        start_time = datetime.strptime(arg, "%m/%d/%y")
                    except ValueError:
                        await ctx.send("Cannot parse start time as MM/DD/YY: {}".format(arg))
                        return
                    self.most_recent_date = start_time

                elif arg.lower() == "reset":
                    self.most_recent_date = None

                else:
                    # This arg may be a tag
                    try:
                        error_tags[arg.lower()]
                    except KeyError:
                        await ctx.send("Unrecognized tag/argument: {}\n**Make sure tag names have `-` instead of space.** Ex: `Needs Fixing` should be `Needs-Fixing`".format(arg))
                        return

                    self.target_tags.append(error_tags[arg.lower()])

        if self.most_recent_date is None:
            two_weeks_ago = datetime.now()-timedelta(weeks=1)
            self.most_recent_date = two_weeks_ago

        error_channel = self.bot.get_channel(ERROR_CHANNEL_ID) # SpritePost channel ID
        archived_threads = error_channel.archived_threads(limit=500, before=self.most_recent_date)
        num_found_threads = 0
        archived_thread_found = False

        await ctx.send("Searching for threads. This may take a few minutes. Wait for 'complete' message at end. \n --- :egg: :egg: :egg: :egg: --- ")
        async for thread in archived_threads:
            archived_thread_found = True

            if error_tags["not-an-error/dupe"] not in thread.applied_tags and error_tags["implemented"] not in thread.applied_tags:
                if (set(self.target_tags) <= set(thread.applied_tags)):
                    num_found_threads += 1

                    first_message = await thread.history(oldest_first=True).__anext__()

                    try:
                        candidate_image = first_message.attachments[0]
                    except:
                        candidate_image = None
                    thread_owner = await self.bot.fetch_user(thread.owner_id)

                    message = _pretty_formatted_message(thread, candidate_image, thread_owner)

                    selectView = ErrorOptionsView(thread, thread_owner)
                    await ctx.send(message, view=selectView)

                    self.most_recent_date = thread.archive_timestamp

            # Check if we are at our max number of threads
            if num_found_threads >= MAX_NUM_ERROR_THREADS:
                break

        if num_found_threads == 0:
            if not archived_thread_found:
                await ctx.send("Found no error threads active before {}.\nTry re-running with `reset` or a specific date `MM/DD/YY`".format(self.most_recent_date))
                return
            await ctx.send("Found no error threads between {} and {}.\n"\
                           "Run again to search later, or you can run again with `reset` or a specific date `MM/DD/YY`".format(
                               self.most_recent_date,
                               thread.archive_timestamp))
            self.most_recent_date = thread.archive_timestamp

        await ctx.send("Complete!")

async def setup(bot:Bot):
    await bot.add_cog(Chansey(bot))

class ErrorOptionsView(discord.ui.View):
    def __init__(self, thread: Thread, thread_owner:User):
        """

        Args:
            - thread (Thread): candidate thread
        """
        super().__init__(timeout=None)

        # Adds the dropdown to our view object.

        self.add_item(ErrorOptions(thread, thread_owner))

class ErrorOptions(ui.Select):
    """
    Options available if the fusion was able to be identified
    """
    def __init__(self, thread: Thread, thread_owner: User,):

        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(label='Implemented', description='Mark as implemented', emoji='📮'),
            discord.SelectOption(label='Not an Error/Dupe', description='Mark as Not an Error/Dupe', emoji='🖌'),
            discord.SelectOption(label='Manual', description="Don't do anything", emoji='🧀'),
        ]

        self.thread = thread
        self.thread_owner = thread_owner

        super().__init__(placeholder='Choose action...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):

        global error_tags
        choice = self.values[0]
        if choice == 'Implemented':
            gal_tag = error_tags["implemented"]
            await clean_tags(self.thread, gal_tag)

            message = "{} marked {} as implemented".format(interaction.user, self.thread.jump_url)

        elif choice == 'Not an Error/Dupe':
            gal_tag = error_tags["not-an-error/dupe"]
            await clean_tags(self.thread, gal_tag)
            message = "{} marked {} as not an error/dupe".format(interaction.user, self.thread.jump_url)

        elif choice == 'Manual':
            message = "{} manually handling {}".format(interaction.user, self.thread.jump_url)

        else:
            message = "How did you do this???? Your choice was {}".format(choice)

        await interaction.message.edit(content = message)
        await interaction.response.defer()
        return True

async def clean_tags(thread:Thread, remaining_tag: ForumTag):
    """Removes Needs Feedback tag and adds the remaing_tag"""
    # Discords api is weird, so we have to unarchive to edit it, and then rearchive the thread
    await thread.edit(archived=False, applied_tags=[remaining_tag])
    await thread.edit(archived=True)
    return

async def check_and_load_cache(bot: Bot):
    """
    Makes sure the cache is filled with channel and tag names
    """
    global error_tags
    if error_tags == {}:
        error_channel = bot.get_channel(ERROR_CHANNEL_ID)
        error_tags = {tag.name.lower().replace(' ','-'):error_channel.get_tag(tag.id) for tag in error_channel.available_tags}


def valid_ids_in_title(thread: Thread):
    # Check post title for numbers. We are assuming that the numbers in the post are separated by '.' (i.e 162.187)
    tags = [tag.name for tag in thread.applied_tags]

    num_ids = _number_of_ids_in_string(thread.name)

    if num_ids >= 4 and "Misnumbered" in tags:
        return True
    elif num_ids >= 2 and "Misnumbered" not in tags:
        return True
    
    return False


def _number_of_ids_in_string(string: str):
    non_numeric_id_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ !?@#$%^&*()[]-+="\\"/\n'
    numbers_and_periods = string.translate({ord(i): None for i in non_numeric_id_chars}).split('.')
    numbers = [item for item in numbers_and_periods if item != '']

    return len(numbers)

def ids_to_add_to_title(thread: Thread):
    # For my sanity, we're assuming names  are seperated by a '/' for now (i.e Furret/Hoppip)
    ids_to_add = []
    slash_seperated = [[clean_pokemon_string(word) for word in str.split(' ') if word != ''] for str in thread.name.split('/')]

    while len(slash_seperated) >= 2:
        slash_seperated[0]
        pre_slash, post_slash = slash_seperated[0], slash_seperated[1]

        # Grab head fusion id
        head_id = raw_pokemon_name_to_id(pre_slash[-1])
        if (head_id is None) and (len(pre_slash) > 1):
            # Try checking if this is a name seperated by a space
            head_id = raw_pokemon_name_to_id(''.join([pre_slash[-2], pre_slash[-1]]))

        # # Grab body fusion id
        body_id = raw_pokemon_name_to_id(post_slash[0])
        if (body_id is None) and (len(post_slash) > 1):
            # Try checking if this is a name seperated by a space
            body_id = raw_pokemon_name_to_id(''.join([post_slash[0], post_slash[1]]))

        # Check if this ID is already in the title
        id_string = f"({head_id}.{body_id})"
        if id_string not in thread.name:
            ids_to_add.append(id_string)
        slash_seperated.pop(0)

    return ids_to_add

def load_env_vars(bot: Bot):
    """ Loads in env vars based on dev or prod. Makes me cry."""
    env = bot.env
    is_dev = env == "dev"

    global ERROR_CHANNEL_ID
    ERROR_CHANNEL_ID = os.environ.get("DEV_ERROR_CHANNEL_ID") if is_dev else os.environ.get("ERROR_CHANNEL_ID")
    ERROR_CHANNEL_ID = int(ERROR_CHANNEL_ID)

    global GUIDELINES_THREAD_ID
    GUIDELINES_THREAD_ID = os.environ.get("DEV_GUIDELINES_THREAD_ID") if is_dev else os.environ.get("GUIDELINES_THREAD_ID")
    GUIDELINES_THREAD_ID = int(GUIDELINES_THREAD_ID)


def _pretty_formatted_message(thread: Thread,
                            candidate_image:Attachment,
                            thread_owner:User):
    """Formats output message text"""
    if thread_owner is None:
        print("Thread with url {} has none user".format(thread.jump_url))
        owner_name = "Unable to parse username."
    else:
        owner_name = thread_owner.name

    header =   'Thread: {} by {}\n'.format(thread.jump_url, owner_name)
    activity = 'Created: *{}*. Archived: *{}*.\n\n'.format(thread.created_at.strftime("%m/%d/%Y"), thread.archive_timestamp.strftime("%m/%d/%Y"))

    # Format candidate section
    if candidate_image is None:
        candidate_info = "No Image found\n"
    else:
        candidate_info = "{}\n".format(candidate_image)

    # Format tags section
    tag_info = "Tags:{}".format([tag.name for tag in thread.applied_tags])

    full_message = "~~~~~~~~~~~~~~\n"+header+activity+candidate_info+tag_info

    return full_message