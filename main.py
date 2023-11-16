import os

from discord import Bot
from dotenv import load_dotenv

load_dotenv()
bot = Bot()


@bot.event
async def on_ready():
    print(f'Ready! Logged in as {bot.user} ({bot.user.id})')

extensions = ['record', 'tts', 'transcribe', 'gpt']
for extension in extensions:
    try:
        bot.load_extension(f'bot.cogs.{extension}')
    except Exception as e:
        raise e

bot.run(os.getenv('DISCORD_TOKEN'))
