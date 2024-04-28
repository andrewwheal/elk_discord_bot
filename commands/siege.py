import os
from typing import List
import logging
import datetime
from enum import Enum
import json
import discord
import discord.ext.commands
import discord.app_commands


class Siege(discord.ext.commands.Cog):
    config_file = f"{os.getcwd()}/config/cities.json"
    siege = discord.app_commands.Group(name='siege', description='Siege things')

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(f'discord.elkbot.{__name__}')

        self.cities = self.load_cities()

    async def cog_load(self):
        self.logger.info('Siege cog loaded')

    async def cog_unload(self):
        self.logger.info('Siege cog unloaded')

    def load_cities(self):
        try:
            with open(self.config_file, 'r') as cities_config:
                return json.load(cities_config)
        except FileNotFoundError as e:
            print('Cities config not found, creating it')
            with open(self.config_file, 'w') as cities_config:
                json.dump([], cities_config)
            return []

    def save_cities(self):
        with open(self.config_file, 'w') as cities_config:
            json.dump(self.cities, cities_config, indent=4)

    @siege.command(description='Schedule a siege on a city')
    @discord.app_commands.describe(city='Select the city we are going to siege', day='Pick which day the siege will take place (or enter in format YYYY-MM-DD)', time='Set the start time of the siege, in 24 hour UTC')
    async def start(self, interaction: discord.Interaction, city: str, day: str, time: str):
        time = datetime.datetime.fromisoformat(f'{day}T{time}')
        await interaction.response.send_message(f"Lets start a siege on {city} at <t:{time:%s}:F> (that's <t:{time:%s}:R>)")

    @start.autocomplete('city')
    async def autocomplete_city(self, interaction: discord.Interaction, current: str) -> List[discord.app_commands.Choice[str]]:
        print('siege city autocomplete')
        return [
            discord.app_commands.Choice(name=f"Lv.{city['level']} {city['name']}", value=city['id'])
            for city in self.cities if current.lower() in city['name'].lower()
        ]

    @start.autocomplete('day')
    async def autocomplete_day(self, interaction: discord.Interaction, current: str) -> List[discord.app_commands.Choice[str]]:
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        two_days = today + datetime.timedelta(days=2)

        days = [
            {"name": f"today ({today:%a %d %b})", "value": str(today)},
            {"name": f"tomorrow ({tomorrow:%a %d %b})", "value": str(tomorrow)},
            {"name": f"in two days ({two_days:%a %d %b})", "value": str(two_days)},
        ]
        return [
            discord.app_commands.Choice(name=day['value'], value=day['value'])
            for day in days if current.lower() in day['name']
        ]

    @siege.command(description='Add a new city (etc) that we can siege')
    async def add_city(self, interaction: discord.Interaction, name: str, level: int):
        id = name.replace(' ', '').lower()
        self.cities.append({"id": id, "name": name, "level": level})
        self.save_cities()
        await interaction.response.send_message('City added', ephemeral=True)

    @siege.command(description='List the currently configured cities available for us to siege')
    async def list_cities(self, interaction: discord.Interaction):
        await self.bot.log_command_to_discord('siege.list_cities', interaction.user, interaction.channel)

        message = 'Here are the cities we can siege that are currently configured:'
        for city in self.cities:
            message += f"\n\tLv.{city['level']} {city['name']}"

        await interaction.response.send_message(message, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Siege(bot=bot))
