from __future__ import annotations
import hashlib
import json
import sqlite3
from pathlib import Path

class ResponseCache:
    def __init__(self, cache_dir: Path | None = None):
        if cache_dir is None:
            cache_dir = Path(__file__).resolve().parent / ".cache"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "vlm_cache.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    response TEXT
                )
            """)
            conn.commit()

    def _make_key(self, prompt: str, image_paths: list[str] | None = None) -> str:
        hasher = hashlib.md5(prompt.encode("utf-8"))
        if image_paths:
            for path in sorted(image_paths):
                hasher.update(path.encode("utf-8"))
                # If image exists, hash its size and modification time for cache invalidation on changes
                p = Path(path)
                if p.exists():
                    stat = p.stat()
                    hasher.update(str(stat.st_size).encode("utf-8"))
                    hasher.update(str(stat.st_mtime).encode("utf-8"))
        return hasher.hexdigest()

    def get(self, prompt: str, image_paths: list[str] | None = None) -> str | None:
        key = self._make_key(prompt, image_paths)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT response FROM cache WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row[0]
        return None

    def set(self, prompt: str, response: str, image_paths: list[str] | None = None):
        key = self._make_key(prompt, image_paths)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO cache (key, response) VALUES (?, ?)", (key, response))
            conn.commit()
