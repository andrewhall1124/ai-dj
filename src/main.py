"""
AI DJ — A terminal-based conversational DJ powered by Claude, Spotify, and ElevenLabs.

Usage:
    1. Copy .env.example to .env and fill in your API keys
    2. pip install anthropic spotipy elevenlabs python-dotenv
    3. python main.py

You talk to the DJ via text. The DJ:
  - Picks and queues songs on Spotify
  - Gives spoken DJ commentary via ElevenLabs
  - Remembers context across the conversation
"""

import sys

from anthropic import Anthropic

import config  # noqa: F401  — side effects: load_dotenv, silence spotipy logger
from agent import run_agent_turn
from spotify_controller import SpotifyController
from voice import DJVoice


def main():
    print("=" * 60)
    print("  🎧  DJ Claude  🎧")
    print("  Your AI-powered personal radio DJ")
    print("=" * 60)

    # ── Init clients ──
    claude = Anthropic()

    print("\n  Connecting to Spotify...")
    try:
        spotify = SpotifyController()
        user = spotify.sp.current_user()
        print(f"  ✅ Logged in as {user['display_name']}")
        device_id = spotify.ensure_active_device()
        device_name = next(
            (d["name"] for d in spotify.sp.devices()["devices"] if d["id"] == device_id),
            device_id,
        )
        print(f"  ✅ Active device: {device_name}")
    except Exception as e:
        print(f"  ❌ Spotify connection failed: {e}")
        print("  Make sure your .env has SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REDIRECT_URI")
        print("  And open Spotify on at least one device (phone, desktop, or web player).")
        sys.exit(1)

    voice = DJVoice()
    if voice.enabled:
        print("  ✅ ElevenLabs TTS enabled")
    else:
        print("  ⚠️  No ELEVENLABS_API_KEY — running text-only (no voice)")

    print("\n  Type your requests, or 'quit' to exit.\n")

    messages = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  👋 DJ Claude signing off. Stay groovy.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\n  👋 DJ Claude signing off. Stay groovy.")
            break

        messages.append({"role": "user", "content": user_input})

        print()
        dj_response, pending_action, pending_clear = run_agent_turn(claude, spotify, messages)
        print(f"DJ Claude: {dj_response}\n")

        if voice.enabled and dj_response:
            current = spotify.sp.current_playback()
            was_playing = bool(current and current.get("is_playing"))
            if was_playing:
                spotify.pause()
            voice.speak(dj_response)
            if pending_clear:
                spotify.clear_queue()
            if pending_action:
                action_type, uri = pending_action
                if action_type == "play":
                    spotify.play(track_uri=uri)
                elif action_type == "skip":
                    spotify.skip()
            elif was_playing and not pending_clear:
                spotify.play()  # resume whatever we paused


if __name__ == "__main__":
    main()
