import io
import time
from typing import Tuple

import discord
from discord.ext import commands
from faster_whisper import WhisperModel
from gpt4all import GPT4All

from bot.util import AbstractTranscribeVoiceClient, create_tts, FFmpegPCMAudio


class TranscribeVoiceClient(AbstractTranscribeVoiceClient):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        whisper_model = WhisperModel(
            model_size_or_path='large-v2',
            device='cuda',
            compute_type='float16'
        )
        super().__init__(client, channel, whisper_model)
        self.gpt_model = GPT4All(
            model_name='orca-mini-3b-gguf2-q4_0.gguf',
            device='cpu'
        )

    def on_speech_end(self, user_id: str, audio: io.BytesIO):
        time_taken, message = self.transcribe(audio)
        message = message.strip()

        if message != '':
            print('Taken %s to transcribe: %s' % (time_taken, message))
            self.client.loop.create_task(self.process_transcription(user_id, message))

    async def process_transcription(self, user_id: str, message: str):
        time_taken, response = self.generate_response(message)
        print('Taken %s to generate response to transcription: %s' % (time_taken, response))

        response_tts = create_tts(response)
        self.play(
            source=FFmpegPCMAudio(response_tts.read(), pipe=True)
        )

    def generate_response(self, message: str) -> Tuple[float, str]:
        start = time.time()
        response = self.gpt_model.generate(prompt=message)
        end = time.time()
        elapsed = end - start
        return elapsed, response


class GPTExtension(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @staticmethod
    async def on_stop(sink: discord.sinks.WaveSink, ctx: discord.ApplicationContext):
        await sink.vc.disconnect()

    @discord.slash_command()
    async def converse(self, ctx: discord.ApplicationContext):
        state = ctx.user.voice
        client = await state.channel.connect(cls=TranscribeVoiceClient)

        sink = discord.sinks.WaveSink()
        client.start_recording(sink, self.on_stop, ctx)

        await ctx.respond(
            content=f'Joined your voice channel.'
        )


def setup(bot: discord.Bot):
    bot.add_cog(GPTExtension(bot))
