import logging
from privacy import PrivacyCog
from cmds import CmdsCog
from discord.ext import commands
import discord
import os
from dotenv import load_dotenv

LOG_FILE = 'discord.log'
LOGGER = 'discord'
TOKEN = 'TOKEN'

class DealsBot(commands.Bot):
    def __init__(self, logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger

    async def on_ready(self):
        self.logger.info(f'Logged in as: {self.user}')
        for guild in self.guilds:
            self.logger.info(f'Connected to server: {guild}')
        if not self.get_cog('PrivacyCog'):
            await self.add_cog(PrivacyCog(self))
        if not self.get_cog('CmdsCog'):
            await self.add_cog(CmdsCog(self))

def main ():
    logger = logging.getLogger(LOGGER)
    load_dotenv()
    handler = logging.FileHandler(filename=LOG_FILE, encoding='utf-8', mode='w')
    intents = discord.Intents.all()
    client = DealsBot(logger, intents=intents, command_prefix='/')
    client.run(os.getenv(TOKEN), log_handler=handler, log_level=logging.INFO)
    
if __name__ == "__main__":
    main()