import logging
from discord.ext import commands
import discord
from deals import DealsCog
from typing import List
import os
import requests

PAT = 'PAT'
USERNAME_GITHUB = 'USERNAME_GITHUB'

class CmdsCog(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('discord')
        self.bot = bot
        self.pat = os.getenv(PAT)
        self.username = os.getenv(USERNAME_GITHUB)
        self.deployed = False

    def cog_unload(self):
        self.logger.info('CmdsCog unloading')

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(self, _):
        self.logger.info(await self.bot.tree.sync())

    @discord.app_commands.guild_only()
    @discord.app_commands.command(name='start', description='Start the bot scrapers. Can only be invoked by bot owner and admins.')
    async def start(self, interaction: discord.Interaction):
        if await self.bot.is_owner(interaction.user) or (interaction.guild.name in self.bot.servers and interaction.user.id in self.bot.admins):
            if not self.bot.get_cog('DealsCog'):
                await self.bot.add_cog(DealsCog(self.bot))
                await interaction.response.send_message('Scrapers started', ephemeral=True)
            else:
                await interaction.response.send_message('Scrapers already started', ephemeral=True)
        else:
            await interaction.response.send_message('Cant help you loser!')

    @discord.app_commands.guild_only()
    @discord.app_commands.command(name='stop', description='Stop the bot scrapers. Can only be invoked by bot owner and admins.')
    async def stop(self, interaction: discord.Interaction):
        if await self.bot.is_owner(interaction.user) or (interaction.guild.name in self.bot.servers and interaction.user.id in self.bot.admins):
            if self.bot.get_cog('DealsCog'):
                await self.bot.remove_cog('DealsCog')
                await interaction.response.send_message('Scrapers stopped', ephemeral=True)
            else:
                await interaction.response.send_message('Scrapers already stopped', ephemeral=True)
        else:
            await interaction.response.send_message('Cant help you loser!')

    @discord.app_commands.guild_only()
    @discord.app_commands.command(name='kill', description='Kill the bot. Can only be invoked by bot owner.')
    async def kill(self, interaction: discord.Interaction):
        if await self.bot.is_owner(interaction.user):
            await interaction.response.send_message('Bot killed!', ephemeral=True)
            await self.bot.close()
        else:
            await interaction.response.send_message('Cant help you loser!')

    @discord.app_commands.guild_only()
    @discord.app_commands.command(name='logs', description='Prints the last specified number of lines of the log. Can only be invoked by bot owner.')
    async def logs(self, interaction: discord.Interaction, number: int):
        if number > 0 and number < 101:
            if await self.bot.is_owner(interaction.user):
                log = ''
                with open('discord.log', 'r') as f:
                    for line in (f.readlines() [-number:]):
                        log += line
                if not log:
                    log = 'Logs empty!'
                logz = [(log[i:i+1999]) for i in range(0, len(log), 1999)]
                await interaction.response.send_message(f'{logz[-1]}', ephemeral=True)
            else:
                await interaction.response.send_message('Cant help you loser!')
        else:
            await interaction.response.send_message('Cant help you loser!')

    @logs.autocomplete('number')
    async def logs_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[discord.app_commands.Choice[str]]:
        numbers = ['1', '5', '10', '50', '100']
        return [
            discord.app_commands.Choice(name=number, value=number)
            for number in numbers if current == number
        ]

    @discord.app_commands.guild_only()
    @discord.app_commands.command(name='clearlogs', description='Clear the logs. Can only be invoked by bot owner.')
    async def clearlogs(self, interaction: discord.Interaction):
        if await self.bot.is_owner(interaction.user):
            with open('discord.log', 'w'):
                pass
            await interaction.response.send_message('Logs cleared', ephemeral=True)
        else:
            await interaction.response.send_message('Cant help you loser!')

    @discord.app_commands.guild_only()
    @discord.app_commands.command(name='getlogs', description='Get the logs. Can only be invoked by bot owner.')
    async def getlogs(self, interaction: discord.Interaction):
        if await self.bot.is_owner(interaction.user):
            await interaction.response.send_message('Got logs', ephemeral=True, file=discord.File('discord.log'))
        else:
            await interaction.response.send_message('Cant help you loser!')

    @discord.app_commands.guild_only()
    @discord.app_commands.command(name='deploy', description='Re-deploys the bot. Can only be invoked by bot owner.')
    async def deploy(self, interaction: discord.Interaction):
        if await self.bot.is_owner(interaction.user):
            if not self.deployed:
                url = f'https://api.github.com/repos/{self.username}/dealsbot/dispatches'
                headers = { 'Authorization': f'Bearer {self.pat}' }
                data = { 'event_type': 'Deploy' }
                response = requests.post(url, headers=headers, json=data)
                self.logger.info(response.text)
                self.deployed = True
                await interaction.response.send_message('Re-deploying...', ephemeral=True)
            else:
                await interaction.response.send_message('Already re-deployed, wait for it...', ephemeral=True)
        else:
            await interaction.response.send_message('Cant help you loser!')