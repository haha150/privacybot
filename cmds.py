import logging
from discord.ext import commands
import discord
from discord import ui
import os
import requests
from privacy import PrivacyCog
from models import PrivacyChannel


class BulkMoveView(ui.View):
    def __init__(self, source: discord.VoiceChannel, destination: discord.VoiceChannel):
        super().__init__(timeout=60)
        self.source = source
        self.destination = destination
        self.selected_member_ids: list[int] = []

        members = source.members
        if not members:
            return

        select = ui.Select(
            placeholder="Select users to move...",
            min_values=1,
            max_values=len(members),
            options=[
                discord.SelectOption(label=m.display_name, value=str(m.id))
                for m in members[:25]
            ],
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        self.selected_member_ids = [int(v) for v in interaction.data["values"]]
        await interaction.response.defer()

    @ui.button(label="Move Selected", style=discord.ButtonStyle.primary)
    async def move_selected(self, interaction: discord.Interaction, button: ui.Button):
        if not self.selected_member_ids:
            await interaction.response.send_message("No users selected.", ephemeral=True)
            return
        moved = []
        failed = []
        for mid in self.selected_member_ids:
            member = self.source.guild.get_member(mid)
            if member and member.voice and member.voice.channel == self.source:
                try:
                    await member.move_to(self.destination)
                    moved.append(member.display_name)
                except discord.Forbidden:
                    failed.append(member.display_name)
            else:
                failed.append(str(mid))
        msg = f"Moved {len(moved)} user(s) to **{self.destination.name}**."
        if failed:
            msg += f"\nFailed to move: {', '.join(failed)}"
        self.stop()
        await interaction.response.edit_message(content=msg, view=None)

    @ui.button(label="Move All", style=discord.ButtonStyle.secondary)
    async def move_all(self, interaction: discord.Interaction, button: ui.Button):
        moved = []
        failed = []
        for member in list(self.source.members):
            try:
                await member.move_to(self.destination)
                moved.append(member.display_name)
            except discord.Forbidden:
                failed.append(member.display_name)
        msg = f"Moved {len(moved)} user(s) to **{self.destination.name}**."
        if failed:
            msg += f"\nFailed to move: {', '.join(failed)}"
        self.stop()
        await interaction.response.edit_message(content=msg, view=None)

    async def on_timeout(self):
        self.stop()

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
    @discord.app_commands.command(name='createchannel', description='Creates a new password protected channel (voice + text).')
    @discord.app_commands.choices(duration=[
        discord.app_commands.Choice(name="5 minutes", value=5*60),
        discord.app_commands.Choice(name="10 minutes", value=10*60),
        discord.app_commands.Choice(name="30 minutes", value=30*60),
        discord.app_commands.Choice(name="1 hour", value=1*60*60),
        discord.app_commands.Choice(name="2 hours", value=2*60*60),
        discord.app_commands.Choice(name="3 hours", value=3*60*60),
        discord.app_commands.Choice(name="6 hours", value=6*60*60),
        discord.app_commands.Choice(name="12 hours", value=12*60*60),
        discord.app_commands.Choice(name="24 hours", value=24*60*60),
        discord.app_commands.Choice(name="Permanent", value=-1)
    ])
    async def createchannel(self, interaction: discord.Interaction, name: str, password: str, duration: discord.app_commands.Choice[int]):
        if not self.bot.get_cog('PrivacyCog'):
            await self.bot.add_cog(PrivacyCog(self.bot))
        cog = self.bot.get_cog('PrivacyCog')
        for c in interaction.guild.channels:
            if name == c.name:
                await interaction.response.send_message(f'Channel "{name}" already exists!', ephemeral=True)
                return
        for r in interaction.guild.roles:
            if name == r.name:
                await interaction.response.send_message(f'Role "{name}" already exists!', ephemeral=True)
                return
        if name in cog.getChannels():
            await interaction.response.send_message(f'Channel "{name}" already exists!', ephemeral=True)
            return
        overwrites = {}
        role = await interaction.guild.create_role(name=name)
        for r in interaction.guild.roles:
            if r == role:
                continue
            overwrites.update({r: discord.PermissionOverwrite(view_channel=False)})
        overwrites.update({role: discord.PermissionOverwrite(view_channel=True)})
        voice = await interaction.guild.create_voice_channel(name, overwrites=overwrites)
        text = await interaction.guild.create_text_channel(name, overwrites=overwrites)
        cog.addChannel(PrivacyChannel(role, voice, text, password, duration.value))
        await interaction.response.send_message(f'Creating channel "{name}" with password "{password}" for {duration.name}.', ephemeral=True)

    @discord.app_commands.guild_only()
    @discord.app_commands.command(name='joinchannel', description='Join a password protected channel (voice + text).')
    async def joinchannel(self, interaction: discord.Interaction, name: str, password: str):
        if not self.bot.get_cog('PrivacyCog'):
            await self.bot.add_cog(PrivacyCog(self.bot))
        cog = self.bot.get_cog('PrivacyCog')
        exists = False
        for c in interaction.guild.channels:
            if name == c.name:
                exists = True
                break
        if name in cog.getChannels() and exists:
            channel = cog.join(name, password)
            if channel:
                await interaction.user.add_roles(channel.role)
                await interaction.response.send_message(f'Joining channel "{name}".', ephemeral=True)
            else:
                await interaction.response.send_message('Wrong password!', ephemeral=True)
        else:
            await interaction.response.send_message(f'Channel "{name}" does not exist!', ephemeral=True)

    @discord.app_commands.guild_only()
    @discord.app_commands.command(name='listchannels', description='Lists all created channels.')
    async def listchannels(self, interaction: discord.Interaction):
        if not self.bot.get_cog('PrivacyCog'):
            await self.bot.add_cog(PrivacyCog(self.bot))
        cog = self.bot.get_cog('PrivacyCog')
        if cog:
            channels = ''
            for name in cog.getChannels():
                channels += name
                channels += '\n'
            if channels:
                await interaction.response.send_message(channels, ephemeral=True)
            else:
                await interaction.response.send_message('No channels created', ephemeral=True)
        else:
            await interaction.response.send_message('No channels created', ephemeral=True)
                        
    @discord.app_commands.guild_only()
    @discord.app_commands.command(name='addtrash', description='Add trash.')
    async def addtrash(self, interaction: discord.Interaction, ban: str):
        if await self.bot.is_owner(interaction.user):
            if not self.bot.get_cog('PrivacyCog'):
                await self.bot.add_cog(PrivacyCog(self.bot))
            cog = self.bot.get_cog('PrivacyCog')
            if cog:
                cog.addTrash(int(ban))
                await interaction.response.send_message('Trash added', ephemeral=True)
            else:
                await interaction.response.send_message('No trash added', ephemeral=True)
        else:
            await interaction.response.send_message('Cant help you loser!')

    @discord.app_commands.guild_only()
    @discord.app_commands.command(name='listtrash', description='Lists all trash.')
    async def listtrash(self, interaction: discord.Interaction):
        if await self.bot.is_owner(interaction.user):
            if not self.bot.get_cog('PrivacyCog'):
                await self.bot.add_cog(PrivacyCog(self.bot))
            cog = self.bot.get_cog('PrivacyCog')
            if cog:
                if cog.trash:
                    await interaction.response.send_message(cog.trash, ephemeral=True)
                else:
                    await interaction.response.send_message('No trash added yet', ephemeral=True)
            else:
                await interaction.response.send_message('No trash added yet', ephemeral=True)
        else:
            await interaction.response.send_message('Cant help you loser!')

    @discord.app_commands.guild_only()
    @discord.app_commands.command(name='cleartrash', description='Clear trash.')
    async def cleartrash(self, interaction: discord.Interaction):
        if await self.bot.is_owner(interaction.user):
            if not self.bot.get_cog('PrivacyCog'):
                await self.bot.add_cog(PrivacyCog(self.bot))
            cog = self.bot.get_cog('PrivacyCog')
            if cog:
                cog.clearTrash()
                await interaction.response.send_message('Trash cleared', ephemeral=True)
            else:
                await interaction.response.send_message('No trash cleared', ephemeral=True)
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
    @discord.app_commands.choices(number=[
        discord.app_commands.Choice(name="1 line", value=1),
        discord.app_commands.Choice(name="5 lines", value=5),
        discord.app_commands.Choice(name="10 lines", value=10),
        discord.app_commands.Choice(name="50 lines", value=50),
        discord.app_commands.Choice(name="100 lines", value=100)
    ])
    async def logs(self, interaction: discord.Interaction, number: discord.app_commands.Choice[int]):
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
    @discord.app_commands.command(name='bulkmove', description='Bulk move users from one voice channel to another.')
    async def bulkmove(self, interaction: discord.Interaction, source: discord.VoiceChannel, destination: discord.VoiceChannel):
        if not interaction.user.guild_permissions.move_members:
            await interaction.response.send_message('You need the Move Members permission.', ephemeral=True)
            return
        if source == destination:
            await interaction.response.send_message('Source and destination must be different.', ephemeral=True)
            return
        if not source.members:
            await interaction.response.send_message(f'No users in **{source.name}**.', ephemeral=True)
            return
        view = BulkMoveView(source, destination)
        user_list = ', '.join(m.display_name for m in source.members[:25])
        await interaction.response.send_message(
            f'Users in **{source.name}**: {user_list}\n'
            f'Select users to move to **{destination.name}**, or click **Move All**.',
            view=view,
            ephemeral=True,
        )

    @discord.app_commands.guild_only()
    @discord.app_commands.command(name='deploy', description='Re-deploys the bot. Can only be invoked by bot owner.')
    async def deploy(self, interaction: discord.Interaction):
        if await self.bot.is_owner(interaction.user):
            if not self.deployed:
                url = f'https://api.github.com/repos/{self.username}/privacybot/dispatches'
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