import io

import discord
from discord.ext import commands
from faster_whisper import WhisperModel

from bot.util import AbstractTranscribeVoiceClient


class TranscribeVoiceClient(AbstractTranscribeVoiceClient):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        model = WhisperModel(
            model_size_or_path='large-v2',
            device='cuda',
            compute_type='float16'
        )
        super().__init__(client, channel, model)

    def on_speech_end(self, user_id: str, audio: io.BytesIO):
        time_taken, message = self.transcribe(audio)
        message = message.strip()

        if message != '':
            print('Taken %s to transcribe: %s' % (time_taken, message))
            self.client.loop.create_task(self.send_transcription(user_id, message))

    async def send_transcription(self, user_id: str, message: str):
        await self.channel.send('<@%s>: %s' % (user_id, message))


class TranscribeExtension(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @staticmethod
    async def on_stop(sink: discord.sinks.WaveSink, ctx: discord.ApplicationContext):
        await sink.vc.disconnect()
        await ctx.edit(embed=discord.Embed(description='I am no longer transcribing your voices.'))

    @discord.slash_command()
    async def transcribe(self, ctx: discord.ApplicationContext):
        state = ctx.user.voice
        client = await state.channel.connect(cls=TranscribeVoiceClient)

        sink = discord.sinks.WaveSink()
        client.start_recording(sink, self.on_stop, ctx)

        await ctx.respond(embed=discord.Embed(description='🎙️ I\'m now transcribing your voices.'))


def setup(bot: discord.Bot):
    bot.add_cog(TranscribeExtension(bot))
