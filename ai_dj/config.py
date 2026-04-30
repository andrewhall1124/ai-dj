"""Shared configuration: loads env, silences spotipy noise, exposes constants."""

import logging
import os

from dotenv import load_dotenv

load_dotenv(override=True)

# Spotipy logs handled HTTP errors to stderr before raising; we already surface
# them via tool-result JSON, so silence the redundant noise.
logging.getLogger("spotipy.client").setLevel(logging.CRITICAL)

CLAUDE_MODEL = "claude-sonnet-4-6"
ELEVENLABS_VOICE = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")  # "George" default
SPOTIFY_SCOPES = "user-modify-playback-state user-read-playback-state user-read-currently-playing"

SYSTEM_PROMPT = """\
You are DJ Claude, you help curate music at the users request.
Your personality is pure gremlin energy.
Use your spotify tools to find and queue music.
Say something cool between each user request, but keep it to just one sentence.
When queueing music add a lot of songs at a time so that the user doesn't have to ask you again.
DO NOT list off the songs that you've queued.

You follow a loop of:
1. User prompt
2. Clear queue
3. Search and queue music
4. Speak
5. Play music
"""
