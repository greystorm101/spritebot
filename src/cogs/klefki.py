import asyncio
import os
from typing import List
from discord.ext.commands import Bot, Cog, Context, has_any_role, hybrid_command
from discord import Thread, User, utils, app_commands
import discord

SPRITER_APPLICANT_ID=0
SPRITER_ID=0
SPRITE_APP_CHANNEL_ID=0
APPLICANT_ABANDONED_ID=0
APPLICANT_ROLE_GIVEN_ID=0

deny_reasons = {"alt": "One or more of sprites do not follow the criteria for a conventional head/body fusion. Please reapply with three sprites that meet the fusion requirements in https://discord.com/channels/302153478556352513/873571372981452830/909608552639897660",
              "similar sprites": "Your sprites are **too similar**, which makes it difficult for the managers to evaluate your spriting skills! Please reapply "\
                                 "with a trio of sprites that are more varied, such as using three **different Pokémon** for the heads of the 3 sprites.",
              "not three": "You did not submit **three sprites**. You either submitted too many or too few sprites. Please reapply once you have three sprites ready to post",
                "self fusion": "One or more of your sprites is a **self-fusion** ( a Pokémon fused with itself), which are not accepted for spriter application due to "\
                              "how different their designs usually are. They're difficult to evaluate. Please reapply once you have three sprites that aren't self fusions!",
              "guidelines": "Your sprites do not follow the  <#873571372981452830>. Please reapply after you have re-read through the guidelines and made 3 unique sprites that follow them.",
              "inactivity": "Due to inactivity, this application will be closed. Feel free to open another application in the future.",
              "feedback": "Applicants are evaluated not only for their sprite quality, but also on their ability to properly take and act on feedback. You may re-apply once you are able to demonstrate taking feedback on your sprites",
              "missing spritework": "Your sprites have not gone through ⁠<#1050404143807873157> before applying for spriter. You may re-apply once you create posts for your sprites.",
              "24 hours": "The ⁠<#1050404143807873157> thread for one or more of your sprites was opened too recently (less that 24 hours ago). In order to ensure quality, it's best for an applicant to leave their sprites open for feedback "\
                           "for at least 24 hours before applying for the role. That way, more people can see your work and give you feedback. If you have not gotten feedback on your sprites and would like some, you can use the /feedbackpls "\
                           "command and the <#882011946801569802> channel to get more eyes on your work. Feel free to reapply once all three of your sprites have been on the gallery for 24 hours or more."}

deny_names = [*deny_reasons.keys()]

async def deny_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    choices = [app_commands.Choice(name=choice, value=choice) for choice in deny_names if current.lower() in choice][:25]
    return choices

class Klefki(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        load_env_vars(bot.env)

    @Cog.listener()
    async def on_thread_create(self, thread: Thread):
        """
        Listen for an error thread to be created, and react depending on the content in the thread
        """
        await asyncio.sleep(2) # We run into an error sometimes if we read or send the message too fast after thread was created

        if thread.parent_id == SPRITE_APP_CHANNEL_ID:
            
            applicant_role = utils.get(thread.guild.roles,id=SPRITER_APPLICANT_ID)
            await thread.owner.add_roles(applicant_role)

            message = f"Welcome {thread.owner.mention}!\n\n## Please post three fusion sprites you've made here if you haven't already! <:smilemeowth:763742948860887050> Please also "\
                      f"*link your Spritework posts* for each of those sprites! And only post 3 sprites please, not more.\n\n"\
                      f"A Sprite Manager will come evaluate them as soon as possible! This may take a few hours or days since"\
                      f" there are usually dozens of open applications at the same time. Please be patient! In the meantime, spriters may come give you feedback too!\n\n"\
                      f"Feel free to ask any questions you have as well!"
        
            await thread.send(content = message)


    @has_any_role("Klefki (Spriter role giver)", "Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="appapp", pass_context=True,
                help ="[KLEFKI] Grants spriter role, removes applicant role, sends a message",
                brief = " Grants the spriter role and gives info")
    async def appaccept(self, ctx: Context, name: User, more_work_needed: bool = False):
        selected_user = ctx.guild.get_member(name.id)

        applicant_role = utils.get(ctx.guild.roles,id=SPRITER_APPLICANT_ID)
        spriter_role = utils.get(ctx.guild.roles,id=SPRITER_ID)
        
        await selected_user.add_roles(spriter_role)
        await selected_user.remove_roles(applicant_role)
        await ctx.channel.edit(archived=False, applied_tags=[APPLICANT_ROLE_GIVEN_ID])

        is_spman = "Sprite Manager" in [role.name for role in ctx.author.roles]
        approver_role = "Sprite Manager" if is_spman else "Klefki"

        message = f"Hey {selected_user.mention}!! Congratulations, a {approver_role} thinks you qualify for the Spriter role! <:ohyes:686653537911832661>\n\n"\
                  f" **Please read the following information:**\n\n"\
                  f":yellow_circle: Make sure you have read the entirety of the <#873571372981452830>!\n\n"\
                  f":yellow_circle: Also have a read through the ⁠<#1113616457197170748>!\n\n"\
                  f":yellow_circle: You must ALWAYS post your sprites to ⁠<#1050404143807873157> first before uploading them to the <#543958354377179176> "\
                  f"so people have a chance to give you feedback! Try to leave it up for a least a day if you're not getting much feedback. You can also post "\
                  f"the latest version of your sprite to ⁠<#882011946801569802> along with a link to your #post, if you're not sure if it's ready to post to the gallery just yet.\n\n"\
                  f":yellow_circle: Posts to the gallery have to be formatted for the game. They must be 288x288 px pngs (3x upscaled from 96x96) and must "\
                  f"have the name headdexnumber.bodydexnumber (e.g. 25.1.png for a Pikachu/Bulbasaur). All PIF Pokémon past gen 2 have different dex numbers "\
                  f"than normal, you can find those out on the wiki [HERE](<https://infinitefusion.fandom.com/wiki/Pokédex>), the FusionDex [HERE](<https://if.daena.me/>) "\
                  f"or with the dex command here on the Discord (e.g dex pikachu/bulbasaur).\n\n"\
                  f":yellow_circle: After You post a sprite to the Gallery, please go back to your Spritework forum post and 1) add the '<:HeartMail:901794946967801896> Added to Gallery' tag, 2) "\
                  f"remove the '<a:rainbudew:794762057727082516> Needs Feedback!' tag, and 3) right click your post and **Close** it!\n\n"\
                  f"- If you have any questions, please ask them here!\n\n"\
                  f"- By the way, please say so once you've read everything above, so the {approver_role} who approved you is aware."
        
        if more_work_needed:
            message += f"\n\n## However, your sprites need a little more work before they're ready to post to the gallery. Please ping a {approver_role} (such as {ctx.author.mention}) in your threads to get further feedback!"
                
        await ctx.message.delete(delay=2)
        await ctx.send(message)
        return
    
    @has_any_role("Klefki (Spriter role giver)", "Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="denyapp", pass_context=True,
                help ="[KLEFKI] Grants spriter role, removes applicant role, sends a message",
                brief = "Removes the spriter applicant role and gives info")
    @app_commands.describe(name="The user to give the role to")
    @app_commands.describe(reason="Reason for denial")
    @app_commands.autocomplete(reason=deny_autocomplete)
    async def appdeny(self, ctx: Context, name: User, reason:str, comment: str = ""):
        selected_user = ctx.guild.get_member(name.id)

        applicant_role = utils.get(ctx.guild.roles,id=SPRITER_APPLICANT_ID)
        
        await selected_user.remove_roles(applicant_role)
        await ctx.channel.edit(archived=False, applied_tags=[APPLICANT_ABANDONED_ID])

        message = f"Hey {selected_user.mention}! Unfortunately, your application has been denied for the time being for the following reason: **{reason.upper()}**.\n\n"\
        
        reason_message = deny_reasons[reason]
        message += reason_message

        if len(comment) > 0:
            message += f"\n\nFurthermore, the evaluator has left the following comment for you:\n\n"
            message += comment

        await ctx.message.delete(delay=2)
        await ctx.send(message)
        return


    @has_any_role("Klefki (Spriter role giver)", "Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="apply", pass_context=True,
                help ="[KLEFKI] Gives a user the spriter applicant role (silent)",
                brief = "Gives a user the spriter applicant role (silent)",)
    async def applicant(self, ctx: Context, name: User = None):
        selected_user = ctx.guild.get_member(name.id)

        applicant_role = utils.get(ctx.guild.roles,id=SPRITER_APPLICANT_ID)
        await selected_user.add_roles(applicant_role)

        await ctx.message.delete(delay=2)
        await ctx.send(f"Gave {selected_user.name} applicant role", ephemeral=True, delete_after=60)
        return
    
    @has_any_role("Klefki (Spriter role giver)", "Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="removeapp", pass_context=True,
                help ="[KLEFKI] Removes the spriter applicant role (silent)",
                brief = "Removes the spriter applicant role (silent)")
    async def remove(self, ctx: Context, name: User = None):
        selected_user = ctx.guild.get_member(name.id)

        applicant_role = utils.get(ctx.guild.roles,id=SPRITER_APPLICANT_ID)
        
        await selected_user.remove_roles(applicant_role)

        await ctx.message.delete(delay=2)
        await ctx.send(f"Removed applicant role from {selected_user.name}", ephemeral=True, delete_after=60)
        return
    
    @has_any_role("Klefki (Spriter role giver)", "Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="givespriter", pass_context=True,
                help ="[KLEFKI] Gives a user the spriter role (silent)",
                brief = "Gives a user the spriter role (silent)",)
    async def givespriter(self, ctx: Context, name: User = None):
        selected_user = ctx.guild.get_member(name.id)

        applicant_role = utils.get(ctx.guild.roles,id=SPRITER_APPLICANT_ID)
        spriter_role = utils.get(ctx.guild.roles,id=SPRITER_ID)
        
        await selected_user.add_roles(spriter_role)
        await selected_user.remove_roles(applicant_role)

        await ctx.message.delete(delay=2)
        await ctx.send(f"Gave {selected_user.name} applicant role", ephemeral=True, delete_after=60)
        return

async def setup(bot:Bot):
    await bot.add_cog(Klefki(bot))


def load_env_vars(env: str):
    """ Loads in env vars based on dev or prod. Makes me cry."""
    is_dev = env == "dev"

    global SPRITER_APPLICANT_ID
    SPRITER_APPLICANT_ID = os.environ.get("DEV_SPRITER_APPLICANT_ID") if is_dev else os.environ.get("SPRITER_APPLICANT_ID")
    SPRITER_APPLICANT_ID = int(SPRITER_APPLICANT_ID)

    global SPRITER_ID
    SPRITER_ID = os.environ.get("DEV_SPRITER_ID") if is_dev else os.environ.get("SPRITER_ID")
    SPRITER_ID = int(SPRITER_ID)

    global SPRITE_APP_CHANNEL_ID
    SPRITE_APP_CHANNEL_ID = os.environ.get("DEV_SPRITE_APP_CHANNEL_ID") if is_dev else os.environ.get("SPRITE_APP_CHANNEL_ID")
    SPRITE_APP_CHANNEL_ID = int(SPRITE_APP_CHANNEL_ID)

    global APPLICANT_ABANDONED_ID
    APPLICANT_ABANDONED_ID = os.environ.get("DEV_APPLICANT_ABANDONED_ID") if is_dev else os.environ.get("APPLICANT_ABANDONED_ID")
    APPLICANT_ABANDONED_ID = int(APPLICANT_ABANDONED_ID)

    global APPLICANT_ROLE_GIVEN_ID
    APPLICANT_ROLE_GIVEN_ID = os.environ.get("DEV_APPLICANT_ROLE_GIVEN_ID") if is_dev else os.environ.get("APPLICANT_ROLE_GIVEN_ID")
    APPLICANT_ROLE_GIVEN_ID = int(APPLICANT_ROLE_GIVEN_ID)