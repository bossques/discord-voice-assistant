# discord-voice-assistant

### Prerequisites

Before running the Discord Voice Bot, make sure you have the following:

* Python installed (version 3.10 or higher)
* Discord API token - You can obtain this by creating a new bot on the [Discord Developer Portal](https://discord.com/developers/applications)

### Setup (Linux)

1. Rename `.env.example` to `.env` and edit the environment variables

2. Install the required packages
```bash
pip install -r requirements.txt
```

3. Paste this to set the `LD_LIBRARY_PATH` variable
```bash
export LD_LIBRARY_PATH=`python3 -c 'import os; import nvidia.cublas.lib; import nvidia.cudnn.lib; print(os.path.dirname(nvidia.cublas.lib.__file__) + ":" + os.path.dirname(nvidia.cudnn.lib.__file__))'`
```

### Run

```bash
python main.py
```

### Features

- `/record` - Enables voice recording in your current voice channel.
- `/tts file {message}` - Generates an MP3 file containing the message you provided, converted into speech.
- `/tts speak {message}` - Joins your voice channel and delivers the message by speaking it aloud.
- `/transcribe` - Joins your voice channel and transcribes your speech into text.
