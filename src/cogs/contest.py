from discord.ext.commands import Bot, Cog, Context, command, has_any_role
from discord import User, utils

WINNING_ROLE_NAME="Current Winner"
PREV_WINNER_ROLE_NAME="Past Winner"

class Contest(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @has_any_role("Mime Jr.(Event Organizer)", "Sprite Manager", "Bot Manager")
    @command(name="win", pass_context=True,
                help ="Gives a mentioned user the current mini-contest winner role",
                brief = "Crowns a champion")
    async def crown(self, ctx: Context, name: User = None):
        winning_user = ctx.guild.get_member(name.id)

        winner_role = utils.get(ctx.guild.roles,name=WINNING_ROLE_NAME)
        await winning_user.add_roles(winner_role)

        await ctx.message.delete(delay=2)
        await ctx.send(f"Crowned {winning_user.name} as a champion!")
        return
    
    @has_any_role("Mime Jr.(Event Organizer)", "Sprite Manager", "Bot Manager")
    @command(name="retire", pass_context=True,
                help ="Removes current winner role from user and adds past winner role",
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

async def setup(bot:Bot):
    await bot.add_cog(Contest(bot))