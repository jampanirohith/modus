from src.config import Config
from src.db import init_dbs
if __name__=="__main__":
    c=Config.load(); init_dbs(c.path("db_dir")); print("Initialized db/playlist.db and db/songs.db")
