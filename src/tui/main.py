"""
AI DJ TUI — terminal client for the DJ Claude server.

Usage:
    1. Start the server: uv run server
    2. python -m tui.main
"""

import sys

import httpx

SERVER_URL = "http://localhost:8000"


def check_server(client: httpx.Client) -> dict:
    try:
        r = client.get(f"{SERVER_URL}/status", timeout=5)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        print(f"  ❌ Could not connect to server at {SERVER_URL}")
        print("  Make sure the server is running: uv run server")
        sys.exit(1)


def send_message(client: httpx.Client, message: str) -> tuple[str, str | None]:
    r = client.post(
        f"{SERVER_URL}/chat",
        json={"message": message, "voice": True},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    return data["reply"], data.get("commentary")


def main():
    print("=" * 60)
    print("  🎧  DJ Claude  🎧")
    print("  Your AI-powered personal radio DJ")
    print("=" * 60)

    with httpx.Client() as client:
        print("\n  Connecting to server...")
        status = check_server(client)
        track = status.get("item", {})
        if track:
            artists = ", ".join(a["name"] for a in track.get("artists", []))
            print(f"  ✅ Server ready — now playing: {track['name']} by {artists}")
        else:
            print("  ✅ Server ready")

        print("\n  Type your requests, or 'quit' to exit.\n")

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

            print()
            try:
                reply, _ = send_message(client, user_input)
            except httpx.HTTPStatusError as e:
                print(f"  ❌ Server error: {e.response.status_code}\n")
                continue
            except httpx.RequestError as e:
                print(f"  ❌ Request failed: {e}\n")
                continue

            print(f"DJ Claude: {reply}\n")


if __name__ == "__main__":
    main()
