from src.config import Config
from src.db import init_dbs, connect
from src.pipeline import Pipeline


def main():
    cfg = Config.load()
    init_dbs(cfg.path("db_dir"))
    pipe = Pipeline(cfg)

    print("=" * 90)
    print("CANONICAL SONG + TELUGU ENHANCED LRC — PHASE 1")
    print("=" * 90)

    added = pipe.ingest()
    print(f"New playlist entries: {len(added)}")

    rows = pipe.pending()
    print(f"Pending entries: {len(rows)}")

    # Each song is isolated. An error is recorded for that serial and does not
    # stop the remaining pending songs from being attempted.
    for row in rows:
        pipe.process(row)


if __name__ == "__main__":
    main()
