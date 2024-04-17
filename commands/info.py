import os
from typing import List, Union
import logging
import datetime
from enum import Enum
import json
import discord
import discord.ui
import discord.ext.commands
import discord.app_commands


class Info(discord.ext.commands.Cog):
    info = discord.app_commands.Group(name='info', description='Get info about different discord things')

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(f'discord.elkbot.{__name__}')

        self.context_menu_commands = [
            discord.app_commands.ContextMenu(name='Channel Info', callback=self.message_context_channel_info),
            discord.app_commands.ContextMenu(name='Message Info', callback=self.message_context_info),
            discord.app_commands.ContextMenu(name='User Info', callback=self.user_context_info),
        ]

    async def cog_load(self):
        for context_menu_command in self.context_menu_commands:
            self.bot.tree.add_command(context_menu_command)

        self.logger.info('Info cog loaded')

    async def cog_unload(self):
        for context_menu_command in self.context_menu_commands:
            self.bot.tree.add_command(context_menu_command.name, type=context_menu_command.type)

        self.logger.info('Info cog unloaded')

    def format_info_message(self, info_type: str, data: dict):
        key_length = 12

        message = f"# {info_type.title()} Info"
        message += '\n```'

        for key, value in data.items():
            key = key.replace('_', ' ').title()

            if isinstance(value, List):
                message += f"\n{key}"
                pad = ' ' * (key_length - len(key))
                for item in value:
                    message += f"{pad} {item}"
                    pad='\n' + ' ' * key_length
            elif isinstance(value, datetime.datetime):
                message += f"\n{key:{key_length}s} {value:%Y-%m-%d %H:%M:%S %Z}"
            else:
                message += f"\n{key:{key_length}s} {value}"

        message += '\n```'

        return message

    # Guild Info (command only)
    @info.command(description='Get info about the Guild')
    async def guild(self, interaction: discord.Interaction, extended: bool = False):
        await self.bot.log_command_to_discord('info.guild', interaction.user, interaction.channel, {'extended': extended})

        guild = interaction.guild

        info = {
            'id': guild.id,
            'name': guild.name,
            'members': guild.member_count,
        }

        if extended:
            info.update({
                'channels': len(guild.channels),
                'vanity_url': guild.vanity_url_code,
                'owner': guild.owner_id,
                'description': guild.description,
                'verification': guild.verification_level,
            })

        await interaction.response.send_message(self.format_info_message('guild', info), ephemeral=True)

    # Channel Info (command and context)
    async def _channel_info(self, interaction: discord.Interaction, channel: discord.TextChannel, extended: bool = False):
        await self.bot.log_command_to_discord('info.channel', interaction.user, interaction.channel, {'channel': channel.name, 'extended': extended})

        info = {
            'id': channel.id,
            'name': channel.name,
            'type': channel.type,
            'category': channel.category,
            'topic': channel.topic,
        }

        if extended:
            info.update({
                'position': channel.position,
                'slow_delay': channel.slowmode_delay,
                'nsfw': channel.nsfw,
            })

        await interaction.response.send_message(self.format_info_message('channel', info), ephemeral=True)

    async def message_context_channel_info(self, interaction: discord.Interaction, message: discord.Message):
        channel = message.channel
        await self._channel_info(interaction, channel)

    @info.command(description='Get info about a Channel')
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel, extended: bool = False):
        await self._channel_info(interaction, channel, extended)

    # Message Info (context only)
    async def message_context_info(self, interaction: discord.Interaction, message: discord.Message):
        await self.bot.log_command_to_discord('info.message', interaction.user, interaction.channel, {'message': message.jump_url})

        info = {
            'id': message.id,
            'author': message.author,
            'channel': message.channel,
            'preview': message.clean_content[:30],
            'created': message.created_at,
            'edited': message.edited_at,
            'pinned': message.pinned,
            'url': message.jump_url,
        }

        await interaction.response.send_message(self.format_info_message('message', info), ephemeral=True)

    # User Info (command and context)
    async def _user_info(self, interaction: discord.Interaction, user: Union[discord.User, discord.Member], extended: bool = False):
        await self.bot.log_command_to_discord('info.user', interaction.user, interaction.channel, {'user': user.name, 'extended': extended})

        info = {
            'id': user.id,
            'name': user.name,
            #'roles': ', '.join(role.name for role in user.roles),
            'roles': user.roles,
            'display_name': user.display_name,
        }

        if isinstance(user, discord.Member):
            info.update({
                'nick': user.nick,
                'joined': user.joined_at,
                'pending': user.pending,
            })

        if extended:
            info.update({
                'global_name': user.global_name,
                'created': user.created_at,
                'bot': user.bot,
                'system': user.system,
            })

        await interaction.response.send_message(self.format_info_message('user', info), ephemeral=True)

    @info.command(description='Get info about a user')
    async def user(self, interaction: discord.Interaction, user: discord.User, extended: bool = False):
        await self._user_info(interaction, user, extended)

    async def user_context_info(self, interaction: discord.Interaction, user: discord.User):
        await self._user_info(interaction, user)

    # Role Info (command only)
    @info.command(description='Get info about a role')
    async def role(self, interaction: discord.Interaction, role: discord.Role, extended: bool = False):
        await self.bot.log_command_to_discord('info.command', interaction.user, interaction.channel, {'role': role.name, 'extended': extended})

        info = {
            'id': role.id,
            'name': role.name,
            'hoist': role.hoist,
            'members': len(role.members),
            'color': role.color,
            'icon': role.display_icon,
        }

        if extended:
            info.update({
                'position': role.position,
                'managed': role.managed,
                'tags': role.tags,
                'created_at': role.created_at,
            })

        await interaction.response.send_message(self.format_info_message('guild', info), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Info(bot=bot))
