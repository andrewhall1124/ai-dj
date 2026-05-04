"""Tool schemas, dispatch, and the Claude agent turn loop."""

import json

from anthropic import Anthropic

from ai_dj.config import CLAUDE_MODEL, SYSTEM_PROMPT
from ai_dj.spotify_controller import SpotifyController
from ai_dj.voice import DJVoice

TOOLS = [
    {
        "name": "search",
        "description": "Search Spotify for tracks, artists, or albums. Returns top results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (song name, artist, genre, mood, etc.)"
                },
                "search_type": {
                    "type": "string",
                    "enum": ["track", "artist", "album"],
                    "description": "Type of search. Default: track"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of results to return (1-10). Default: 5"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "play",
        "description": "Start playing a specific track by its Spotify URI, or resume playback.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track_uri": {
                    "type": "string",
                    "description": "Spotify track URI (e.g. spotify:track:xxx). If omitted, resumes current playback."
                }
            },
            "required": []
        }
    },
    {
        "name": "add_to_queue",
        "description": "Add a track to the playback queue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track_uri": {
                    "type": "string",
                    "description": "Spotify track URI to add to queue"
                }
            },
            "required": ["track_uri"]
        }
    },
    {
        "name": "skip",
        "description": "Skip to the next track in the queue.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "clear_queue",
        "description": "Clear all upcoming tracks from the playback queue.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "currently_playing",
        "description": "Get info about the currently playing track.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "pause",
        "description": "Pause playback.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "speak",
        "description": "Deliver one sentence of DJ commentary before queuing music. Pauses current playback while speaking; call this BEFORE play or add_to_queue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "One sentence of DJ commentary — pure gremlin energy."
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "volume",
        "description": "Set playback volume on the active device.",
        "input_schema": {
            "type": "object",
            "properties": {
                "volume_percent": {
                    "type": "integer",
                    "description": "Volume level from 0 (mute) to 100 (max)."
                }
            },
            "required": ["volume_percent"]
        }
    },
    {
        "name": "list_devices",
        "description": "List all available Spotify devices and which one is currently selected.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "select_device",
        "description": "Select which Spotify device to play music on.",
        "input_schema": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The Spotify device ID to use for playback."
                }
            },
            "required": ["device_id"]
        }
    },
    {
        "name": "ask_user",
        "description": "Ask the user a question and wait for their reply before continuing. Use when you need information to proceed, e.g. which Spotify device to play on. Call list_devices first, then ask_user with the options listed. Do NOT guess or auto-select.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user."
                }
            },
            "required": ["question"]
        }
    },
]


def handle_tool_call(
    spotify: SpotifyController,
    voice: DJVoice,
    tool_name: str,
    tool_input: dict,
    voice_enabled: bool = True,
) -> str:
    """Execute a tool call and return the result as a string."""
    if tool_name == "search":
        return spotify.search(
            query=tool_input["query"],
            search_type=tool_input.get("search_type", "track"),
            limit=tool_input.get("limit", 5)
        )
    elif tool_name == "play":
        return spotify.play(track_uri=tool_input.get("track_uri"))
    elif tool_name == "add_to_queue":
        return spotify.add_to_queue(track_uri=tool_input["track_uri"])
    elif tool_name == "skip":
        return spotify.skip()
    elif tool_name == "clear_queue":
        return spotify.clear_queue()
    elif tool_name == "currently_playing":
        return spotify.currently_playing()
    elif tool_name == "pause":
        return spotify.pause()
    elif tool_name == "speak":
        text = tool_input["text"]
        playback = spotify.sp.current_playback()
        if playback and playback.get("is_playing"):
            spotify.pause()
        if voice_enabled and voice.enabled:
            voice.speak(text)
        return json.dumps({"status": "spoke", "text": text})
    elif tool_name == "volume":
        return spotify.volume(volume_percent=tool_input["volume_percent"])
    elif tool_name == "list_devices":
        return spotify.list_devices()
    elif tool_name == "select_device":
        return spotify.select_device(device_id=tool_input["device_id"])
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


def run_agent_turn(
    client: Anthropic,
    spotify: SpotifyController,
    voice: DJVoice,
    messages: list,
    voice_enabled: bool = True,
) -> tuple[str, str, str | None, str | None]:
    """Run one full agent turn and return (reply, commentary, question, pending_tool_use_id).

    If the agent calls ask_user, the turn pauses: question and pending_tool_use_id are
    non-None, and the caller must inject the user's answer as a tool result before the
    next turn.
    """
    commentaries: list[str] = []

    while True:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        text_parts = []
        tool_uses = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            ask_user_call = next((t for t in tool_uses if t.name == "ask_user"), None)
            if ask_user_call:
                question = ask_user_call.input["question"]
                print(f"  🔧 ask_user({question[:80]}...)")
                return "", " ".join(commentaries), question, ask_user_call.id

            tool_results = []
            for tool_use in tool_uses:
                print(f"  🔧 {tool_use.name}({json.dumps(tool_use.input, indent=None)[:80]}...)")
                result = handle_tool_call(
                    spotify, voice, tool_use.name, tool_use.input, voice_enabled
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result
                })
                if tool_use.name == "speak":
                    commentaries.append(tool_use.input["text"])

            messages.append({"role": "user", "content": tool_results})
            continue

        else:
            messages.append({"role": "assistant", "content": response.content})
            reply = "\n".join(text_parts)
            commentary = " ".join(commentaries)
            return reply, commentary, None, None
