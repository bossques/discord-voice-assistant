import os

from discord import Bot
from dotenv import load_dotenv

load_dotenv()
bot = Bot()


@bot.event
async def on_ready():
    print(f'Ready! Logged in as {bot.user} ({bot.user.id})')

bot.load_extension('cogs.record')
bot.run(os.getenv('DISCORD_TOKEN'))
