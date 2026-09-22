from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Config:
    root: Path
    raw: dict
    @classmethod
    def load(cls, path: str | Path = "config.json") -> "Config":
        p = Path(path).resolve()
        data = json.loads(p.read_text(encoding="utf-8"))
        root = p.parent
        for key in ("db_dir", "temp_dir", "songs_dir"):
            data.setdefault("paths", {}).setdefault(key, key.replace("_dir", ""))
        return cls(root, data)
    def path(self, key: str) -> Path:
        p = self.raw["paths"][key]
        out = self.root / p
        out.mkdir(parents=True, exist_ok=True)
        return out
    @property
    def spotify(self): return self.raw["spotify"]
    @property
    def processing(self): return self.raw["processing"]
    @property
    def genius(self): return self.raw.get("genius", {})
