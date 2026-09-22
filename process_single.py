import argparse
from src.config import Config
from src.db import init_dbs, connect
from src.pipeline import Pipeline

def main():
    ap=argparse.ArgumentParser(description="Retry one failed Phase 1 song")
    ap.add_argument("serial",type=int); args=ap.parse_args(); cfg=Config.load(); init_dbs(cfg.path("db_dir")); pipe=Pipeline(cfg)
    c=connect(cfg.path("db_dir")/"playlist.db"); row=c.execute("SELECT * FROM playlist_entries WHERE serial_number=?",(args.serial,)).fetchone(); c.close()
    if not row: raise SystemExit(f"Serial {args.serial} not found")
    print(f"Previous status: {row['status']}")
    if row["error_remark"]: print(row["error_remark"])
    pipe.process(row,reset=True)
if __name__=="__main__": main()
