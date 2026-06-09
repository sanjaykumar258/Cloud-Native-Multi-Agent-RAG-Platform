import json
import hashlib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

CACHE_DIR = Path("./.brain_cache")
VISION_CACHE = CACHE_DIR / "vision_cache.json"

def get_file_hash(path: Path | str) -> str:
    """Get MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(path, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

class BrainCache:
    def __init__(self):
        CACHE_DIR.mkdir(exist_ok=True)
        self.data = {}
        if VISION_CACHE.exists():
            try:
                with open(VISION_CACHE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error("Failed to load cache: %s", e)

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def set(self, key: str, value: str):
        self.data[key] = value
        try:
            with open(VISION_CACHE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save cache: %s", e)

# Global singleton
cache = BrainCache()
