import asyncio
import os
from discord.ext.commands import Bot, Cog, Context, command, has_role, has_any_role

from discord import ForumTag, Member, Thread, Attachment, Message, ui, Embed, User, Client, client
import discord
from cogs.utils import clean_pokemon_string, fusion_is_valid, raw_pokemon_name_to_id

ERROR_CHANNEL_ID = None
GUIDELINES_THREAD_ID = None
GUIDELINES_THREAD = None

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

async def setup(bot:Bot):
    await bot.add_cog(Chansey(bot))


def valid_ids_in_title(thread: Thread):
    # Check post title for numbers. We are assuming that the numbers in the post are separated by '.' (i.e 162.187)
    thread_title = thread.name
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