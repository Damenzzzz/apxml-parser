import sqlite3
from datetime import datetime

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (
    slug TEXT PRIMARY KEY,
    title TEXT,
    short_description TEXT,
    description TEXT,
    category TEXT,
    level TEXT,
    duration_hours INTEGER,
    prerequisites TEXT,
    instructor TEXT,
    is_free INTEGER,
    url TEXT,
    status TEXT DEFAULT 'pending',
    scraped_at TEXT
);

CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_slug TEXT REFERENCES courses(slug),
    position INTEGER,
    slug TEXT,
    title TEXT,
    url TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id INTEGER REFERENCES chapters(id),
    course_slug TEXT REFERENCES courses(slug),
    position INTEGER,
    slug TEXT,
    title TEXT,
    url TEXT UNIQUE,
    description TEXT,
    content_html TEXT,
    content_text TEXT,
    word_count INTEGER,
    status TEXT DEFAULT 'pending',
    fetched_at TEXT
);
"""


def now():
    return datetime.now().isoformat(timespec="seconds")


def connect():
    config.DB_PATH.parent.mkdir(exist_ok=True)
    db = sqlite3.connect(config.DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(SCHEMA)
    return db


def save_catalog_course(db, course):
    db.execute(
        """
        INSERT INTO courses (slug, title, short_description, category, level,
                             duration_hours, prerequisites, url)
        VALUES (:slug, :title, :short_description, :category, :level,
                :duration_hours, :prerequisites, :url)
        ON CONFLICT(slug) DO UPDATE SET
            title = excluded.title,
            short_description = excluded.short_description,
            category = excluded.category,
            level = excluded.level,
            duration_hours = excluded.duration_hours,
            prerequisites = excluded.prerequisites
        """,
        course,
    )
    db.commit()


def save_course(db, slug, course):
    db.execute(
        "INSERT OR IGNORE INTO courses (slug, title, url) VALUES (?, ?, ?)",
        (slug, course["title"], f"{config.BASE_URL}/courses/{slug}"),
    )
    db.execute(
        """
        UPDATE courses
        SET description = ?, instructor = ?, is_free = ?, status = 'done', scraped_at = ?
        WHERE slug = ?
        """,
        (course["description"], course["instructor"], course["is_free"], now(), slug),
    )

    for chapter_pos, chapter in enumerate(course["chapters"], 1):
        db.execute(
            """
            INSERT INTO chapters (course_slug, position, slug, title, url)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET position = excluded.position, title = excluded.title
            """,
            (slug, chapter_pos, chapter["slug"], chapter["title"], chapter["url"]),
        )
        chapter_id = db.execute("SELECT id FROM chapters WHERE url = ?", (chapter["url"],)).fetchone()[0]

        for lesson_pos, lesson in enumerate(chapter["lessons"], 1):
            db.execute(
                """
                INSERT OR IGNORE INTO lessons (chapter_id, course_slug, position, slug, title, url)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (chapter_id, slug, lesson_pos, lesson["slug"], lesson["title"], lesson["url"]),
            )
    db.commit()


def save_lesson(db, url, lesson):
    status = "done" if lesson["content_text"] else "empty"
    db.execute(
        """
        UPDATE lessons
        SET title = COALESCE(?, title), description = ?, content_html = ?, content_text = ?,
            word_count = ?, status = ?, fetched_at = ?
        WHERE url = ?
        """,
        (lesson["title"], lesson["description"], lesson["content_html"], lesson["content_text"],
         lesson["word_count"], status, now(), url),
    )
    db.commit()


def set_status(db, table, column, value, status):
    db.execute(f"UPDATE {table} SET status = ? WHERE {column} = ?", (status, value))
    db.commit()
