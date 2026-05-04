"""Telegram bot client for DJ Claude — bridges Telegram messages to the DJ server."""

import logging
import os

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🎧 DJ Claude here — your AI-powered personal radio DJ.\n\n"
        "Tell me what you want to hear and I'll take care of the rest.\n"
        "Use /status to see what's currently playing."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{SERVER_URL}/status", timeout=10)
            r.raise_for_status()
            data = r.json()
        except httpx.ConnectError:
            await update.message.reply_text(
                f"❌ Could not connect to the DJ server at {SERVER_URL}.\n"
                "Make sure it's running: `ai-dj-server`"
            )
            return
        except httpx.HTTPStatusError as e:
            await update.message.reply_text(f"❌ Server error: {e.response.status_code}")
            return

    track = data.get("item")
    if not track:
        await update.message.reply_text("Nothing playing right now.")
        return

    name = track.get("name", "Unknown")
    artists = ", ".join(a["name"] for a in track.get("artists", []))
    album = track.get("album", {}).get("name", "")
    await update.message.reply_text(f"🎵 Now playing: *{name}* by {artists}\n_{album}_", parse_mode="Markdown")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message.text
    await update.message.chat.send_action("typing")

    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                f"{SERVER_URL}/chat",
                json={"message": message, "voice": False},
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
        except httpx.ConnectError:
            await update.message.reply_text(
                f"❌ Could not connect to the DJ server at {SERVER_URL}.\n"
                "Make sure it's running: `ai-dj-server`"
            )
            return
        except httpx.HTTPStatusError as e:
            await update.message.reply_text(f"❌ Server error: {e.response.status_code}")
            return
        except httpx.ReadTimeout:
            await update.message.reply_text("❌ Request timed out — the DJ is taking too long.")
            return

    reply = data.get("reply", "")
    if reply:
        await update.message.reply_text(reply)


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logger.info("DJ Claude Telegram bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
