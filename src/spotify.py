from __future__ import annotations

from typing import Any

from .db import connect, next_serial


class SpotifyClient:
    """Spotify playlist client compatible with the current playlist-items schema.

    Spotify's playlist-items endpoint currently returns playlist entries with the
    actual track/episode under ``entry['item']``. Older Spotipy/API combinations
    exposed the same object under ``entry['track']``. We accept both shapes so
    the ingestion layer is resilient, while preferring the current ``item`` key.
    """

    def __init__(self, cfg):
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth

        s = cfg.spotify
        self.playlist_id = s["playlist_id"]
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=s["client_id"],
                client_secret=s["client_secret"],
                redirect_uri=s.get("redirect_uri", "http://127.0.0.1:8888/callback"),
                scope=s.get(
                    "scope",
                    "playlist-read-private playlist-read-collaborative",
                ),
                cache_path=str(cfg.root / ".spotify_cache"),
            )
        )

    @staticmethod
    def _extract_track(entry: dict[str, Any]) -> dict[str, Any] | None:
        """Return the actual Spotify track object from a playlist entry.

        Current Spotify responses use ``entry['item']``. The legacy fallback is
        deliberately retained because some Spotipy versions/API responses used
        ``entry['track']``. Note that in the current response the *track object's*
        ``track`` field is a boolean, so ``entry.get('track')`` must not be used
        as the primary extraction path.
        """
        item = entry.get("item")
        if isinstance(item, dict):
            if item.get("type") == "track" or item.get("id"):
                return item
            return None

        legacy = entry.get("track")
        if isinstance(legacy, dict):
            if legacy.get("type") in (None, "track"):
                return legacy
        return None

    def fetch_all(self) -> list[dict[str, Any]]:
        """Fetch every playlist entry in exact Spotify order.

        We intentionally do not depend on a fragile ``fields=`` projection here.
        The current Spotify API uses ``item`` instead of the older ``track`` key;
        requesting the complete page also makes this code tolerant of small API
        response-shape changes.
        """
        rows: list[dict[str, Any]] = []
        offset = 0
        page_size = 100
        total: int | None = None

        while True:
            page = self.sp.playlist_items(
                self.playlist_id,
                offset=offset,
                limit=page_size,
            )
            if not isinstance(page, dict):
                raise RuntimeError("Spotify playlist_items returned an invalid response")

            items = page.get("items") or []
            if total is None:
                total = page.get("total")

            rows.extend(items)

            # Prefer Spotify's next URL when present. If it is absent, the page
            # is complete. The fallback protects against wrappers that omit next.
            if not page.get("next"):
                break
            if not items:
                raise RuntimeError(
                    "Spotify returned a next page but the current page contained no items"
                )
            offset += len(items)

        if total is not None and len(rows) < int(total):
            raise RuntimeError(
                f"Spotify pagination incomplete: fetched {len(rows)} of {total} playlist entries"
            )

        return rows

    def ingest(self, db_path):
        c = connect(db_path)
        try:
            rows = self.fetch_all()
            existing = {
                r["spotify_id"]
                for r in c.execute(
                    "SELECT spotify_id FROM playlist_entries WHERE spotify_playlist_id=?",
                    (self.playlist_id,),
                )
            }

            serial = next_serial(c)
            added: list[int] = []
            skipped_unavailable = 0
            skipped_non_track = 0
            skipped_existing = 0

            for entry_number, entry in enumerate(rows, 1):
                track = self._extract_track(entry)

                if track is None:
                    # Playlist entries can be unavailable/deleted or can refer to
                    # unsupported item types such as episodes. They are not songs.
                    raw_item = entry.get("item") if isinstance(entry, dict) else None
                    if isinstance(raw_item, dict) and raw_item.get("type") not in (
                        None,
                        "track",
                    ):
                        skipped_non_track += 1
                    else:
                        skipped_unavailable += 1
                    continue

                spotify_id = track.get("id")
                if not spotify_id:
                    skipped_unavailable += 1
                    continue

                if spotify_id in existing:
                    skipped_existing += 1
                    continue

                artists = track.get("artists") or []
                artist = ", ".join(
                    a.get("name", "") for a in artists if isinstance(a, dict) and a.get("name")
                )
                album = track.get("album") or {}
                isrc = (track.get("external_ids") or {}).get("isrc")

                c.execute(
                    """INSERT INTO playlist_entries(
                        serial_number, spotify_playlist_id,
                        spotify_playlist_entry_number, spotify_id,
                        title, artist, album, isrc, status
                    ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        serial,
                        self.playlist_id,
                        entry_number,
                        spotify_id,
                        track.get("name", ""),
                        artist,
                        album.get("name"),
                        isrc,
                        "pending",
                    ),
                )
                added.append(serial)
                existing.add(spotify_id)
                serial += 1

            c.commit()
            print(
                "Spotify sync: "
                f"fetched={len(rows)}, new={len(added)}, "
                f"existing={skipped_existing}, unavailable={skipped_unavailable}, "
                f"non_track={skipped_non_track}"
            )
            return added
        finally:
            c.close()

    def metadata(self, spotify_id):
        t = self.sp.track(spotify_id)
        a = t.get("album") or {}
        arts = t.get("artists") or []
        return {
            "spotify_id": spotify_id,
            "title": t.get("name", ""),
            "artist": ", ".join(x["name"] for x in arts),
            "album": a.get("name"),
            "album_artist": ", ".join(x["name"] for x in a.get("artists", arts)),
            "release_date": a.get("release_date"),
            "duration": round((t.get("duration_ms") or 0) / 1000),
            "spotify_url": (t.get("external_urls") or {}).get("spotify"),
            "isrc": (t.get("external_ids") or {}).get("isrc"),
            "artwork_url": ((a.get("images") or [{}])[0]).get("url"),
        }
