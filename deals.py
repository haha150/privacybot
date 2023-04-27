from discord.ext import tasks, commands
import asyncio
import logging
from scrapers import Scrapers

class DealsCog(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('discord')
        self.bot = bot
        self.scrapers = Scrapers()
        self.scrape.start()

    def cog_unload(self):
        self.logger.info('DealsCog unloading')
        self.scrape.cancel()

    @tasks.loop(minutes=1)
    async def scrape(self):
        self.logger.info('DealsCog started')
        try:
            adealsweden = self.scrapers.scrape_adealsweden()
            if self.scrapers.adealsweden_old and len(adealsweden) <= 5:
                for channel in self.bot.allowed_channels:
                    for adeal in adealsweden:
                        msg = f'@everyone new deal from adealsweden.com\n{adeal.name}\n{adeal.price}\n{adeal.url}'
                        self.logger.info(msg)
                        await channel.send(content=msg)
                        await asyncio.sleep(2)
        except Exception as e:
            self.logger.error(f'Failed to scrape: adealsweden.com')
            self.logger.error(e)
        try:
            swedroid = self.scrapers.scrape_swedroid()
            if self.scrapers.swedroid_old and len(swedroid) <= 5:
                for channel in self.bot.allowed_channels:
                    for droid in swedroid:
                        url = droid.url.split('?')[0]
                        if url == 'https://www.amazon.se/s':
                            url = droid.url
                        msg = f'@everyone new deal from swedroid.se\n{url}'
                        self.logger.info(msg)
                        await channel.send(content=msg)
                        await asyncio.sleep(2)
        except Exception as e:
            self.logger.error(f'Failed to scrape: swedroid.se')
            self.logger.error(e)

    @scrape.before_loop
    async def before_printer(self):
        self.logger.info('DealsCog waiting...')
        await self.bot.wait_until_ready()
