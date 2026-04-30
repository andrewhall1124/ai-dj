"""Spotify Web API wrapper used by the DJ agent."""

import json
import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from config import SPOTIFY_SCOPES


class SpotifyController:
    def __init__(self):
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback"),
            scope=SPOTIFY_SCOPES,
            cache_path=".spotify_cache"
        ))
        self.device_id = None

    def ensure_active_device(self) -> str:
        """Find an active Spotify device, waking one up if needed. Returns the device id."""
        devices = self.sp.devices().get("devices", [])
        if not devices or len(devices) == 0:
            raise RuntimeError(
                "No Spotify devices found. Open Spotify on a phone, desktop, or web player first."
            )
        self.device_id = devices[0]['id']

    def search(self, query: str, search_type: str = "track", limit: int = 5) -> str:
        results = self.sp.search(q=query, type=search_type, limit=limit)
        key = f"{search_type}s"
        items = results[key]["items"]
        if not items:
            return json.dumps({"results": [], "message": "No results found"})

        formatted = []
        for item in items:
            if search_type == "track":
                formatted.append({
                    "name": item["name"],
                    "artist": ", ".join(a["name"] for a in item["artists"]),
                    "album": item["album"]["name"],
                    "uri": item["uri"],
                    "id": item["id"],
                    "duration_ms": item["duration_ms"]
                })
            elif search_type == "artist":
                formatted.append({
                    "name": item["name"],
                    "genres": item.get("genres", []),
                    "uri": item["uri"],
                    "id": item["id"]
                })
            elif search_type == "album":
                formatted.append({
                    "name": item["name"],
                    "artist": ", ".join(a["name"] for a in item["artists"]),
                    "uri": item["uri"],
                    "id": item["id"]
                })
        return json.dumps({"results": formatted})

    def play(self, track_uri: str = None) -> str:
        try:
            self.ensure_active_device()
            if track_uri:
                self.sp.start_playback(device_id=self.device_id, uris=[track_uri])
                return json.dumps({"status": "playing", "track_uri": track_uri})
            else:
                self.sp.start_playback(device_id=self.device_id)
                return json.dumps({"status": "resumed"})
        except spotipy.exceptions.SpotifyException as e:
            return json.dumps({"error": str(e)})

    def add_to_queue(self, track_uri: str) -> str:
        try:
            self.ensure_active_device()
            self.sp.add_to_queue(track_uri, device_id=self.device_id)
            return json.dumps({"status": "queued", "track_uri": track_uri})
        except spotipy.exceptions.SpotifyException as e:
            return json.dumps({"error": str(e)})

    def skip(self) -> str:
        try:
            self.ensure_active_device()
            self.sp.next_track(device_id=self.device_id)
            return json.dumps({"status": "skipped"})
        except spotipy.exceptions.SpotifyException as e:
            return json.dumps({"error": str(e)})

    def clear_queue(self) -> str:
        try:
            self.ensure_active_device()
            playback = self.sp.current_playback()
            prior_volume = (playback or {}).get("device", {}).get("volume_percent")
            if prior_volume is None:
                prior_volume = 50
            try:
                self.sp.volume(0, device_id=self.device_id)
            except spotipy.exceptions.SpotifyException:
                pass  # some devices reject volume control; clear anyway
            try:
                queue = self.sp.queue()
                for _ in queue["queue"]:
                    self.sp.next_track()
            finally:
                try:
                    self.sp.volume(prior_volume, device_id=self.device_id)
                except spotipy.exceptions.SpotifyException:
                    pass
            return json.dumps({"status": "queue_cleared", "restored_volume": prior_volume})
        except spotipy.exceptions.SpotifyException as e:
            return json.dumps({"error": str(e)})

    def currently_playing(self) -> str:
        current = self.sp.current_playback()
        if not current or not current.get("item"):
            return json.dumps({"status": "nothing_playing"})
        track = current["item"]
        return json.dumps({
            "name": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "album": track["album"]["name"],
            "uri": track["uri"],
            "id": track["id"],
            "is_playing": current["is_playing"],
            "progress_ms": current["progress_ms"],
            "duration_ms": track["duration_ms"]
        })

    def pause(self) -> str:
        try:
            self.sp.pause_playback(device_id=self.device_id)
            return json.dumps({"status": "paused"})
        except spotipy.exceptions.SpotifyException as e:
            return json.dumps({"error": str(e)})

    def volume(self, volume_percent: int) -> str:
        try:
            self.ensure_active_device()
            volume_percent = max(0, min(100, int(volume_percent)))
            self.sp.volume(volume_percent, device_id=self.device_id)
            return json.dumps({"status": "volume_set", "volume_percent": volume_percent})
        except spotipy.exceptions.SpotifyException as e:
            return json.dumps({"error": str(e)})
