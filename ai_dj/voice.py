"""ElevenLabs TTS wrapper for DJ commentary."""

import os

from elevenlabs import ElevenLabs
from elevenlabs.play import play

from config import ELEVENLABS_VOICE


class DJVoice:
    def __init__(self):
        api_key = os.getenv("ELEVENLABS_API_KEY")
        self.client = ElevenLabs(api_key=api_key) if api_key else None
        self.voice_id = ELEVENLABS_VOICE
        self.enabled = self.client is not None

    def speak(self, text: str):
        if not self.enabled:
            return
        try:
            audio = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id="eleven_turbo_v2_5",
                voice_settings={'speed': 1.2}
            )
            play(audio)
        except Exception as e:
            print(f"  [TTS error: {e}]")
