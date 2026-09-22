from pathlib import Path

from src.db import connect, init_dbs
from src.spotify import SpotifyClient


class FakeSpotify:
    def __init__(self, pages):
        self.pages = pages

    def playlist_items(self, playlist_id, offset=0, limit=100):
        return self.pages[offset]


def make_client(pages):
    obj = object.__new__(SpotifyClient)
    obj.playlist_id = "playlist-1"
    obj.sp = FakeSpotify(pages)
    return obj


def test_extracts_current_item_shape():
    entry = {
        "item": {
            "id": "track-1",
            "type": "track",
            "track": True,
            "name": "Urike Urike",
            "artists": [{"name": "Sid Sriram"}],
            "album": {"name": "Hit 2"},
            "duration_ms": 1000,
            "external_ids": {"isrc": "INH102216408"},
        }
    }
    track = SpotifyClient._extract_track(entry)
    assert track["id"] == "track-1"
    assert track["name"] == "Urike Urike"
    assert track["external_ids"]["isrc"] == "INH102216408"


def test_legacy_track_shape_still_supported():
    entry = {"track": {"id": "track-old", "type": "track", "name": "Old"}}
    assert SpotifyClient._extract_track(entry)["id"] == "track-old"


def test_current_playlist_response_ingests_all_pages(tmp_path: Path):
    pages = {
        0: {
            "items": [
                {
                    "item": {
                        "id": "track-1",
                        "type": "track",
                        "name": "Urike Urike",
                        "artists": [{"name": "Sid Sriram"}],
                        "album": {"name": "Hit 2"},
                        "external_ids": {"isrc": "INH102216408"},
                    }
                },
                {
                    "item": {
                        "id": "track-2",
                        "type": "track",
                        "name": "Nuvvu Navvukuntu",
                        "artists": [{"name": "Artist 2"}],
                        "album": {"name": "Album 2"},
                        "external_ids": {"isrc": "INA092318852"},
                    }
                },
            ],
            "next": "page-2",
            "total": 3,
        },
        2: {
            "items": [
                {"item": None},
            ],
            "next": None,
            "total": 3,
        },
    }

    # Replace the second page with a real third track so the test verifies
    # pagination without requiring a real Spotify account.
    pages[2]["items"] = [
        {
            "item": {
                "id": "track-3",
                "type": "track",
                "name": "Mastaaru Mastaaru",
                "artists": [{"name": "Artist 3"}],
                "album": {"name": "Album 3"},
                "external_ids": {"isrc": "INA092218296"},
            }
        }
    ]

    client = make_client(pages)
    db = tmp_path / "playlist.db"
    init_dbs(tmp_path)
    added = client.ingest(db)

    assert added == [1, 2, 3]
    c = connect(db)
    rows = c.execute(
        "SELECT serial_number, spotify_playlist_entry_number, spotify_id, title, status "
        "FROM playlist_entries ORDER BY serial_number"
    ).fetchall()
    c.close()

    assert [(r["serial_number"], r["spotify_playlist_entry_number"], r["spotify_id"]) for r in rows] == [
        (1, 1, "track-1"),
        (2, 2, "track-2"),
        (3, 3, "track-3"),
    ]
    assert all(r["status"] == "pending" for r in rows)
