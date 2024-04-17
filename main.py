import os
import typing
import logging
import dotenv
from enum import Enum
import datetime
import discord
from discord.ext import commands
from distutils.util import strtobool

dotenv.load_dotenv()
DEVELOPMENT_MODE = bool(strtobool(os.getenv('DEVELOPMENT', False)))
GUILD_ID = os.getenv('DISCORD_GUILD')


def expected_guild():
    if GUILD_ID:
        try:
            return discord.Object(id=GUILD_ID)
        except Exception as e:
            print('Could not load guild from ID in .env: [' + type(e) + '] ' + str(e))
            exit()
    elif os.getenv('DEVELOPMENT'):
        print('Allowing null guild for development/testing')
        return None
    else:
        raise Exception('No Guild ID set in .env and we are not in development mode')


class ELKBot(commands.Bot):
    def __init__(self, *args, dev_mode=False, expected_guild, **kwargs):
        print(f'ELKBot.__init__({args}, {kwargs})')

        self.dev_mode = dev_mode
        self.expected_guild = expected_guild
        self.bot_channel = None

        self.logger = logging.getLogger('discord.elkbot')
        self.logger.setLevel(logging.DEBUG)

        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        self.logger.info(f'ELKBot.setup_hook()')

        self.bot_channel = await self.get_bot_channel()

        await bot.load_extension('commands.info')
        await bot.load_extension('commands.siege')
        await bot.load_extension('commands.v1')

    def global_check(self, ctx):
        # TODO do we want this?
        # if self.dev_mode and self.is_owner(ctx.author):
        #     self.logger.debug('Skipping global checks as we are in dev mode and author is the bot owner')
        #     return True

        if ctx.guild is None:
            raise commands.NoPrivateMessage('Not in a Guild context')

        # TODO make this better (load from config)
        # Check if the command author has any of the specified roles
        # 1182141732079542283 = Kings
        # 1182141804821356644 = Princes
        # 1227613947482472510 = ELK Bot Testing - bot-commands
        role_ids = [1182141732079542283, 1182141804821356644, 1227613947482472510]
        if not any(role.id in role_ids for role in ctx.author.roles):
            raise commands.CheckFailure('Author does not have allowed role')

        # All checks have passed
        return True

    async def get_bot_channel(self):
        bot_channel_id = os.getenv('DISCORD_BOT_CHANNEL')

        if not bot_channel_id:
            logger.warning('Discord bot channel has not been configured')
            return None

        try:
            return await self.fetch_channel(bot_channel_id)
        except discord.HTTPException as e:
            self.logger.error(f'Could not fetch Discord bot channel: {e}')
            return None

    async def log_to_discord(self, message, silent=True):
        if not self.bot_channel:
            return

        return await self.bot_channel.send(message, silent=silent)

    async def log_command_to_discord(self, command: str, user: discord.User, channel: discord.TextChannel, content: any = None):
        message = f'Command `{command}` called by {user.mention} in {channel.mention}'

        if content:
            message += ' with `{content}`'

        await self.log_to_discord(message)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            self.logger.warning(f'Bot command check failed: {error}')
            await ctx.message.reply(f"You are not allowed to run this command", delete_after=10, silent=True)

            if ctx.interaction:
                pass # how to handle interaction?
            else:
                await ctx.message.delete(delay=11) # delayed to after error message auto-deleted
        else:
            self.logger.error(f'Bot command error: {error}')
            await ctx.send(f"Bot command error: {error}", ephemeral=True)
            await self.log_to_discord(f"Bot command error: {error}")

    def on_error(self, event: str, *args, **kwargs):
        self.logger.error(f'Bot error: {event}')
        #await self.log_to_discord(f'Bot error: {event}') # TODO howdo?

        return super(ELKBot, self).on_error(event, *args, **kwargs)

    async def on_ready(self):
        self.logger.debug(f'ELKBot.on_ready()')
        start_message = await self.log_to_discord(f'ELKBot is starting: <t:{datetime.datetime.utcnow():%s}:F>')

        for guild in self.guilds:
            if self.dev_mode and self.expected_guild is None:
                self.logger.warning('WARNING: Allowing any guild as we are in development mode')
            elif guild.id != self.expected_guild.id:
                self.logger.warning(f'WARNING: Bot connected to unexpected Guild')
            self.logger.info(f'We have logged in as {self.user} for {guild} ({guild.id})')

        if self.expected_guild is None:
            self.logger.info('Not syncing commands to guild as there is no configured expected guild')
        else:
            self.tree.copy_global_to(guild=self.expected_guild)
            await self.tree.sync(guild=self.expected_guild)

        self.logger.info('ELKBot ready!')
        await start_message.edit(content=f'ELKBot is up and running: <t:{datetime.datetime.utcnow():%s}:F>')

    ################
    ## Debug Logging

    async def start(self, *args, **kwargs):
        self.logger.debug(f'ELKBot.start({args}, {kwargs})')
        return await super().start(*args, **kwargs)

    async def login(self, *args, **kwargs):
        self.logger.debug(f'ELKBot.login({args}, {kwargs})')
        return await super().login(*args, **kwargs)

    async def on_connect(self):
        self.logger.debug(f'ELKBot.on_connect()')

    async def on_disconnect(self):
        self.logger.debug(f'ELKBot.on_disconnect()')

    async def on_guild_join(self, guild: discord.Guild):
        self.logger.debug(f'Guild joined: {guild.name} ({guild.id})')

    async def on_guild_remove(self, guild: discord.Guild):
        self.logger.debug(f'Guild left: {guild.name} ({guild.id})')

    async def on_guild_available(self, guild: discord.Guild):
        self.logger.debug(f'Guild available: {guild.name} ({guild.id})')

    async def on_guild_unavailable(self, guild: discord.Guild):
        self.logger.debug(f'Guild unavailable: {guild.name} ({guild.id})')

    async def on_resumed(self):
        self.logger.debug(f'Bot has resumed')

    # TODO work out a way to generically log slash/context commands
    # async def on_interaction(self, interaction: discord.Interaction):
    #     data = {
    #         'id': interaction.id,
    #         'type': str(interaction.type),
    #         'user': interaction.user.name,
    #         'channel': interaction.channel.name,
    #     }
    #
    #     if str(interaction.type) == 'InteractionType.application_command':
    #         data['command'] = {
    #             'type': interaction.
    #             'cog': interaction.data['name'],
    #             'name': interaction.command.name,
    #             'description': interaction.command.description,
    #         }
    #     else:
    #         data['command'] = interaction.command
    #         data['data'] = interaction.data
    #
    #     self.logger.info(f'Interaction: {data}')


intents = discord.Intents.default()
intents.message_content = True
bot = ELKBot(command_prefix='!', intents=intents, expected_guild=expected_guild(), dev_mode=DEVELOPMENT_MODE)

# Add the global bot check
bot.check(bot.global_check)


@bot.command(name='reload')
async def reload(ctx: commands.Context):
    await ctx.message.delete()

    reload_msg = await ctx.bot.log_to_discord(f'Reloading commands...')
    await ctx.bot.reload_extension('commands.info')
    await ctx.bot.reload_extension('commands.siege')
    await ctx.bot.reload_extension('commands.v1')
    await reload_msg.edit(content=f'All commands reloaded at <t:{datetime.datetime.utcnow():%s}:F>')

    if ctx.bot.expected_guild is None:
        print('Not syncing commands to guild as there is no configured expected guild')
    else:
        sync_msg = await ctx.bot.log_to_discord(f'Syncing command tree...')
        ctx.bot.tree.copy_global_to(guild=ctx.bot.expected_guild)
        await ctx.bot.tree.sync(guild=ctx.bot.expected_guild)
        await sync_msg.edit(content=f'Command tree synced at <t:{datetime.datetime.utcnow():%s}:F>')


bot.run(os.getenv('DISCORD_TOKEN'))