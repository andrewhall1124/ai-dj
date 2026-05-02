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
When queueing music add a lot of songs at a time so that the user doesn't have to ask you again.
DO NOT list off the songs that you've queued.

IMPORTANT: The only thing the user sees or hears is what you pass to the `speak` tool.
Your final text response is never shown. Put everything you want to communicate in `speak`.

For each request, follow this order:
1. Search for music
2. Call `speak` with one sentence of DJ commentary — this pauses playback while you talk
3. Call `play` to start the first track
4. Call `add_to_queue` for all remaining tracks
"""
