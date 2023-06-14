import subprocess
import shlex
import discord
from discord.ext import commands
from discord.opus import Encoder
from gtts import gTTS
from io import BytesIO


def create_tts(message: str) -> BytesIO:
    tts = gTTS(message)
    tts_mp3 = BytesIO()
    tts.write_to_fp(tts_mp3)
    tts_mp3.seek(0)

    return tts_mp3


async def on_end(client: discord.VoiceClient, error):
    if error:
        raise error
    await client.disconnect()


class FFmpegPCMAudio(discord.AudioSource):
    def __init__(self, source, *, executable='ffmpeg', pipe=False, stderr=None, before_options=None, options=None):
        stdin = None if not pipe else source
        args = [executable]
        if isinstance(before_options, str):
            args.extend(shlex.split(before_options))
        args.append('-i')
        args.append('-' if pipe else source)
        args.extend(('-f', 's16le', '-ar', '48000', '-ac', '2', '-loglevel', 'warning'))
        if isinstance(options, str):
            args.extend(shlex.split(options))
        args.append('pipe:1')
        self._process = None
        try:
            self._process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr)
            self._stdout = BytesIO(
                self._process.communicate(input=stdin)[0]
            )
        except FileNotFoundError:
            raise discord.ClientException(executable + ' was not found.') from None
        except subprocess.SubprocessError as exc:
            raise discord.ClientException('Popen failed: {0.__class__.__name__}: {0}'.format(exc)) from exc

    def read(self):
        ret = self._stdout.read(Encoder.FRAME_SIZE)
        if len(ret) != Encoder.FRAME_SIZE:
            return b''
        return ret

    def cleanup(self):
        proc = self._process
        if proc is None:
            return
        proc.kill()
        if proc.poll() is None:
            proc.communicate()

        self._process = None


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
