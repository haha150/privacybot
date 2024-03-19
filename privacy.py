from discord.ext import tasks, commands
import logging

class PrivacyCog(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('discord')
        self.bot = bot
        self.prune.start()
        self.channels = []
        self.id = 210888915090014208
        self.trash = []
        self.prune_trash.start()

    def addChannel(self, c):
        self.channels.append(c)

    def addTrash(self, t):
        self.trash.append(t)

    def clearTrash(self):
        self.trash.clear()

    def getChannels(self):
        return [channel.voice.name for channel in self.channels]
    
    def join(self, name, password):
        for channel in self.channels:
            if channel.voice.name == name and channel.password == password:
                return channel
        return None

    async def cog_unload(self):
        self.logger.info('PrivacyCog unloading')
        for channel in self.channels:
            await channel.voice.delete()
            await channel.text.delete()
            await channel.role.delete()

    @tasks.loop(minutes=1)
    async def prune(self):
        for channel in self.channels:
            if channel.duration == -1:
                continue
            if channel.expired():
                await channel.voice.delete()
                await channel.text.delete()
                await channel.role.delete()
                self.channels.remove(channel)

    @tasks.loop(seconds=30)
    async def prune_trash(self):
        for guild in self.bot.guilds:
            smuts = guild.get_member(self.id)
            if not smuts:
                break
            for t in self.trash:
                ban = guild.get_member(t)
                if ban and smuts.voice and ban.voice and smuts.voice.channel == ban.voice.channel:
                    await ban.move_to(None)

    @prune.before_loop
    async def before_printer(self):
        self.logger.info('PrivacyCog waiting...')
        await self.bot.wait_until_ready()

