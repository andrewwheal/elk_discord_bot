import os
from typing import List, NamedTuple, Tuple
import logging
import datetime
from enum import Enum
import json
import discord
import discord.ext.commands
import discord.app_commands


class City(NamedTuple):
    """Represents a PvE City/Citadel we can siege"""
    id: str
    name: str
    level: int
    deep_link: str = None
    coords: Tuple[int, int] = None
    region: str = None

    @property
    def full_name(self):
        return f'Lv.{self.level} {self.name}'


class Siege(discord.ext.commands.Cog):
    config_file = f"{os.getcwd()}/config/cities.json"
    siege = discord.app_commands.Group(name='siege', description='Manage Sieges')

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(f'discord.elkbot.{__name__}')

        self.cities = self.load_cities()

    async def cog_load(self):
        self.logger.info('Siege cog loaded')

    async def cog_unload(self):
        self.logger.info('Siege cog unloaded')

    def load_cities(self):
        """Load cities from list of dicts into dict of NamedTuples"""
        try:
            with open(self.config_file, 'r') as cities_config:
                data = json.load(cities_config)

            return {city['id']:City(**city) for city in data}
        except FileNotFoundError as e:
            self.logger.warning('Cities config not found')
            return []
        except Exception:
            self.logger.exception('Could not load cities from config')
            return []

    def save_cities(self):
        """Save our dict of City NamedTuples as a list of dicts"""
        try:
            with open(self.config_file, 'w') as cities_config:
                json.dump(list(city._asdict() for city in self.cities.values()), cities_config, indent=4)
        except Exception:
            self.logger.exception('Could not save cities to config')

    def get_city(self, city_id: str) -> dict:
        return self.cities[city_id]

    @siege.command(description='Schedule a siege on a city')
    @discord.app_commands.describe(city='Select the city we are going to siege', day='Pick which day the siege will take place (or enter in format YYYY-MM-DD)', time='Set the start time of the siege, in 24 hour UTC')
    async def start(self, interaction: discord.Interaction, city: str, day: str, time: str):
        # Detect wrong channel
        if not interaction.channel.name.endswith('-missions'):
            return await interaction.response.send_message('Sieges must be started in the `s01-missions` channel', ephemeral=True)

        await self.bot.log_command_to_discord('siege.start', interaction.user, interaction.channel, {'city': city, 'day': day, 'time': time})

        # Validate time, it's the only manually input data
        try:
            datetime.time.fromisoformat(time)
        except:
            self.logger.exception(f'siege.start time not valid: {time}')
            raise ValueError('The provided time is not valid')

        city = self.get_city(city)
        start_string = f'{day}T{time}Z'
        start_time = datetime.datetime.fromisoformat(start_string)

        await interaction.response.send_message(f"Scheduling siege of {city.full_name} at <t:{start_time:%s}:F> (that's <t:{start_time:%s}:R>)", ephemeral=True)

        reactions = {
            "✅": "if you will be there",
            "❓": "if you're not sure",
            "❌": "if you know you won't make it",
        }

        role = discord.utils.get(interaction.guild.roles, name='Server 01')

        message_content = f"# {city.full_name}\nSiege will start at <t:{start_time:%s}:F> (that's <t:{start_time:%s}:R>)"

        if city.deep_link:
            link_text = city.name

            if city.coords:
                link_text += f' ({city.coords})'

            message_content += f'\nLink to city in game: [{link_text}]({city.deep_link})'

        message_content += f'\n\n{role.mention} React with whether you will be joining this siege'
        for reaction, reason in reactions.items():
            message_content += f"\n\t{reaction} {reason}"

        first_message = await interaction.channel.send(message_content)

        for reaction in reactions:
            try:
                await first_message.add_reaction(reaction)
            except Exception as e:
                self.logger.exception('Could not add reaction to siege message: %s', str(e))

    @start.autocomplete('city')
    async def autocomplete_city(self, interaction: discord.Interaction, current: str) -> List[discord.app_commands.Choice[str]]:
        try:
            return [
                discord.app_commands.Choice(name=city.full_name, value=city.id)
                for city in self.cities.values() if current.lower() in city.name.lower()
            ]
        except:
            self.logger.exception('Error autocompleting city for siege')

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

    @start.error
    async def start_on_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        self.logger.warning(f'siege.start error: {error}')

        if error.original:
            await interaction.response.send_message(f'There was an error scheduling the siege: {error.original}', ephemeral=True)
        else:
            await interaction.response.send_message(f'There was an error scheduling the siege: {error}', ephemeral=True)

    @siege.command(description='Add a new city/gate that we can siege')
    @discord.app_commands.describe(
        name='Name of the city (e.g. "Ochyro Zoni")',
        level='Numeric level (e.g. "5")',
        coordinates='Coordinates of the city (e.g. `808,1480`, note no space or brackets)',
        deep_link='The link provided when sharing in game to an external app',
        region='Name of the region the city is in (e.g. "Orion")'
    )
    async def add_city(self, interaction: discord.Interaction, name: str, level: int, coordinates: str = None, deep_link: str = None, region: str = None):
        await self.bot.log_command_to_discord('siege.add_city', interaction.user, interaction.channel, {'name': name, 'level': level})

        id = name.replace(' ', '').lower()

        city = City(id, name, level, deep_link, coordinates, region)

        self.cities.update({id: city})
        self.save_cities()

        await interaction.response.send_message(f'City added: {city.full_name}', ephemeral=True)

    @siege.command(description='List the currently configured cities available for us to siege')
    async def list_cities(self, interaction: discord.Interaction):
        await self.bot.log_command_to_discord('siege.list_cities', interaction.user, interaction.channel)

        message = 'Here are the cities we can siege that are currently configured:'
        for city in self.cities.values():
            message += f"\n\t{city.full_name}"

            if city.deep_link:
                if city.coords:
                    message += f" [({city.coords})]({city.deep_link})"
                else:
                    message += f" [game link]({city.deep_link})"
            elif city.coords:
                message += f' ({city.coords})'

        await interaction.response.send_message(message, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Siege(bot=bot))
