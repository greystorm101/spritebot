from datetime import timedelta
import json

from discord.ext.commands import Bot
from discord import Thread, Attachment, Message
import discord
from discord.channel import TextChannel



# Defining configs and hard-coded vals
SPRITEWORK_CHANNEL_ID = 1185685268133593118
SPRITEGALLERY_CHANNEL_ID = 1185991301645209610
NEEDSFEEDBACK_TAG_ID = 1185685810960420874

MAX_LOOKAHEAD_THEAD_TIME = 21 # Ammount of time, in days, that we will check in the gallery after time of spritework post, 

async def find_old_threads(ctx, bot: Bot):
    """Find the oldest threads with a given tag."""
    spritework_channel= bot.get_channel(SPRITEWORK_CHANNEL_ID) # SpritePost channel ID
    gallery_channel = bot.get_channel(SPRITEGALLERY_CHANNEL_ID) # SpritePost channel ID
    target_tag = spritework_channel.get_tag(NEEDSFEEDBACK_TAG_ID) # "Needs Feedback" tag ID

    archived_threads = spritework_channel.archived_threads(limit=10) #TODO: Only search BEFORE cached date
    
    
    await ctx.send("Digging for threads. This may take a few minutes. Wait for 'complete' message at end. \n --- ⛏⛏⛏⛏⛏⛏⛏ --- ")

    async for thread in archived_threads:
        if target_tag in thread.applied_tags:

            candidate_image, canidate_id, gal_post = await scrape_thread_and_gallery(thread, gallery_channel)
            message = _pretty_formatted_message(thread, candidate_image, canidate_id, gal_post)
            await ctx.send(message)

    await ctx.send("Digging Complete!")
    

async def scrape_thread_and_gallery(thread: Thread, gallery_channel: TextChannel):
    """
    Takes a spritework thread and determines if the thread has
    been posted in sprite gallery

    Returns:
        List with three elements: [Candidate_image, candidate_id, gallery_post]
        Candidate_image: attachment of latest image from thread poster. False if no 
                         candidate image was found
        Candidate_id: Id of fusion in format xxx.xxx. False if bot was unable to identify
                      the fusion in the post
        gallery_post: Link to gallery post of fusion if it was able to be found. False if
                      no matching post was found.
    """
    candidate_image, candidate_id = await _get_candidate_info(thread)

    if candidate_image is False:
        # No image found in post
        return [False, False, False]
    
    if candidate_id is False:
        # Can't identify pokemon in post
        return [candidate_image, False, False]
    
    gallery_post = await _find_gallery_image(thread, candidate_id, gallery_channel)
    return [candidate_image, candidate_id, gallery_post]


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
    
    pokemon_id = _get_thread_pokemon_name(thread, image)
    return image, pokemon_id

def _get_thread_pokemon_name(thread:Thread, image:Attachment):
    """
    Tries to extrapolate pokemon name 
    """
    # Plan A: check file name and, if it is formatted correctly, grab id from there
    try:
        head_num, body_num, png = image.filename.split(".")
        return "{}.{}".format(head_num, body_num)
    except ValueError:
        pass

    # Plan B: check post title for numbers. We are assuming that the numbers in the post are separated by '.' (i.e 162.187)
    thread_title = thread.name

    non_numeric_id_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ !?@#$%^&*()-+="\\"/\n'
    number_pair = thread_title.translate({ord(i): None for i in non_numeric_id_chars}).split('.')

    if len(number_pair) == 2:
        return "{}.{}".format(number_pair[0], number_pair[1])
    
    # Plan C: Check post title for Pokemon names. For my sanity, we're assuming it's seperated by a '/' for now (i.e Furret/Hoppip)


    # Sad trombone noise
    return False

async def _find_gallery_image(thread: Thread, pokemon_id:str, gallery_channel: TextChannel):
    """
    Tries to find a sprite gallery post that matches a given thread.
    """
    thread_author = thread.owner
    search_start_date = thread.created_at
    search_end_date= search_start_date + timedelta(MAX_LOOKAHEAD_THEAD_TIME)

    # authors_posts = await discord.utils.get(
    #                     gallery_channel.history(after=search_start_date, before=search_end_date),
    #                     author__id=thread_author.id)

    async for post in gallery_channel.history(after=search_start_date, before=search_end_date, oldest_first=True):
        if post.author.id == thread_author.id:
            if pokemon_id in str(post.content) :
                return post
    return False
    # [post for post in authors_posts if ]


def _pretty_formatted_message(thread: Thread, 
                              candidate_image:Attachment,
                              canidate_id:str,
                              gallery_post:Message):
    """Formats output message"""
    
    header =   'Thread: {} by {}\n'.format(thread.jump_url, thread.owner.name)
    activity = 'Created {}. Last active {}.\n'.format(thread.created_at.strftime("%m/%d/%Y"), thread.last_message)

    # Format candidate section
    if candidate_image is False:
        candidate_info = "No candidate image found"
    elif canidate_id is False:
        candidate_info = "Candidate image: {}\n".format(candidate_image)
    else:
        candidate_info = "Candidate image: {} Fusion Identified: {}\n".format(candidate_image, canidate_id)

    # Format gallery section
    if gallery_post:
        gallery_info = "Gallery post found: {} Image: {}\n".format(gallery_post.jump_url, gallery_post.attachments[0].url)
    else:
        gallery_info = "No matching sprite gallery post found\n"

    return "~~~~~~~~~~~~~~\n"+header+activity+candidate_info+gallery_info