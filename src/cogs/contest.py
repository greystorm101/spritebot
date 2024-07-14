import os
from discord.ext.commands import Bot, Cog, Context, has_any_role, hybrid_command
from discord import User, utils
import discord

WINNING_ROLE_NAME="Event Winner"
PREV_WINNER_ROLE_NAME="Past Event Winner"

MIME_JR_ID = 641801785618726956

class Contest(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        load_env_vars(bot.env)

    @has_any_role(MIME_JR_ID, "Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="win", pass_context=True,
                help ="[MIMEJR] Gives a mentioned user the current mini-contest winner role",
                brief = "Crowns a champion")
    async def crown(self, ctx: Context, name: User = None):
        winning_user = ctx.guild.get_member(name.id)

        winner_role = utils.get(ctx.guild.roles,name=WINNING_ROLE_NAME)
        await winning_user.add_roles(winner_role)

        await ctx.message.delete(delay=2)
        await ctx.send(f"Crowned {winning_user.name} as a champion!")
        return
    
    @has_any_role(MIME_JR_ID, "Sprite Manager", "Bot Manager", "Creator")
    @hybrid_command(name="retire", pass_context=True,
                help ="[MIMEJR] Removes current winner role from user and adds past winner role",
                brief = "Makes a winner a past winner")
    async def retire(self, ctx: Context, name: User = None):
        winning_user = ctx.guild.get_member(name.id)

        winner_role = utils.get(ctx.guild.roles,name=WINNING_ROLE_NAME)
        past_winner_role = utils.get(ctx.guild.roles,name=PREV_WINNER_ROLE_NAME)
        
        await winning_user.add_roles(past_winner_role)
        await winning_user.remove_roles(winner_role)

        await ctx.message.delete(delay=2)
        await ctx.send(f"Made {winning_user.name} a retired champion!")
        return

def load_env_vars(env: str):

    is_dev = env == "dev"

    global MIME_JR_ID
    MIME_JR_ID = os.environ.get("DEV_MIME_JR_ID") if is_dev else os.environ.get("MIME_JR_ID")
    MIME_JR_ID = int(MIME_JR_ID)


async def setup(bot:Bot):
    await bot.add_cog(Contest(bot))
