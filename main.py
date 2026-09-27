from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.config import load_config
from src.db import Database
from src.doctor import doctor
from src.pipeline import Pipeline
from src.recovery import RecoveryManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Standalone Phase 2 Telugu word-level lyric synchronisation pipeline"
    )
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--all", action="store_true", help="Process all discovered song packages")
    parser.add_argument("--song", action="append", default=[], help="Process one basename; repeatable")
    parser.add_argument("--failed", action="store_true", help="Process songs with failed quality status")
    parser.add_argument("--needs-review", action="store_true", help="Process songs marked needs_review")
    parser.add_argument("--partial", action="store_true", help="Process songs marked partial")
    parser.add_argument("--force", action="store_true", help="Discard Phase 2 checkpoint data and rebuild")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report without heavy processing")
    parser.add_argument("--scan-only", action="store_true", help="Scan and show package matching without processing")
    parser.add_argument("--recover", action="store_true", help="Reset stale in-progress DB states to pending")
    parser.add_argument("--doctor", action="store_true", help="Check Python packages, CUDA, ffmpeg and ffprobe")
    parser.add_argument("--reconcile", "--repair-state", dest="reconcile", action="store_true", help="Reconcile final outputs with phase2.db")
    parser.add_argument("--backup-db", metavar="PATH", help="Create an SQLite backup and exit")
    parser.add_argument("--debug", action="store_true", help="Keep extra debug logging")
    parser.add_argument("--keep-temp", action="store_true", help="Do not delete per-song temp data after success")
    parser.add_argument("--allow-cpu-fallback", action="store_true", help="Allow Demucs/MMS to fall back to CPU when CUDA is unavailable or fails (not recommended for production GPU runs)")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of packages to process")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.doctor:
        print(json.dumps(doctor(), indent=2, ensure_ascii=False))
        return 0

    config = load_config(args.config)
    db_path = config.path("paths.db_dir") / "phase2.db"
    db = Database(db_path)
    try:
        if args.backup_db:
            db.backup(Path(args.backup_db))
            print(f"Database backup written: {args.backup_db}")
            return 0
        if args.reconcile:
            result = RecoveryManager(db, int(config.get("recovery.stale_after_minutes", 30))).reconcile(config.path("paths.final_dir"))
            print(json.dumps(result, indent=2))
            return 0
        if args.recover:
            count = RecoveryManager(
                db,
                int(config.get("recovery.stale_after_minutes", 30)),
            ).mark_stale_as_pending()
            print(f"Recovered stale songs: {count}")

        pipeline = Pipeline(config, db, allow_cpu_fallback=args.allow_cpu_fallback)
        packages, issues = pipeline.scan()
        print(f"Discovered packages: {len(packages)}")
        if issues:
            for issue in issues:
                print(f"SCAN {issue.severity.upper()}: {issue.basename}: {issue.issue}")

        if args.scan_only:
            for package in packages:
                print(package.basename)
            return 0

        basenames = set(args.song) if args.song else None
        quality = None
        selected_flags = sum(bool(x) for x in (args.failed, args.needs_review, args.partial))
        if selected_flags > 1:
            parser.error("Use only one quality selector: --failed, --needs-review, or --partial")
        if args.failed:
            quality = "failed"
        elif args.needs_review:
            quality = "needs_review"
        elif args.partial:
            quality = "partial"

        if not (args.all or basenames or quality or args.dry_run):
            parser.error("Specify --all, --song, --failed, --needs-review, --partial, or --dry-run")

        counts = pipeline.process_all(
            force=args.force,
            debug=args.debug,
            keep_temp=args.keep_temp,
            dry_run=args.dry_run,
            basenames=basenames,
            quality=quality,
            limit=args.limit,
        )
        print(json.dumps(counts, indent=2, ensure_ascii=False))
        return 0 if counts.get("failed", 0) == 0 else 2
    finally:
        db.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("INTERRUPTED: current song was not promoted; rerun the same command to resume from the last safe checkpoint.")
        raise SystemExit(130)
