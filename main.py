import os

from discord import Bot
from dotenv import load_dotenv

load_dotenv()
bot = Bot()


@bot.event
async def on_ready():
    print(f'Ready! Logged in as {bot.user} ({bot.user.id})')

extensions = ['record', 'tts', 'transcribe']
for extension in extensions:
    bot.load_extension(f'cogs.{extension}')

bot.run(os.getenv('DISCORD_TOKEN'))
