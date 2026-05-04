# AI-DJ
Curate your music on Spotify with DJ Claude.

## Usage

Install the package:

```bash
pip install ai-dj
```

Add the required environment variables to your shell RC file (e.g. `~/.bashrc` or `~/.zshrc`):

```bash
export ANTHROPIC_API_KEY=...
export SPOTIFY_CLIENT_ID=...
export SPOTIFY_CLIENT_SECRET=...
export ELEVENLABS_API_KEY=...
# Optional
export SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
export ELEVENLABS_VOICE_ID=JBFqnCBsd6RMkjVDRZzb
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
export SERVER_URL=http://localhost:8000
```

## Development

Clone the repo and install in editable mode:

```bash
pip install -e .
```

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key for Claude |
| `SPOTIFY_CLIENT_ID` | Yes | — | Spotify app client ID |
| `SPOTIFY_CLIENT_SECRET` | Yes | — | Spotify app client secret |
| `SPOTIFY_REDIRECT_URI` | No | `http://localhost:8888/callback` | OAuth redirect URI |
| `ELEVENLABS_API_KEY` | Yes | — | ElevenLabs API key for DJ voice |
| `ELEVENLABS_VOICE_ID` | No | `JBFqnCBsd6RMkjVDRZzb` | ElevenLabs voice ID |
| `TELEGRAM_BOT_TOKEN` | For Telegram | — | Telegram bot token from BotFather |
| `TELEGRAM_CHAT_ID` | For Telegram (server) | — | Telegram chat ID to send notifications to |
| `SERVER_URL` | For Telegram bot | `http://localhost:8000` | URL of the AI-DJ server |

## Commands

### Entry Points

| Command | Description |
|---|---|
| `ai-dj` | Launch the terminal UI client |
| `ai-dj-server` | Start the FastAPI server |
| `ai-dj-telegram` | Start the Telegram bot |

### Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Show welcome message and usage instructions |
| `/status` | Show currently playing track |
| *(any text)* | Send a request to the DJ agent |

### Server API Endpoints

| Endpoint | Description |
|---|---|
| `POST /chat` | Send a message to the DJ agent |
| `POST /siri` | Process Siri voice input through the DJ agent |
| `GET /status` | Get currently playing track info |
