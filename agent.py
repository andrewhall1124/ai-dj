"""Tool schemas, dispatch, and the Claude agent turn loop."""

import json

from anthropic import Anthropic

from config import CLAUDE_MODEL, SYSTEM_PROMPT
from spotify_controller import SpotifyController

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
]


def handle_tool_call(spotify: SpotifyController, tool_name: str, tool_input: dict) -> str:
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
    elif tool_name == "volume":
        return spotify.volume(volume_percent=tool_input["volume_percent"])
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


def run_agent_turn(client: Anthropic, spotify: SpotifyController, messages: list) -> tuple[str, tuple | None, bool]:
    """
    Run one full agent turn: call Claude, handle any tool use in a loop,
    and return (final_text, pending_action, pending_clear).

    play, skip, and clear_queue are NOT executed immediately — they are deferred
    so the caller can fire them after TTS finishes. When clear_queue is deferred
    alongside play/skip, the caller runs clear_queue first.

    pending_action is ("play", uri_or_None) | ("skip", None) | None.
    pending_clear is True if clear_queue was requested this turn.
    """
    pending_action = None
    pending_clear = False

    while True:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Collect text blocks and tool use blocks from the response
        text_parts = []
        tool_uses = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        # If there are tool calls, execute them and continue the loop
        if response.stop_reason == "tool_use":
            # Append the full assistant message (with tool_use blocks)
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool and collect results
            tool_results = []
            for tool_use in tool_uses:
                print(f"  🔧 {tool_use.name}({json.dumps(tool_use.input, indent=None)[:80]}...)")
                # Defer playback-mutating calls so music doesn't start before TTS
                if tool_use.name == "play":
                    uri = tool_use.input.get("track_uri")
                    pending_action = ("play", uri)
                    result = json.dumps({"status": "playing" if uri else "resumed", "track_uri": uri})
                elif tool_use.name == "skip":
                    pending_action = ("skip", None)
                    result = json.dumps({"status": "skipped"})
                elif tool_use.name == "clear_queue":
                    pending_clear = True
                    result = json.dumps({"status": "queue_cleared"})
                else:
                    result = handle_tool_call(spotify, tool_use.name, tool_use.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result
                })

            messages.append({"role": "user", "content": tool_results})
            continue  # Loop back for Claude to process tool results

        else:
            # End turn — append final assistant message
            messages.append({"role": "assistant", "content": response.content})
            return "\n".join(text_parts), pending_action, pending_clear
