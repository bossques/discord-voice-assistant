import discord
from discord.ext import commands

from bot.util import FFmpegPCMAudio, create_tts


async def on_end(client: discord.VoiceClient, error):
    if error:
        raise error
    await client.disconnect()


class TTSExtension(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    tts = discord.SlashCommandGroup('tts')

    @tts.command()
    async def file(self, ctx: discord.ApplicationContext, message: str):
        tts = create_tts(message)

        await ctx.respond(
            file=discord.File(tts, 'tts.mp3')
        )

    @tts.command()
    async def speak(self, ctx: discord.ApplicationContext, message: str):
        state = ctx.user.voice
        client = await state.channel.connect(cls=discord.VoiceClient)
        tts = create_tts(message)

        client.play(
            source=FFmpegPCMAudio(tts.read(), pipe=True),
            after=lambda error: self.bot.loop.create_task(on_end(client, error))
        )
        await ctx.respond(
            content=f'Playing tts in {client.channel.mention}'
        )


def setup(bot: discord.Bot):
    bot.add_cog(TTSExtension(bot))
