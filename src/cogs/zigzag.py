from datetime import timedelta, datetime
import os
from dateutil.relativedelta import *
import io
import time
import sys

import pickle
from discord.ext.commands import Bot, Cog, Context, command, has_role, has_any_role
from discord import ForumTag, Member, Thread, Attachment, Message, ui, Embed, User
import discord
from discord.channel import TextChannel

from cogs.utils import clean_pokemon_string, raw_pokemon_name_to_id, id_to_name_map, fusion_is_valid

# Defining globals
SPRITEWORK_CHANNEL_ID = None
SPRITEGALLERY_CHANNEL_ID = None
NOQA_CHANNEL_ID = None

NEEDSFEEDBACK_TAG_ID = None
ADDEDTOGAL_TAG_ID = None
HARVESTED_TAG_ID = None
OTHER_TAG_ID = None
NONIF_TAG_ID = None

HARVEST_IMMUNITY_ID = None
POST_IMMUNITY_ID = None
DM_IMMUNITY_ID = None

MAX_LOOKAHEAD_THEAD_TIME = 21 # Amount of time, in days, that we will check in the gallery after time of spritework post, 
MAX_NUM_FEEDBACK_THREADS = 10 # Amount of feedback threads to find

GALLERY_FOOTER = "Note: This sprite was posted by a sprite manager or zigzagoon because it had gone unposted in spritework for over two weeks."\
                     "It may have an incorrect size, file name or other small issue. This will be fixed in the sprite pack!"


spritepost_tags = {}
sprite_channels = {}

cached_gal_list = []
cache_start_date = None
cache_end_date = None

class ZigZag(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.most_recent_date = None
        load_env_vars(bot.env)

    @command(name="tagids")
    async def tagids(self,  ctx: Context):
        """Debug command to get tag ids for the channel"""
        spritework_channel= self.bot.get_channel(SPRITEWORK_CHANNEL_ID)
        print(spritework_channel.available_tags)
    
    @has_any_role("Zigzagoon (abandoned sprite poster)", "Sprite Manager", "Bot Manager")
    @command(name="galcache")
    async def galcache(self,  ctx: Context, starttime = None):
        """Caches gallery posts"""
        pass
        spritework_channel= self.bot.get_channel(SPRITEWORK_CHANNEL_ID)

        start_time = datetime.strptime(starttime, "%m/%y")
        end_time = start_time + relativedelta(months=+1)
        print("Caching gallery from {} to {}".format(start_time, end_time))
        cached_gal_list = [message async for message in spritework_channel.history(after=start_time, before=end_time, oldest_first=True, limit=None)]
        # with open() as f:
        # pickle.dump

    @has_any_role("Zigzagoon (abandoned sprite poster)", "Sprite Manager", "Bot Manager")
    @command(name="dig", pass_context=True,
             help ="Finds old threads with needs feedback tag. Run with `MM/DD/YY` to start at a certain date. Run with `reset` to start with 2 weeks ago",
             brief = "Finds old threads")
    async def oldest(self, ctx: Context, start_args:str = None):
        """Find the oldest threads with a given tag. Main Zigzag command"""

        # Parse args and determine start date
        if start_args is not None:
            if len(start_args.split('/')) == 3:
                try:
                    start_time = datetime.strptime(start_args, "%m/%d/%y")
                except ValueError:
                    await ctx.send("Cannot parse start time as MM/DD/YY: {}".format(start_args))
                    return
                self.most_recent_date = start_time

            elif start_args.lower() == "reset":
                self.most_recent_date = None

        if self.most_recent_date is None:
            two_weeks_ago = datetime.now()-timedelta(weeks=2)
            self.most_recent_date = two_weeks_ago

        # Load in what we need from the cache and add back in type hints
        await check_and_load_cache(self.bot)
        spritework_channel = sprite_channels["spritework"]
        spritework_channel : TextChannel

        target_tag = spritepost_tags["feedback"]
        target_tag : ForumTag

        archived_threads = spritework_channel.archived_threads(limit=500, before=self.most_recent_date)
        num_found_threads = 0; archived_thread_found = False
        await ctx.send("Digging for threads. This may take a few minutes. Wait for 'complete' message at end. \n --- ⛏⛏⛏⛏⛏⛏⛏ --- ")
        async for thread in archived_threads:
            archived_thread_found = True

            if target_tag in thread.applied_tags:
                num_found_threads += 1

                start = time.time()
                thread_owner = await self.bot.fetch_user(thread.owner_id)
                candidate_image, canidate_ids, gal_post = await scrape_thread_and_gallery(thread, sprite_channels["gallery"], self.bot)
                archive_time = time.time() - start; print(f"Scraping Time: {archive_time}")

                start = time.time()
                message = _pretty_formatted_message(thread, candidate_image, canidate_ids, gal_post, thread_owner)
                archive_time = time.time() - start; print(f"Message Time: {archive_time}")

                selectView = PostOptionsView(thread, canidate_ids, candidate_image, thread_owner)
                await ctx.send(message, view=selectView)

                self.most_recent_date = thread.archive_timestamp

            # Check if we are at our max number of threads
            if num_found_threads >= MAX_NUM_FEEDBACK_THREADS:
                break
        
        if num_found_threads == 0:
            if not archived_thread_found:
                await ctx.send("Found no feedback threads active before {}.\nTry re-running with `reset` or a specific date `MM/DD/YY`".format(self.most_recent_date))
                return
            await ctx.send("Found no feedback threads between {} and {}.\n"\
                           "Run again to search later, or you can run again with `reset` or a specific date `MM/DD/YY`".format(
                               self.most_recent_date,
                               thread.archive_timestamp))
            self.most_recent_date = thread.archive_timestamp

        await ctx.send("Digging Complete!")
        
    @has_any_role("Zigzagoon (abandoned sprite poster)", "Sprite Manager", "Bot Manager")
    @command(name="galpost", pass_context=True,
             help ="Posts the replied to image to the gallery.",
             brief = "Posts image to gallery")
    async def galpost(self, ctx: Context, *args):

        await ctx.message.delete()
        await _manually_post_to_channel("gallery", ctx, args, self.bot)
        
    @has_any_role("Zigzagoon (abandoned sprite poster)", "Sprite Manager", "Bot Manager")
    @command(name="noqa", pass_context=True,
             help ="Finds old threads with needs feedback tag",
             brief = "Posts image to noqa")
    async def noqa(self, ctx: Context, *args):

        await ctx.message.delete()
        await _manually_post_to_channel("noqa", ctx, args, self.bot)

async def setup(bot:Bot):
    await bot.add_cog(ZigZag(bot))

class PostOptions(ui.Select):
    """
    Options available if the fusion was able to be identified
    """
    def __init__(self, thread: Thread, thread_owner: User, fusion:list, image:Attachment):

        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(label='Post', description='Post the candidate image to sprite gallery', emoji='📮'),
            discord.SelectOption(label='Harvest', description='Post candidate image to noqa', emoji='🖌'),
            discord.SelectOption(label='Clean', description='Remove Needs Feedback tag adds Added to Gallery tag', emoji='🧺'),
            discord.SelectOption(label='Non-IF', description='Remove Needs Feedback tag adds Non-if tag', emoji='🙃'),
            discord.SelectOption(label='Other', description='Remove Needs Feedback tag adds other tag', emoji='🤔'),
            discord.SelectOption(label='Manual', description="Don't do anything", emoji='🧀'),
        ]

        self.thread = thread
        self.thread_owner = thread_owner
        self.fusion = fusion
        self.image = image

        super().__init__(placeholder='Choose action...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):

        choice = self.values[0]
        if choice == 'Post':
            gal_tag = spritepost_tags["gallery"]
            await clean_tags(self.thread, gal_tag)

            if (is_user_post_immune(self.thread.owner)):
                await interaction.response.send_message("User has post immunity", delete_after=60, ephemeral=True)

            post = await post_to_channel(sprite_channels["gallery"], self.fusion, self.image, self.thread_owner, footer_message=GALLERY_FOOTER)
            await send_galpost_notification(self.thread, self.thread_owner, post)
            message = "{} posted sprite from thread {}".format(interaction.user, self.thread.jump_url)

        elif choice == 'Harvest':
            harvested_tag = spritepost_tags["harvested"]
            await clean_tags(self.thread, harvested_tag)

            if (is_user_harvest_immune(self.thread.owner)):
                await interaction.response.send_message("User has harvest immunity", delete_after=60, ephemeral=True)

            post = await post_to_channel(sprite_channels["noqa"], self.fusion, self.image, self.thread_owner, footer_message="")
            await send_noqa_notification(self.thread, self.thread_owner, post)
            message = "{}: Harvested thread {}".format(interaction.user, self.thread.jump_url)
            pass

        elif choice == 'Clean':
            gal_tag = spritepost_tags["gallery"]
            await clean_tags(self.thread, gal_tag)
            message = "{}: Marked {} as already added to gallery".format(interaction.user, self.thread.jump_url)

        elif choice == 'Non-IF':
            gal_tag = spritepost_tags["non-if"]
            await clean_tags(self.thread, gal_tag)
            message = "{}: Marked {} as non-if".format(interaction.user, self.thread.jump_url)

        elif choice == 'Other':
            gal_tag = spritepost_tags["other"]
            await clean_tags(self.thread, gal_tag)
            message = "{}: Marked {} as other".format(interaction.user, self.thread.jump_url)

        elif choice == 'Manual':
            message = "{}: manually handling {}".format(interaction.user, self.thread.jump_url)

        else:
            message = "How did you do this???? Your choice was {}".format(choice)

        await interaction.message.edit(content = message)
        await interaction.response.defer()
        return True


class UnidentifiedOptions(ui.Select):
    def __init__(self, thread: Thread, thread_owner: User):

        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(label='Clean', description='Remove Needs Feedback tag and add Other tag', emoji='🧺'),
            discord.SelectOption(label='Non-IF', description='Remove Needs Feedback tag adds Non-if tag', emoji='🙃'),
            discord.SelectOption(label='Other', description='Remove Needs Feedback tag adds other tag', emoji='🤔'),
            discord.SelectOption(label='Manual', description="Don't do anything", emoji='🧀'),
        ]
        self.thread = thread
        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Choose action...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        if choice == 'Clean':
            gal_tag = spritepost_tags["gallery"]
            await clean_tags(self.thread, gal_tag)
            message = "{}: Marked {} as already added to gallery".format(interaction.user, self.thread.jump_url)

        elif choice == 'Non-IF':
            gal_tag = spritepost_tags["non-if"]
            await clean_tags(self.thread, gal_tag)
            message = "{}: Marked {} as non-if".format(interaction.user, self.thread.jump_url)

        elif choice == 'Other':
            gal_tag = spritepost_tags["other"]
            await clean_tags(self.thread, gal_tag)
            message = "{}: Marked {} as other".format(interaction.user, self.thread.jump_url)

        elif choice == 'Manual':
            message = "{}: manually handling {}".format(interaction.user, self.thread.jump_url)

        await interaction.message.edit(content = message)
        await interaction.response.defer()
        return True

class ImmuneOptions(ui.Select):
    """ Options available if user has immunity to their sprites being posted """
    def __init__(self, thread: Thread, thread_owner: User):

        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(label='Clean', description='Remove Needs Feedback tag and add gallery tag', emoji='🧺'),
            discord.SelectOption(label='Non-IF', description='Remove Needs Feedback tag adds Non-if tag', emoji='🙃'),
            discord.SelectOption(label='Other', description='Remove Needs Feedback tag adds other tag', emoji='🤔'),
            discord.SelectOption(label='Manual', description="Don't do anything", emoji='🧀'),
        ]
        self.thread = thread
        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Choose action...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        if choice == 'Clean':
            gal_tag = spritepost_tags["gallery"]
            await clean_tags(self.thread, gal_tag)
            message = "{}: Marked {} as already added to gallery".format(interaction.user, self.thread.jump_url)

        elif choice == 'Non-IF':
            gal_tag = spritepost_tags["non-if"]
            await clean_tags(self.thread, gal_tag)
            message = "{}: Marked {} as non-if".format(interaction.user, self.thread.jump_url)

        elif choice == 'Other':
            gal_tag = spritepost_tags["other"]
            await clean_tags(self.thread, gal_tag)
            message = "{}: Marked {} as other".format(interaction.user, self.thread.jump_url)

        elif choice == 'Manual':
            message = "{}: manually handling {}".format(interaction.user, self.thread.jump_url)

        await interaction.message.edit(content = message)
        await interaction.response.defer()
        return True


class PostOptionsView(discord.ui.View):
    def __init__(self, thread: Thread, fusion: list, image: Attachment, thread_owner:User):
        """
        
        Args:
            - thread (Thread): candidate thread
            - fusion (list): list containing the fusion ids, in format [headid, bodyid]
            - image (Attachment): candidate image to post or harvest
        """
        super().__init__(timeout=None)

        # Adds the dropdown to our view object.
        if is_user_immune(thread.owner):
            self.add_item(ImmuneOptions(thread, thread_owner))
        
        elif fusion is False:
            self.add_item(UnidentifiedOptions(thread, thread_owner))
        else:
            self.add_item(PostOptions(thread, thread_owner, fusion, image))
            

def load_env_vars(env: str):
    """ Loads in env vars based on dev or prod. Makes me cry."""
    is_dev = env == "dev"

    global SPRITEWORK_CHANNEL_ID
    SPRITEWORK_CHANNEL_ID = os.environ.get("DEV_SPRITEWORK_CHANNEL_ID") if is_dev else os.environ.get("SPRITEWORK_CHANNEL_ID")
    SPRITEWORK_CHANNEL_ID = int(SPRITEWORK_CHANNEL_ID)

    global SPRITEGALLERY_CHANNEL_ID
    SPRITEGALLERY_CHANNEL_ID = os.environ.get("DEV_SPRITEGALLERY_CHANNEL_ID") if is_dev else os.environ.get("SPRITEGALLERY_CHANNEL_ID")
    SPRITEGALLERY_CHANNEL_ID = int(SPRITEGALLERY_CHANNEL_ID)

    global NOQA_CHANNEL_ID
    NOQA_CHANNEL_ID = os.environ.get("DEV_NOQA_CHANNEL_ID") if is_dev else os.environ.get("NOQA_CHANNEL_ID")
    NOQA_CHANNEL_ID = int(NOQA_CHANNEL_ID)

    global NEEDSFEEDBACK_TAG_ID
    NEEDSFEEDBACK_TAG_ID = os.environ.get("DEV_NEEDSFEEDBACK_TAG_ID") if is_dev else os.environ.get("NEEDSFEEDBACK_TAG_ID")
    NEEDSFEEDBACK_TAG_ID = int(NEEDSFEEDBACK_TAG_ID)

    global ADDEDTOGAL_TAG_ID
    ADDEDTOGAL_TAG_ID = os.environ.get("DEV_ADDEDTOGAL_TAG_ID") if is_dev else os.environ.get("ADDEDTOGAL_TAG_ID")
    ADDEDTOGAL_TAG_ID = int(ADDEDTOGAL_TAG_ID)

    global HARVESTED_TAG_ID
    HARVESTED_TAG_ID = os.environ.get("DEV_HARVESTED_TAG_ID") if is_dev else os.environ.get("HARVESTED_TAG_ID")
    HARVESTED_TAG_ID = int(HARVESTED_TAG_ID)

    global OTHER_TAG_ID
    OTHER_TAG_ID = 0 if is_dev else os.environ.get("OTHER_TAG_ID")
    OTHER_TAG_ID = int(OTHER_TAG_ID)

    global NONIF_TAG_ID
    NONIF_TAG_ID = os.environ.get("DEV_NONIF_TAG_ID") if is_dev else os.environ.get("NONIF_TAG_ID")
    NONIF_TAG_ID = int(NONIF_TAG_ID)

    global HARVEST_IMMUNITY_ID
    HARVEST_IMMUNITY_ID = os.environ.get("DEV_HARVEST_IMMUNITY_ID") if is_dev else os.environ.get("HARVEST_IMMUNITY_ID")
    HARVEST_IMMUNITY_ID = int(HARVEST_IMMUNITY_ID)

    global POST_IMMUNITY_ID
    POST_IMMUNITY_ID = os.environ.get("DEV_POST_IMMUNITY_ID") if is_dev else os.environ.get("POST_IMMUNITY_ID")
    POST_IMMUNITY_ID = int(POST_IMMUNITY_ID)

    global DM_IMMUNITY_ID
    DM_IMMUNITY_ID = os.environ.get("DEV_DM_IMMUNITY_ID") if is_dev else os.environ.get("DM_IMMUNITY_ID")
    DM_IMMUNITY_ID = int(DM_IMMUNITY_ID)


async def check_and_load_cache(bot: Bot):
    """
    Makes sure the cache is filled with channel and tag names
    """
    if sprite_channels == {}:
            sprite_channels["spritework"] = bot.get_channel(SPRITEWORK_CHANNEL_ID) # SpritePost channel ID
            sprite_channels["gallery"] = bot.get_channel(SPRITEGALLERY_CHANNEL_ID) # SpritePost channel ID
            sprite_channels["noqa"] = bot.get_channel(NOQA_CHANNEL_ID) # SpritePost channel ID

    if spritepost_tags == {}:
        spritework_channel = sprite_channels["spritework"]
        spritepost_tags["feedback"] = spritework_channel.get_tag(NEEDSFEEDBACK_TAG_ID) # "Needs Feedback" tag ID
        spritepost_tags["gallery"]  = spritework_channel.get_tag(ADDEDTOGAL_TAG_ID) # "Needs Feedback" tag ID
        spritepost_tags["harvested"]  = spritework_channel.get_tag(HARVESTED_TAG_ID) # "Needs Feedback" tag ID
        spritepost_tags["non-if"]  = spritework_channel.get_tag(NONIF_TAG_ID) # "Needs Feedback" tag ID
        spritepost_tags["other"]  = spritework_channel.get_tag(OTHER_TAG_ID) # "Needs Feedback" tag ID
 
 

async def scrape_thread_and_gallery(thread: Thread, gallery_channel: TextChannel, bot: Bot):
    """
    Takes a spritework thread and determines if the thread has
    been posted in sprite gallery

    Args:
        thread(Thread): spritework thread that is being evaluated

    Returns:
        List with three elements: [Candidate_image, candidate_id, gallery_post]
        Candidate_image: attachment of latest image from thread poster. False if no 
                        candidate image was found
        Candidate_id: Id of fusion in format xxx.xxx. False if bot was unable to identify
                    the fusion in the post
        gallery_post: Link to gallery post of fusion if it was able to be found. False if
                    no matching post was found.
    """
    candidate_image, candidate_ids = await _get_candidate_info(thread, bot)

    if candidate_image is False:
        # No image found in post
        return [False, False, False]
    
    if candidate_ids is False:
        # Can't identify pokemon in post
        return [candidate_image, False, False]
    
    gallery_post = await find_gallery_image(thread, candidate_ids, gallery_channel, bot)
    return [candidate_image, candidate_ids, gallery_post]


async def clean_tags(thread:Thread, remaining_tag: ForumTag):
    """Removes Needs Feedback tag and adds the remaing_tag"""
    # Discords api is weird, so we have to unarchive to edit it, and then rearchive the thread
    await thread.edit(archived=False, applied_tags=[remaining_tag])
    await thread.edit(archived=True)
    return


async def post_to_channel(channel: TextChannel, fusion:list, image: Attachment, author:User, footer_message:str, message: str = None):
    """
    Posts a given image to the given channel

        channel: channel to post message to
        fusion: list with head number as element 1 and bo
        image: image to post
        author: Discord member representing user who created the thread.
    """

    filename = f"{fusion[0]}.{fusion[1]} by {author.name}.png"
    image_bytes = await image.read()
    bytes_io_file = io.BytesIO(image_bytes)

    fusion_names = [id_to_name_map()[id] for id in fusion]
    gal_message_title = "{}/{} ({}.{})".format(fusion_names[0],
                                              fusion_names[1],
                                              fusion[0],
                                              fusion[1])
    if message is not None:
        gal_message_title += " {}".format(message)
    
    upload_image = discord.File(fp = bytes_io_file, filename=filename)
    

    embedded_message = Embed(title=gal_message_title, color=16764242)
    
    if author.avatar != None:
        embedded_message.set_author(name=author, icon_url=author.avatar.url)
    else:
        embedded_message.set_author(name=author)
    embedded_message.set_footer(text=footer_message)
    embedded_message.set_image(url="attachment://{}".format(filename.replace(' ','_')))

    post = await channel.send(file=upload_image, embed=embedded_message)
    return post


async def send_galpost_notification(thread: Thread, thread_owner: User, galleryPost: Message):
    message = f"### Hey {thread_owner.mention}!\nA sprite manager or Zigzagoon thought this sprite looked great, so it has "\
              f"been automatically posted to the sprite gallery for you here: {galleryPost.jump_url} :ohyes: . You can expect to see "\
              f"it included in an upcoming sprite pack release. **You should not post this sprite to the gallery, or it will cause a duplicate**\n"\
              f"## If you would like to remove this sprite from the gallery:\n- Ping `Zigzagoon (abandoned sprite poster)`"\
              f"or a sprite manager in this thread.\n- Let them know you would like the sprite removed from the gallery."\
              f"\n*Make sure to remove the “Needs Feedback” tag on your spritework posts once they’re added to the gallery* :happo: \n{galleryPost.embeds[0].image.url}"
    
    await thread.send(content = message)
    
    if is_user_zigzag_muted(thread.owner):
        return
    dm_message = f"Hey {thread_owner.mention}, this Pokemon Infinite Fusion sprite has been posted to the sprite gallery by "\
              f"a sprite manager or zigzagoon. You can see the gallery post here: {galleryPost.jump_url}\n"\
              f"If you have any questions or would like to remove the post, please ping a sprite manager or zigzagoon in this thread:{thread.jump_url}.\n{galleryPost.embeds[0].image.url}"
    await thread_owner.send(content=dm_message)
    await thread.edit(archived=True)

async def send_noqa_notification(thread: Thread, thread_owner: User, noqaPost: Message):

    message = f"### Hey {thread_owner.mention}!\nDue to inactivity, this sprite has been archived by a Zigzagoon or Sprite Manager. "\
              f"After a certain amount of time, it will be made available for other spriters to edit so it can be added to the game (you will still be credited) :ohyes:\n"\
              f"## If you would like to remove this sprite from the archive:\n- Ping `Zigzagoon (abandoned sprite poster)`"\
              f"or a sprite manager in this thread.\n- Let them know you would like the sprite removed from the archive.\n- You may "\
              f"continue working on this sprite (in this thread or a new thread), or you can chose to leave it abandoned."\
              f"\n*Make sure to remove the “Needs Feedback” tag on your spritework posts once you're done with your sprite* :happo: \n{noqaPost.embeds[0].image.url}"

    await thread.send(content = message)
    
    if is_user_zigzag_muted(thread.owner):
        return
    
    dm_message = f"Hey {thread_owner.mention}, due to inactivity this Pokemon Infinite Fusion sprite has been archived by "\
              f"a sprite manager or zigzagoon.\n"\
              f"If you have any questions or would like to remove the post, please ping a sprite manager in this thread: {thread.jump_url}.\n{noqaPost.embeds[0].image.url}"
    await thread_owner.send(content=dm_message)
    await thread.edit(archived=True)

def is_user_immune(user: Member):
    return is_user_post_immune(user) or is_user_harvest_immune(user)

def is_user_post_immune(user: Member):
    """Determines if a user has yanmega/posting immunity"""
    if user is None or type(user) == User:
        return False
    
    role_ids = [role.id for role in user.roles]
    if (POST_IMMUNITY_ID in role_ids):
        return True
    return False

def is_user_harvest_immune(user: Member):
    """Determines if a user has yanmega/posting immunity"""
    if user is None or type(user) == User:
        return False
    
    role_ids = [role.id for role in user.roles]
    if (HARVEST_IMMUNITY_ID in role_ids):
        return True
    return False

def is_user_zigzag_muted(user:Member):
    if user is None:
        return True
    
    role_ids = [role.id for role in user.roles]
    if (DM_IMMUNITY_ID in role_ids):
        return True
    return False


def _get_thread_pokemon_name(thread:Thread, image:Attachment):
    """
    Tries to extrapolate pokemon name 
    """
    # Plan A: check file name and, if it is formatted correctly, grab id from there
    non_numeric_id_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ !?@#$%^&*()[]-+="\\"/\n'

    try:
        head_num, body_num, png = image.filename.split(".")
        if fusion_is_valid(head_num) and fusion_is_valid(body_num):
            return [head_num.translate({ord(i): None for i in non_numeric_id_chars}),
                    body_num.translate({ord(i): None for i in non_numeric_id_chars})]
        
    except ValueError:
        pass

    # Plan B: check post title for numbers. We are assuming that the numbers in the post are separated by '.' (i.e 162.187)
    thread_title = thread.name

    non_numeric_id_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ !?@#$%^&*()[]-+="\\"/\n'
    number_pair = thread_title.translate({ord(i): None for i in non_numeric_id_chars}).split('.')

    if len(number_pair) == 2:
        if fusion_is_valid(number_pair[0]) and fusion_is_valid(number_pair[1]):
            return [number_pair[0], number_pair[1]]
    
    # Plan C: Check post title for Pokemon names. For my sanity, we're assuming it's seperated by a '/' for now (i.e Furret/Hoppip)
    pre_and_post_slash_list = [[clean_pokemon_string(word) for word in str.split(' ') if word != ''] for str in thread_title.split('/')]
    if len(pre_and_post_slash_list) == 2:
        pre_list, post_list = pre_and_post_slash_list

        # Grab first fusion name
        pre_id = raw_pokemon_name_to_id(pre_list[-1])
        if (pre_id is None) and (len(pre_list) > 1):
            # Try checking if this is a name seperated by a space
            pre_id = raw_pokemon_name_to_id(''.join([pre_list[-2], pre_list[-1]]))

        # Grab second fusion name
        post_id = raw_pokemon_name_to_id(post_list[0])
        if (post_id is None) and (len(post_list) > 1):
            # Try checking if this is a name seperated by a space
            post_id = raw_pokemon_name_to_id(''.join([post_list[0], post_list[1]]))

        if pre_id is not None and post_id is not None:
            return [pre_id, post_id]

    # Sad trombone noise
    return False

async def _get_candidate_info(thread:Thread, bot: Bot):
    """
    Finds the candidate image to post from a given thread.
    Returns none if there is no image found.
    """
    thread_author = await bot.fetch_user(thread.owner_id)
    image = None

    async for message in thread.history(oldest_first=False, limit=100):
        # Find last post from author with an image attachment
        if (len(message.attachments) != 0) and (message.author == thread_author):
            image = message.attachments[0]
            break
    
    if image is None:
        return [False, False]
    
    pokemon_ids = _get_thread_pokemon_name(thread, image)
    return image, pokemon_ids



async def find_gallery_image(thread: Thread, pokemon_ids:list, gallery_channel: TextChannel, bot:Bot):
    """
    Tries to find a sprite gallery post that matches a given thread.
    """
    thread_author = await bot.fetch_user(thread.owner_id)
    search_start_date = thread.created_at
    search_end_date = search_start_date + timedelta(weeks=5)

    ids_as_str = f"{pokemon_ids[0]}.{pokemon_ids[1]}"

    def thread_match(message:Message):
        if (message.author.id == thread_author.id):
            if (ids_as_str in str(message.content)):
                return True
        return False
    
    await fill_gallery_cache(gallery_channel, search_start_date, search_end_date)

    msg = discord.utils.find(lambda m: thread_match(m),
                                 cached_gal_list)
    
    if msg is None:
        return False
    return msg

async def fill_gallery_cache(gallery_channel: TextChannel, start:datetime, end: datetime):
    """
    Determines if cache is filled with all posts between start date and end date, and if not adds them in.
    """
    global cached_gal_list
    global cache_start_date
    global cache_end_date

    print("Cache start:{} Requested Start:{}".format(cache_start_date, start))
    print("Cache end:{} Requested end:{}".format(cache_end_date, end))

    if cached_gal_list == []:
        cached_gal_list = [message async for message in gallery_channel.history(after=start, before=end, oldest_first=True, limit=None)]
        cache_start_date = start
        cache_end_date = end
        return

    if cache_start_date > start:
        print("Adding start")
        added_entries = [message async for message in gallery_channel.history(after=start, before=cache_start_date, oldest_first=True, limit=None)]
        cache_start_date = start
        cached_gal_list.extend(added_entries)
    
    if cache_end_date < end:
        print("Adding end")
        added_entries = [message async for message in gallery_channel.history(after=cache_end_date, before=end, oldest_first=True, limit=None)]
        cache_end_date = end
        cached_gal_list.extend(added_entries)
    
    return

def _pretty_formatted_message(thread: Thread, 
                            candidate_image:Attachment,
                            canidate_ids:list,
                            gallery_post:Message,
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
    if candidate_image is False:
        candidate_info = "No candidate image found"
    elif canidate_ids is False:
        candidate_info = "Candidate image: {}\n Unable to Identify Fusion\n".format(candidate_image)
    else:
        fusion_names = [id_to_name_map()[id] for id in canidate_ids]
        candidate_info = "Fusion Identified: \n## {}/{} ({}.{})\n Candidate image: {}\n".format(fusion_names[0],
                                                                                        fusion_names[1],
                                                                                        canidate_ids[0],
                                                                                        canidate_ids[1],
                                                                                        candidate_image)

    # Format gallery section
    if gallery_post:
        if len(gallery_post.attachments) != 0:
            gallery_info = "Gallery post found: {} Image: {}\n".format(gallery_post.jump_url, gallery_post.attachments[0].url)
        else:
            gallery_info = "Gallery post found: {} **Image not attached**\n".format(gallery_post.jump_url)
    else:
        gallery_info = "No matching sprite gallery post found automatically\n"
        if canidate_ids is False:
            gallery_info = ""

    full_message = "~~~~~~~~~~~~~~\n"+header+activity+candidate_info+gallery_info

    if is_user_immune(thread.owner):
        full_message += "\n *User Has Posting Immunity*"
    return full_message

async def _manually_post_to_channel(location: str, ctx: Context, args:list, bot:Bot):

    # Parse args and ensure they are correct
    arg_results = await _parse_channelpost_args(args)
    if arg_results is None:
        usage_message = "Usage (must be in reply to a message): `PicNum[Optional] Head/Body message[optional]`\nFusions can be names or id numbers"
        await ctx.send(usage_message, delete_after=10, ephemeral=True)
        await ctx.message.delete(delay=2)
        return
    img_num, fusion_list, message = arg_results

    # Check that we replied to a real post
    replied_post_reference = ctx.message.reference
    if replied_post_reference is None:
        error_message = "Please reply to a message that has an image to post"
        await ctx.send(error_message, ephemeral=True, delete_after=6)
        await ctx.message.delete(delay=2)
        return

    msg = await ctx.channel.fetch_message(replied_post_reference.message_id)

    # Make sure there is an attachment on the message
    attachments = msg.attachments
    if len(attachments) <= img_num-1:
        error_message = "Message attachment out of range"
        await ctx.send(error_message, ephemeral=True, delete_after=6)
        await ctx.message.delete(delay=2)
        return
    
    await check_and_load_cache(bot)

    image = msg.attachments[img_num-1]

    
    # If the user is not the author of the post, warn the user
    sprite_author = msg.author
    is_og_author = True

    if (msg.channel.owner != msg.author) and (msg.channel.owner != None):
        warning_message = "*This image is not from the post author.* Post will be credited to original author."
        await ctx.send(warning_message, ephemeral=True, delete_after=10)
        is_og_author = False
        sprite_author = msg.channel.owner
        
    if location == "gallery":
        # Check for posting immunity. Check message and thread author if they are different people
        if is_user_post_immune(msg.author):
            await ctx.send("User is immune to automated sprite posting", delete_after=20)
            await ctx.message.delete(delay=2)
            return
        if not is_og_author:
            if is_user_post_immune(sprite_author):
                await ctx.send("Message author is immune to automated sprite posting", delete_after=20)
                await ctx.message.delete(delay=2)
                return

        post = await post_to_channel(sprite_channels["gallery"], fusion_list, image, sprite_author, footer_message=GALLERY_FOOTER, message=message)
        await ctx.message.delete(delay=2)
        await clean_tags(ctx.channel, spritepost_tags["gallery"])
        await send_galpost_notification(ctx.channel, sprite_author, post)


    elif location == "noqa":
        # Check for harvest immunity. Check message and thread author if they are different people
        if is_user_harvest_immune(msg.author):
            await ctx.send("User is immune to automated sprite harvesting", delete_after=20)
            await ctx.message.delete(delay=2)
            return
        if not is_og_author:
            if is_user_harvest_immune(sprite_author):
                await ctx.send("Message author is immune to automated sprite harvesting", delete_after=20)
                await ctx.message.delete(delay=2)
                return
        
        footer_message = ""
        post = await post_to_channel(sprite_channels["noqa"], fusion_list, image, sprite_author, footer_message=footer_message, message=message)
        await ctx.message.delete(delay=2)
        await clean_tags(ctx.channel, spritepost_tags["harvested"])
        await send_noqa_notification(ctx.channel, sprite_author, post)

    await ctx.message.delete(delay=2)


async def _parse_channelpost_args(args:list):
    """
    Parses args for galpost and noqa commands

    Takes in the arg list

    Returns:
        List of 
        None if there was an error
    """
    pic_num = 1 # Indexing starts at 1
    fusion_lst = None
    message = None

    if len(args) == 0:
        return None

    if len(args) == 1:
        fusions = args[0].split('/')
        if len(fusions) != 2:
            return None
        
        fusion_lst = clean_names_or_ids(fusions)
        if fusion_lst is None:
            return None
        
    if len(args) >= 2:
        # This could be 'imgNum Head/Body' or 'imgNum Head/Body message'
        if args[0].isdigit():
            pic_num = int(args[0])
            
            fusions = args[1].split('/')
            if len(fusions) != 2:
                return None

            fusion_lst = clean_names_or_ids(fusions)
            if fusion_lst is None:
                return None
            
            if len(args) > 2:
                message = ' '.join(args[2:])
        
        # 'Head/Body message'
        elif '/' in args[0]:
            fusions = args[0].split('/')
            fusion_lst = clean_names_or_ids(fusions)
            if fusion_lst is None:
                return None
            
            message = ' '.join(args[1:])
        
        else:
            return None

    return [pic_num, fusion_lst, message]


def clean_names_or_ids(fusions):
    """
    Take a list of two fusion names OR ids and returns a string with both fusion ids

    Args: list of fusion head and body
    """
    # Parse head/fusion id or name
    headid = raw_pokemon_name_to_id(fusions[0])
    bodyid = raw_pokemon_name_to_id(fusions[1])


    if headid is None:
        if fusion_is_valid(fusions[0]):
            headid = fusions[0]
    if bodyid is None:
        if fusion_is_valid(fusions[1]):
            bodyid = fusions[1]

    if headid is None or bodyid is None:
        print("One is none: Head:{} Body:{} Raw:{}".format(headid, bodyid, fusions))
        return None
    
    fusion_lst = [headid, bodyid]
    return fusion_lst