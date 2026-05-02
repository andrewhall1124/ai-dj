"""FastAPI server — the shared DJ daemon used by all clients."""

import asyncio
import sys
from contextlib import asynccontextmanager

import uvicorn
from anthropic import Anthropic
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ai_dj.agent import run_agent_turn
from ai_dj.spotify_controller import SpotifyController
from ai_dj.voice import DJVoice


class ChatRequest(BaseModel):
    message: str
    voice: bool = True


class ChatResponse(BaseModel):
    reply: str
    commentary: str | None = None


_state: dict = {}
_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("DJ Claude server starting...")

    print("Connecting to Spotify...")
    try:
        spotify = SpotifyController()
        user = spotify.sp.current_user()
        print(f"Logged in as {user['display_name']}")
        spotify.ensure_active_device()
    except Exception as e:
        print(f"Spotify connection failed: {e}")
        sys.exit(1)

    voice = DJVoice()
    if voice.enabled:
        print("ElevenLabs TTS enabled")
    else:
        print("No ELEVENLABS_API_KEY — running text-only")

    _state["claude"] = Anthropic()
    _state["spotify"] = spotify
    _state["voice"] = voice
    _state["messages"] = []

    print("DJ Claude is ready.\n")
    yield
    _state.clear()


app = FastAPI(lifespan=lifespan)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    async with _lock:
        messages = _state["messages"]
        messages.append({"role": "user", "content": req.message})
        reply, commentary = await asyncio.to_thread(
            run_agent_turn,
            _state["claude"],
            _state["spotify"],
            _state["voice"],
            messages,
            req.voice,
        )
        return ChatResponse(reply=reply, commentary=commentary or None)


@app.get("/status")
async def status():
    spotify: SpotifyController = _state.get("spotify")
    if not spotify:
        raise HTTPException(status_code=503, detail="Server not ready")
    import json
    return json.loads(spotify.currently_playing())


def main():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000)
