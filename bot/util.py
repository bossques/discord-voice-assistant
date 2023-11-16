import time
import io
import wave
import os
import subprocess
import shlex
from typing import Tuple

import discord
from faster_whisper import WhisperModel
from gtts import gTTS


class AbstractTranscribeVoiceClient(discord.VoiceClient):
    def __init__(
        self,
        client: discord.Client,
        channel: discord.abc.Connectable,
        transcription_model: WhisperModel
    ):
        super().__init__(client, channel)
        self.transcription_model = transcription_model
        self.speaking_states = {}

    def recv_decoded_audio(self, data):
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

            if os.getenv('DEBUG', 'false').lower() == 'true':
                with open(f'{user_id}-{int(time.time())}.wav', 'wb') as f:
                    f.write(buffer.getvalue())

            self.on_speech_end(user_id, buffer)

    def transcribe(self, buffer: io.BytesIO) -> Tuple[float, str]:
        start = time.time()

        try:
            segments, _ = self.transcription_model.transcribe(
                audio=buffer,
                language='en',
                beam_size=5,
                vad_filter=True
            )

            segments = [segment.text for segment in list(segments)]
            message = ' '.join(segments)

            end = time.time()
            elapsed = end - start

            return elapsed, message
        except Exception as e:
            raise e

    def on_speech_end(self, user_id: str, audio: io.BytesIO):
        time_taken, message = self.transcribe(audio)
        print('Taken %s to transcribe: %s' % (time_taken, message))


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
            self._stdout = io.BytesIO(
                self._process.communicate(input=stdin)[0]
            )
        except FileNotFoundError:
            raise discord.ClientException(executable + ' was not found.') from None
        except subprocess.SubprocessError as exc:
            raise discord.ClientException('Popen failed: {0.__class__.__name__}: {0}'.format(exc)) from exc

    def read(self):
        ret = self._stdout.read(discord.opus.Encoder.FRAME_SIZE)
        if len(ret) != discord.opus.Encoder.FRAME_SIZE:
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


def create_tts(message: str) -> io.BytesIO:
    tts = gTTS(message)
    tts_mp3 = io.BytesIO()
    tts.write_to_fp(tts_mp3)
    tts_mp3.seek(0)

    return tts_mp3
