import asyncio
import os
from discord.ext.commands import Bot, Cog, Context, has_any_role, hybrid_command
from discord import Message, Thread, User, utils, Member
import discord

from cogs.utils import is_former_spriter, update_former_spriter_cache

FORMER_SPRITER_ROLE_ID = None

FILEPACK_DIR = "datadir/"

ROLES_TO_RM_IDS = []
ROLES_TO_RM = []
FORMER_SPRITER_RESTRICTED_CHANNEL_IDS = []

class Eraser(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        load_env_vars(bot.env)

    @has_any_role("Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="make-former-spriter", pass_context=True,
                help ="Adds a spriter to the former spriter tracker and updates their roles",
                brief = "Makes former spriter")
    async def former_spriter(self, ctx: Context, name: User = None):
        former_spriter = ctx.guild.get_member(name.id)
        
        global ROLES_TO_RM
        if ROLES_TO_RM == []:
            for id in ROLES_TO_RM_IDS:
                role = utils.get(ctx.guild.roles,id=int(id))
                ROLES_TO_RM.append(role)

        former_spriters_fd = open(os.path.join(FILEPACK_DIR, "former-spriters.txt"), "a")
        former_spriters_fd.write(f"{former_spriter.id}\n")
        former_spriters_fd.close()

        update_former_spriter_cache()

        await former_spriter.remove_roles(*ROLES_TO_RM)
        await former_spriter.add_roles(utils.get(ctx.guild.roles,id=int(FORMER_SPRITER_ROLE_ID)))

        await ctx.message.delete(delay=2)
        await ctx.send(f"Made {former_spriter.name} a former spriter.")
        return
    
    @has_any_role("Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="undo-former-spriter", pass_context=True,
                help ="[DEBUGGING] Removes former spriter. Useful for testing and debugging",
                brief = "(Debugging) removed former spriter")
    async def undo_former_spriter(self, ctx: Context, name: User = None):
        former_spriter = ctx.guild.get_member(name.id)
        
        with open(os.path.join(FILEPACK_DIR, "former-spriters.txt"), "r+") as fd:
            new_names_list = [line for line in fd.readlines() if line.rstrip() != str(former_spriter.id)]
            new_names = "".join(new_names_list)
            
            fd.seek(0)
            fd.write(new_names)
            fd.truncate()

        update_former_spriter_cache()

        await former_spriter.remove_roles(utils.get(ctx.guild.roles,id=int(FORMER_SPRITER_ROLE_ID)))

        await ctx.message.delete(delay=2)
        await ctx.send(f"Undid {former_spriter.name}'s former spriter status")
        return
    
    @has_any_role("Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="make-former-spriter-by-id", pass_context=True,
                help ="[DEBUGGING] Removes former spriter. Useful for testing and debugging",
                brief = "(Debugging) removed former spriter")
    async def former_spriter_by_id(self, ctx: Context, id: str):
        
        former_spriters_fd = open(os.path.join(FILEPACK_DIR, "former-spriters.txt"), "a")
        former_spriters_fd.write(f"{id}\n")
        former_spriters_fd.close()

        await ctx.message.delete(delay=2)
        await ctx.send(f"Made user with id {id} a former spriter")
        return
    

    @Cog.listener()
    async def on_member_join(self, member: Member):
        """
        Listen for if a former spriter re-joins
        """
        await asyncio.sleep(2) # We run into an error sometimes if we read or send the message too fast after thread was created

        if is_former_spriter(member):
            await member.add_roles(member.guild.get_role(FORMER_SPRITER_ROLE_ID))
            zigzag_chat_channel = self.bot.get_channel(ZIGZAG_CHATTER_CHANNEL_ID)
            message = f"{member.mention} has rejoined the server.\n\nThis user is flagged as a former spriter and may need to former spriter role re-added to them."
            await zigzag_chat_channel.send(content=message)

    @Cog.listener()
    async def on_message(self, message: Message):
        if is_former_spriter(message.author):
            if message.channel.id in FORMER_SPRITER_RESTRICTED_CHANNEL_IDS:
                await message.delete()
                reply = f"Hey {message.author.mention}, looks like you are a withdrawn artist and therefore you cannot"\
                        "send messages in this restricted channel. If you believe this is an error, please contact a sprite manager"
                await message.channel.send(reply, delete_after=30)


    # @Cog.listener()
    # async def on_thread_create(self, thread: Thread):
    #     """
    #     Listen for an error thread to be created, and react depending on the content in the thread
    #     """
    #     await asyncio.sleep(2) # We run into an error sometimes if we read or send the message too fast after thread was created

    #     if thread.parent_id == SPRITE_APP_CHANNEL_ID:
            
    #         if is_former_spriter(thread.owner):
    #             await check_and_load_cache(self.bot)
    #             message = f"Hello {thread.owner.mention}\n\n It appears you have the `Former Spriter` role, which mean you are ineligible to apply for the spriter role and this application will be marked as abandoned.\n\n"\
    #                       f"If you believe this is a mistake, please contact a sprite manager."

    #             await thread.edit(archived=False, applied_tags=[tags["abandoned"]])
    #             await thread.send(content = message)
    #             return

    #         applicant_role = utils.get(thread.guild.roles,id=SPRITER_APPLICANT_ID)
    #         await thread.owner.add_roles(applicant_role)

    #         message = f"Welcome {thread.owner.mention}!\n\n## Please post three fusion sprites you've made here if you haven't already! <:smilemeowth:763742948860887050> Please also "\
    #                   f"*link your Spritework posts* for each of those sprites! And only post 3 sprites please, not more.\n\n"\
    #                   f"A Sprite Manager will come evaluate them as soon as possible! This may take a few hours or days since"\
    #                   f" there are usually dozens of open applications at the same time. Please be patient! In the meantime, spriters may come give you feedback too!\n\n"\
    #                   f"Feel free to ask any questions you have as well!"
        
    #         await thread.send(content = message)


def load_env_vars(env: str):

    is_dev = env == "dev"

    global ROLES_TO_RM_IDS
    role_ids = os.environ.get("DEV_ROLES_TO_RM") if is_dev else os.environ.get("ROLES_TO_RM")
    ROLES_TO_RM_IDS = [role.strip() for role in role_ids.split(',')]

    global FORMER_SPRITER_ROLE_ID
    FORMER_SPRITER_ROLE_ID = os.environ.get("DEV_FORMER_SPRITER_ROLE_ID") if is_dev else os.environ.get("FORMER_SPRITER_ROLE_ID")
    FORMER_SPRITER_ROLE_ID = int(FORMER_SPRITER_ROLE_ID)

    global ZIGZAG_CHATTER_CHANNEL_ID
    ZIGZAG_CHATTER_CHANNEL_ID = os.environ.get("DEV_ZIGZAG_CHATTER_CHANNEL_ID") if is_dev else os.environ.get("ZIGZAG_CHATTER_CHANNEL_ID")
    ZIGZAG_CHATTER_CHANNEL_ID = int(ZIGZAG_CHATTER_CHANNEL_ID)

    global FORMER_SPRITER_RESTRICTED_CHANNEL_IDS
    channel_ids = os.environ.get("DEV_FORMER_SPRITER_RESTRICTED_CHANNELS") if is_dev else os.environ.get("FORMER_SPRITER_RESTRICTED_CHANNELS")
    FORMER_SPRITER_RESTRICTED_CHANNEL_IDS = [int(channel.strip()) for channel in channel_ids.split(',')]


async def setup(bot:Bot):
    await bot.add_cog(Eraser(bot))
