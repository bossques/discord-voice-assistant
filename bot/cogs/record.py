import discord
from discord.ext import commands


async def on_stop(sink: discord.sinks.WaveSink, ctx: discord.ApplicationContext):
    await sink.vc.disconnect()
    files = [discord.File(audio.file, f'{user_id}.{sink.encoding}') for user_id, audio in sink.audio_data.items()]
    await ctx.edit(
        embed=None,
        files=files
    )


class RecordView(discord.ui.View):
    def __init__(self, voice_client: discord.VoiceClient):
        self.voice_client = voice_client
        super().__init__()

    @discord.ui.button(label='Pause', style=discord.ButtonStyle.gray, emoji='⏸')
    async def pause_callback(self, button, interaction):
        button.label = 'Pause' if self.voice_client.paused else 'Resume'
        button.emoji = '⏸' if self.voice_client.paused else '▶'
        button.style = discord.ButtonStyle.gray if self.voice_client.paused else discord.ButtonStyle.green
        self.voice_client.toggle_pause()
        await interaction.response.edit_message(
            embed=discord.Embed(
                description='Recording has paused. ⏸' if self.voice_client.paused else 'Recording has resumed! 🎙️'
            ),
            view=self
        )

    @discord.ui.button(label='Stop', style=discord.ButtonStyle.danger, emoji='🛑')
    async def stop_callback(self, button, interaction):
        self.voice_client.stop_recording()
        await interaction.response.edit_message(
            embed=discord.Embed(
                description='Recording is processing. ⌛'
            ),
            view=None
        )


class RecordExtension(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command()
    async def record(self, ctx: discord.ApplicationContext):
        state = ctx.user.voice
        client = await state.channel.connect(cls=discord.VoiceClient)

        client.start_recording(
            discord.sinks.WaveSink(),
            on_stop,
            ctx
        )

        await ctx.respond(
            embed=discord.Embed(
                description='Recording has started! 🎙️'
            ),
            view=RecordView(client)
        )


def setup(bot: discord.Bot):
    bot.add_cog(RecordExtension(bot))
