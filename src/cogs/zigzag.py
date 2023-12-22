from datetime import timedelta
import io
import json
import time

from discord.ext.commands import Bot, Cog, Context, command, has_role
from discord import ForumTag, Thread, Attachment, Message, ui
import discord
from discord.channel import TextChannel

from cogs.utils import clean_pokemon_string, raw_pokemon_name_to_id, id_to_name_map

# Defining configs and hard-coded vals
SPRITEWORK_CHANNEL_ID = 1185685268133593118
SPRITEGALLERY_CHANNEL_ID = 1185991301645209610
NOQA_CHANNEL_ID = 1187874415090868224

NEEDSFEEDBACK_TAG_ID = 1185685810960420874
ADDEDTOGAL_TAG_ID = 1185685841973084310
HARVESTED_TAG_ID = 1185685876978753657
NONIF_TAG_ID = 1186024872695042048


MAX_LOOKAHEAD_THEAD_TIME = 21 # Ammount of time, in days, that we will check in the gallery after time of spritework post, 

spritepost_tags = {}
sprite_channels = {}

class ZigZag(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @command(name="tagids")
    async def tagids(self, ctx: Context):
        """Debug command to get tag ids for the thannel"""
        spritework_channel= self.bot.get_channel(SPRITEWORK_CHANNEL_ID)
        print(spritework_channel.available_tags)


    @command(name="oldest", pass_context=True)
    async def oldest(self, ctx: Context):
        """Find the oldest threads with a given tag."""

        # Fill cache with channels and tags
        if sprite_channels == {}:
            sprite_channels["spritework"] = self.bot.get_channel(SPRITEWORK_CHANNEL_ID) # SpritePost channel ID
            sprite_channels["gallery"] = self.bot.get_channel(SPRITEGALLERY_CHANNEL_ID) # SpritePost channel ID
            sprite_channels["noqa"] = self.bot.get_channel(NOQA_CHANNEL_ID) # SpritePost channel ID

        if spritepost_tags == {}:
            spritework_channel = sprite_channels["spritework"]
            spritepost_tags["feedback"] = spritework_channel.get_tag(NEEDSFEEDBACK_TAG_ID) # "Needs Feedback" tag ID
            spritepost_tags["gallery"]  = spritework_channel.get_tag(ADDEDTOGAL_TAG_ID) # "Needs Feedback" tag ID
            spritepost_tags["harvested"]  = spritework_channel.get_tag(HARVESTED_TAG_ID) # "Needs Feedback" tag ID
            spritepost_tags["non-if"]  = spritework_channel.get_tag(NONIF_TAG_ID) # "Needs Feedback" tag ID


        target_tag = spritepost_tags["feedback"]
        archived_threads = sprite_channels["spritework"].archived_threads(limit=10) #TODO: Only search BEFORE cached date
        await ctx.send("Digging for threads. This may take a few minutes. Wait for 'complete' message at end. \n --- ⛏⛏⛏⛏⛏⛏⛏ --- ")

        async for thread in archived_threads:
            if target_tag in thread.applied_tags:
                start = time.time()
                candidate_image, canidate_ids, gal_post = await scrape_thread_and_gallery(thread, sprite_channels["gallery"])
                archive_time = time.time() - start; print(f"Scraping Time: {archive_time}")

                start = time.time()
                message = _pretty_formatted_message(thread, candidate_image, canidate_ids, gal_post)
                archive_time = time.time() - start; print(f"Message Time: {archive_time}")

                selectView = PostOptionsView(thread, canidate_ids, candidate_image)
                await ctx.send(message, view=selectView)

        await ctx.send("Digging Complete!")
        
    
async def setup(bot:Bot):
    await bot.add_cog(ZigZag(bot))

class PostOptions(ui.Select):
    """
    Options available if the fusion was able to be identified
    """
    def __init__(self, thread: Thread, fusion:list, image:Attachment):

        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(label='Post', description='Post the candidate image to sprite gallery', emoji='📮'),
            discord.SelectOption(label='Harvest', description='Post candidate image to noqa', emoji='🖌'),
            discord.SelectOption(label='Clean', description='Remove Needs Feedback tag adds Added to Gallery tag', emoji='🧺'),
            discord.SelectOption(label='Manual', description="Don't do anything", emoji='🧀'),
        ]

        self.thread = thread
        self.fusion = fusion
        self.image = image

        super().__init__(placeholder='Choose action...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # await interaction.message.edit(content = f'You chose action {self.values[0]}')

        choice = self.values[0]
        if choice == 'Post':
            gal_tag = spritepost_tags["gallery"]
            await clean_tags(self.thread, gal_tag)

            post = await post_to_channel(sprite_channels["gallery"], self.fusion, self.image, self.thread.owner.name)
            await send_galpost_notification(self.thread, post)
            message = "{} posted sprite from thread {} here: {}".format(interaction.user, self.thread.jump_url, self.thread)

        elif choice == 'Harvest':
            harvested_tag = spritepost_tags["harvested"]
            await clean_tags(self.thread, harvested_tag)

            post = await post_to_channel(sprite_channels["noqa"], self.fusion, self.image, self.thread.owner.name)
            await send_noqa_notification(self.thread, post)
            message = "{}: Harvested thread {} here:".format(interaction.user, self.thread.jump_url, self.thread)
            pass

        elif choice == 'Clean':
            gal_tag = spritepost_tags["gallery"]
            await clean_tags(self.thread, gal_tag)
            message = "{}: Marked {} as already added to gallery".format(interaction.user, self.thread.jump_url)

        elif choice == 'Manual':
            message = "{}: manually handling {}".format(interaction.user, self.thread.jump_url)

        else:
            message = "How did you do this????"

        await interaction.message.edit(content = message, delete_after=60*5, embed=None)
        # await interaction.response.send_message(f'You chose action {self.values[0]}')


class UnidentifiedOptions(ui.Select):
    def __init__(self, thread: Thread):

        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(label='Clean', description='Remove Needs Feedback tag and add Other tag', emoji='🧺'),
            discord.SelectOption(label='Manual', description="Don't do anything", emoji='🧀'),
        ]
        self.thread = thread
        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder='Choose action...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.edit(content = f'You chose action {self.values[0]}')
        await interaction.response.send_message(f'You chose action {self.values[0]}')



class PostOptionsView(discord.ui.View):
    def __init__(self, thread: Thread, fusion: list, image: Attachment):
        """
        
        Args:
            - thread (Thread): candidate thread
            - fusion (list): list containing the fusion ids, in format [headid, bodyid]
            - image (Attachment): candidate image to post or harvest
        """
        super().__init__()

        # Adds the dropdown to our view object.
        
        if fusion is False:
            self.add_item(UnidentifiedOptions(thread))
        else:
            self.add_item(PostOptions(thread, fusion, image))
            



async def scrape_thread_and_gallery(thread: Thread, gallery_channel: TextChannel):
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
    candidate_image, candidate_ids = await _get_candidate_info(thread)


    if candidate_image is False:
        # No image found in post
        return [False, False, False]
    
    if candidate_ids is False:
        # Can't identify pokemon in post
        return [candidate_image, False, False]
    
    gallery_post = await _find_gallery_image(thread, candidate_ids, gallery_channel)
    return [candidate_image, candidate_ids, gallery_post]


async def clean_tags(thread:Thread, remaining_tag: ForumTag):
    """Removes Needs Feedback tag and adds the remaing_tag"""
    # Discords api is weird, so we have to unarchive to edit it, and then rearchive the thread
    await thread.edit(archived=False, applied_tags=[remaining_tag])
    await thread.edit(archived=True)


async def post_to_channel(channel: TextChannel, fusion:list, image: Attachment, author:str):
    """
    Posts a given image to the given channel

        channel ()
    """
    filename = f"{fusion[0]}.{fusion[1]}.png"
    image_bytes = await image.read()
    bytes_io_file = io.BytesIO(image_bytes)

    fusion_names = [id_to_name_map()[id] for id in fusion]
    message = "From: {}\n{}/{} ({}.{})".format(author,
                                              fusion_names[0],
                                              fusion_names[1],
                                              fusion[0],
                                              fusion[1])
    
    upload_image = discord.File(fp = bytes_io_file, filename= filename)
    
    post = await channel.send(content=message, file=upload_image)
    return post


async def send_galpost_notification(thread: Thread, galleryPost: Message):
    author = thread.owner
    message = f"Hey {author.mention}, this sprite has been posted to the sprite gallery by "\
              f"a sprite manager or zigzagoon. You can see the gallery post here: {galleryPost.jump_url}\n"\
              f"If you have any questions or would like to remove the post, please ping a sprite manager in this thread.\n{galleryPost.attachments[0]}"
    
    await thread.send(content = message)

async def send_noqa_notification(thread: Thread, noqaPost: Message):
    author = thread.owner
    message = f"Hey {author.mention}, due to inactivity this sprite has been archived by "\
              f"a sprite manager or zigzagoon.\n"\
              f"If you have any questions or would like to remove the post, please ping a sprite manager in this thread.\n{noqaPost.attachments[0]}"
    
    await thread.send(content = message)


def _get_thread_pokemon_name(thread:Thread, image:Attachment):
    """
    Tries to extrapolate pokemon name 
    """
    # Plan A: check file name and, if it is formatted correctly, grab id from there
    non_numeric_id_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ !?@#$%^&*()[]-+="\\"/\n'

    try:
        head_num, body_num, png = image.filename.split(".")
        return [head_num.translate({ord(i): None for i in non_numeric_id_chars}), body_num.translate({ord(i): None for i in non_numeric_id_chars})]
    except ValueError:
        pass

    # Plan B: check post title for numbers. We are assuming that the numbers in the post are separated by '.' (i.e 162.187)
    thread_title = thread.name

    non_numeric_id_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ !?@#$%^&*()[]-+="\\"/\n'
    number_pair = thread_title.translate({ord(i): None for i in non_numeric_id_chars}).split('.')

    if len(number_pair) == 2:
        return [number_pair[0], number_pair[1]]
    
    # Plan C: Check post title for Pokemon names. For my sanity, we're assuming it's seperated by a '/' for now (i.e Furret/Hoppip)
    pre_and_post_slash_list = [[clean_pokemon_string(word) for word in str.split(' ') if word != ''] for str in thread_title.split('/')]
    if len(pre_and_post_slash_list) == 2:
        pre_list, post_list = pre_and_post_slash_list

        # Grab first fusion name
        pre_id = raw_pokemon_name_to_id(pre_list[-1])
        if (pre_id == None) and (len(pre_list) > 1):
            # Try checking if this is a name seperated by a space
            pre_id = raw_pokemon_name_to_id(''.join([pre_list[-2], pre_list[-1]]))

        # Grab second fusion name
        post_id = raw_pokemon_name_to_id(post_list[0])
        if (post_id == None) and (len(post_list) > 1):
            # Try checking if this is a name seperated by a space
            post_id = raw_pokemon_name_to_id(''.join([post_list[0], post_list[1]]))

        if pre_id != None and post_id != None:
            return [pre_id, post_id]

    # Sad trombone noise
    return False

async def _get_candidate_info(thread:Thread):
    """
    Finds the candidate image to post from a given thread.
    Returns none if there is no image found.
    """
    thread_author = thread.owner
    image = None

    async for message in thread.history(oldest_first=True, limit=100):
        # Find last post from autho with an image attachment
        if (len(message.attachments) != 0) and (message.author == thread_author):
            image = message.attachments[0]
            break
    
    if image is None:
        return False
    
    pokemon_ids = _get_thread_pokemon_name(thread, image)
    return image, pokemon_ids



async def _find_gallery_image(thread: Thread, pokemon_ids:list, gallery_channel: TextChannel):
    """
    Tries to find a sprite gallery post that matches a given thread.
    """
    thread_author = thread.owner
    search_start_date = thread.created_at
    search_end_date= search_start_date + timedelta(MAX_LOOKAHEAD_THEAD_TIME)

    # authors_posts = await discord.utils.get(
    #                     gallery_channel.history(after=search_start_date, before=search_end_date),
    #                     author__id=thread_author.id)
    ids_as_str = f"{pokemon_ids[0]}.{pokemon_ids[1]}"

    async for post in gallery_channel.history(after=search_start_date, before=search_end_date, oldest_first=True):
        if post.author.id == thread_author.id:
            if ids_as_str in str(post.content) :
                return post
    return False
    # [post for post in authors_posts if ]


def _pretty_formatted_message(thread: Thread, 
                            candidate_image:Attachment,
                            canidate_ids:list,
                            gallery_post:Message):
    """Formats output message"""
    
    header =   'Thread: {} by {}\n'.format(thread.jump_url, thread.owner.name)
    activity = 'Created {}. Last active {}.\n\n'.format(thread.created_at.strftime("%m/%d/%Y"), thread.last_message)

    # Format candidate section

    if candidate_image is False:
        candidate_info = "No candidate image found"
    elif canidate_ids is False:
        candidate_info = "Candidate image: {}\n Unable to Identify Fusion\n".format(candidate_image)
    else:
        fusion_names = [id_to_name_map()[id] for id in canidate_ids]
        candidate_info = "Candidate image: {} Fusion Identified: {}/{} ({}.{})\n".format(candidate_image, 
                                                                                        fusion_names[0],
                                                                                        fusion_names[1],
                                                                                        canidate_ids[0],
                                                                                        canidate_ids[1])

    # Format gallery section
    if gallery_post:
        gallery_info = "Gallery post found: {} Image: {}\n".format(gallery_post.jump_url, gallery_post.attachments[0].url)
    else:
        gallery_info = "No matching sprite gallery post found\n"
        if canidate_ids is False:
            gallery_info = ""

    return "~~~~~~~~~~~~~~\n"+header+activity+candidate_info+gallery_info