"""FastAPI server — the shared DJ daemon used by all clients."""

import asyncio
import os
import sys
from contextlib import asynccontextmanager

import httpx
import uvicorn
from anthropic import Anthropic
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ai_dj.agent import run_agent_turn
from ai_dj.spotify_controller import SpotifyController
from ai_dj.voice import DJVoice

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


class ChatRequest(BaseModel):
    message: str
    voice: bool = True


class SiriRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    commentary: str | None = None
    question: str | None = None


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
    _state["pending_question"] = None  # {"tool_use_id": str} when agent awaits user input

    print("DJ Claude is ready.\n")
    yield
    _state.clear()


app = FastAPI(lifespan=lifespan)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    async with _lock:
        messages = _state["messages"]
        pending = _state["pending_question"]
        if pending:
            # User's message is the answer to the agent's pending ask_user call
            messages.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": pending["tool_use_id"], "content": req.message}]
            })
            _state["pending_question"] = None
        else:
            messages.append({"role": "user", "content": req.message})

        reply, commentary, question, tool_use_id = await asyncio.to_thread(
            run_agent_turn,
            _state["claude"],
            _state["spotify"],
            _state["voice"],
            messages,
            req.voice,
        )

        if question:
            _state["pending_question"] = {"tool_use_id": tool_use_id}
            return ChatResponse(reply=question, question=question, commentary=commentary or None)

        return ChatResponse(reply=reply, commentary=commentary or None)


@app.post("/siri", response_model=ChatResponse)
async def siri(req: SiriRequest):
    async with _lock:
        messages = _state["messages"]
        pending = _state["pending_question"]
        if pending:
            messages.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": pending["tool_use_id"], "content": req.message}]
            })
            _state["pending_question"] = None
        else:
            messages.append({"role": "user", "content": req.message})

        reply, commentary, question, tool_use_id = await asyncio.to_thread(
            run_agent_turn,
            _state["claude"],
            _state["spotify"],
            _state["voice"],
            messages,
            False,
        )

        if question:
            _state["pending_question"] = {"tool_use_id": tool_use_id}
            reply = question

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        dj_says = commentary or reply
        text = f"🎤 *Via Siri:* {req.message}\n\n{dj_says}" if dj_says else f"🎤 *Via Siri:* {req.message}"
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            )

    return ChatResponse(reply=reply, commentary=commentary or None, question=question if question else None)


@app.get("/status")
async def status():
    spotify: SpotifyController = _state.get("spotify")
    if not spotify:
        raise HTTPException(status_code=503, detail="Server not ready")
    import json
    return json.loads(spotify.currently_playing())


def main():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000)
