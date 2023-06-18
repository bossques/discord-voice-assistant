import io
import struct
import time
import wave

import discord
from discord import opus
from discord.ext import commands
from faster_whisper import WhisperModel

model = WhisperModel(
    model_size_or_path='base.en',
    device='cpu',
    compute_type='int8'
)


def transcribe(buffer: io.BytesIO) -> str:
    start = time.time()

    try:
        segments, _ = model.transcribe(
            audio=buffer,
            language='en',
            beam_size=5,
            vad_filter=True
        )

        segments = [segment.text for segment in list(segments)]
        message = ' '.join(segments)

        end = time.time()
        elapsed = end - start

        print(f'Taken {elapsed}s to process: {message}')

        return message
    except Exception as e:
        print('Failed to transcribe', e)
        return ''


async def send_transcription(channel: discord.VoiceChannel, user_id: str, message: str):
    message = message.strip()
    if message != '':
        await channel.send(
            content=f'<@{user_id}>: {message}'
        )


async def on_stop(sink: discord.sinks.WaveSink, ctx: discord.ApplicationContext):
    await sink.vc.disconnect()

    await ctx.edit(
        embed=discord.Embed(
            description='I am no longer transcribing your voices.'
        )
    )


class TranscribeVoiceClient(discord.VoiceClient):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        super().__init__(client, channel)
        self.speaking_states = {}

    def recv_decoded_audio(self, data):
        # do not fill quiet time with silence
        silence = 0

        data.decoded_data = (
            struct.pack("<h", 0) * silence * opus._OpusStruct.CHANNELS
            + data.decoded_data
        )
        while data.ssrc not in self.ws.ssrc_map:
            time.sleep(0.05)

        self.sink.write(data.decoded_data, self.ws.ssrc_map[data.ssrc]["user_id"])

    def unpack_audio(self, data):
        if 200 <= data[1] <= 204:
            return
        if self.paused:
            return

        data = discord.sinks.RawData(data, self)

        while data.ssrc not in self.ws.ssrc_map:
            time.sleep(0.05)

        user_id = self.ws.ssrc_map[data.ssrc]['user_id']

        if data.decrypted_data == b"\xf8\xff\xfe":  # Frame of silence
            is_speaking = self.speaking_states.get(user_id, False)
            if is_speaking:
                self.speaking_states[user_id] = False
                self.on_silence(user_id)
            return
        else:
            is_speaking = self.speaking_states.get(user_id, False)
            if not is_speaking:
                self.speaking_states[user_id] = True
                self.on_speak(user_id)

        self.decoder.decode(data)

    def on_speak(self, user_id: str):
        audio_data = self.sink.audio_data.get(user_id)
        if not audio_data:
            return
        audio_file = audio_data.file

        audio_file.seek(0)
        audio_file.truncate(0)

    def on_silence(self, user_id: str):
        audio_data = self.sink.audio_data[user_id]
        audio_file = audio_data.file
        audio_file.seek(0)

        audio_bytes = audio_file.read()

        with io.BytesIO() as buffer:
            with wave.open(buffer, 'wb') as f:
                f.setnchannels(self.sink.vc.decoder.CHANNELS)
                f.setsampwidth(self.sink.vc.decoder.SAMPLE_SIZE // self.sink.vc.decoder.CHANNELS)
                f.setframerate(self.sink.vc.decoder.SAMPLING_RATE)
                f.writeframes(audio_bytes)

            buffer.seek(0)

            # for debugging purposes
            # with open(f'{user_id}-{int(time.time())}.wav', 'wb') as f:
            #    f.write(buffer.getvalue())

            message = transcribe(buffer)

        self.client.loop.create_task(send_transcription(self.channel, user_id, message))


class TranscribeExtension(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command()
    async def transcribe(self, ctx: discord.ApplicationContext):
        state = ctx.user.voice
        client = await state.channel.connect(cls=TranscribeVoiceClient)

        sink = discord.sinks.WaveSink()

        client.start_recording(
            sink,
            on_stop,
            ctx
        )

        await ctx.respond(
            embed=discord.Embed(
                description='🎙️ I\'m now transcribing your voices.'
            )
        )


def setup(bot: discord.Bot):
    bot.add_cog(TranscribeExtension(bot))
