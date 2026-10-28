from pathlib import Path

BASE_URL = "https://apxml.com"
DB_PATH = Path("data/apxml.db")
EXPORT_PATH = Path("data/lessons.jsonl")
COVERS_DIR = Path("data/images/covers")
FILES_DIR = Path("data/courses")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

WORKERS = 4
DELAY = 0.3
RETRIES = 3
TIMEOUT = 30
