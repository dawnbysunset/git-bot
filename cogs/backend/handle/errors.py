import discord
import traceback
from typing import Union
from discord.ext import commands
from bot import PRODUCTION
from lib.globs import Mgr


class Errors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error) -> None:
        setattr(ctx, 'fmt', Mgr.fmt(ctx))
        ctx.fmt.set_prefix('errors')
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.err(ctx.l.errors.missing_required_argument)
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.err(ctx.fmt('command_on_cooldown', '{:.2f}'.format(error.retry_after)))
        elif isinstance(error, commands.MaxConcurrencyReached):
            await ctx.err(ctx.l.errors.max_concurrency_reached)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.err(ctx.fmt('bot_missing_permissions', ', '.join([f'`{m}`' for m in error.missing_perms]).replace('_', ' ')))
        elif isinstance(error, commands.MissingPermissions):
            await ctx.err(ctx.fmt('missing_permissions', ', '.join([f'`{m}`' for m in error.missing_perms]).replace('_', ' ')))
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.err(ctx.l.errors.no_private_message)
        elif isinstance(error, commands.CommandNotFound):
            await self.respond_to_command_doesnt_exist(ctx, error)
            if PRODUCTION:
                await self.log_error_in_discord(ctx, error)
        elif not PRODUCTION:
            raise error
        else:
            await self.log_error_in_discord(ctx, error)
            print(error)

    async def respond_to_command_doesnt_exist(self, ctx: commands.Context, error: commands.CommandNotFound) -> None:
        setattr(ctx, 'l', await Mgr.get_locale(ctx))
        setattr(ctx, 'fmt', Mgr.fmt(ctx))
        ctx.fmt.set_prefix('errors command_not_found')
        embed: discord.Embed = discord.Embed(
            color=0x0384fc,
            title=ctx.l.errors.command_not_found.title,
            description=ctx.fmt('description', f'```haskell\n{str(self.bot.command_prefix).strip()} {(self.closest_existing_command_from_error(error))}```')
        )
        embed.set_footer(text=ctx.l.errors.command_not_found.footer)
        await ctx.send(embed=embed)

    async def log_error_in_discord(self, ctx: commands.Context, error: Exception) -> None:
        channel: discord.TextChannel = await self.bot.fetch_channel(853247229036593164)
        if channel:
            guild_id: str = str(ctx.guild.id) if not isinstance(ctx.channel, discord.DMChannel) else 'DM'
            if ctx.command:
                embed: discord.Embed = discord.Embed(
                    color=0xda4353,
                    title=f'Error in `{ctx.command}` command'
                )
                embed.add_field(name='Message', value=f'```{error}```', inline=False)
                embed.add_field(name='Traceback', value=f'```{self.format_tb(error.__traceback__)}```', inline=False)
                embed.add_field(name='Arguments', value=f'```properties\nargs={self.format_args(ctx.args)}\nkwargs={self.format_kwargs(ctx.kwargs)}```', inline=False)

            elif isinstance(error, commands.CommandNotFound):
                embed: discord.Embed = discord.Embed(
                    color=0x0384fc,
                    title=f'Nonexistent command!',
                    description=f'```{(error := str(error))}```'
                )
                embed.set_footer(text=f'Closest existing command: "' + self.closest_existing_command_from_error(error))
            else:
                return
            embed.add_field(name='Location', value=f'**Guild ID:** `{guild_id}`\n**Author ID:** `{ctx.author.id}`', inline=False)
            await channel.send(embed=embed)

    def closest_existing_command_from_error(self, error: Union[commands.CommandNotFound, str]) -> str:
        return str(Mgr.get_closest_match_from_iterable(
               (error := str(error))[error.index('"') + 1:error.rindex('"')],
               map(str, self.bot.walk_commands())))

    def format_tb(self, tb) -> str:
        return '\n\n'.join([i.strip() for i in traceback.format_tb(tb, -5)])

    def format_args(self, args: list) -> str:
        for i, arg in enumerate(args):
            if repr(arg).startswith('<cogs'):
                args[i]: str = repr(arg).split()[0].strip('<')
            elif 'Context' in repr(arg):
                args[i]: str = 'ctx'
        return f"[{', '.join(args)}]"

    def format_kwargs(self, kwargs: dict) -> str:
        items: str = ', '.join([f"{k}=\'{v}\'" for k, v in kwargs.items()])
        return f'dict({items})' if items else 'No keyword arguments'


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Errors(bot))
