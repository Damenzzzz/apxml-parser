import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config, db as store, fetcher, parsers


def fetch_all(urls, workers):
    pool = ThreadPoolExecutor(workers)
    futures = {pool.submit(fetcher.get, url): url for url in urls}
    try:
        for future in as_completed(futures):
            yield futures[future], future.result()
    finally:
        pool.shutdown(cancel_futures=True)


def catalog(db, max_pages):
    seen = set()
    for number, html in fetcher.catalog_pages(max_pages):
        new = [c for c in parsers.parse_catalog(html) if c["slug"] not in seen]
        if not new:
            break
        for course in new:
            store.save_catalog_course(db, course)
            seen.add(course["slug"])
            save_cover(db, course)
        print(f"page {number}: {len(new)} courses")
    print(f"catalog done: {len(seen)} courses")


def save_cover(db, course):
    if not course["cover_url"]:
        return
    extension = course["cover_url"].split("?")[0].rsplit(".", 1)[-1]
    path = config.COVERS_DIR / f"{course['slug']}.{extension}"
    if path.exists() or fetcher.download(course["cover_url"], path):
        store.set_cover(db, course["slug"], path)


def courses(db, limit, slug, workers):
    if slug:
        slugs = [slug]
    else:
        rows = db.execute(
            "SELECT slug FROM courses WHERE status IN ('pending', 'error') LIMIT ?",
            (limit or -1,),
        )
        slugs = [row["slug"] for row in rows]

    urls = {f"{config.BASE_URL}/courses/{s}": s for s in slugs}
    for i, (url, html) in enumerate(fetch_all(urls, workers), 1):
        course_slug = urls[url]
        if html is None:
            store.set_status(db, "courses", "slug", course_slug, "error")
            print(f"[{i}/{len(urls)}] {course_slug}: error")
            continue

        course = parsers.parse_course(html, course_slug)
        store.save_course(db, course_slug, course)
        lessons = sum(len(ch["lessons"]) for ch in course["chapters"])
        print(f"[{i}/{len(urls)}] {course_slug}: {len(course['chapters'])} chapters, {lessons} lessons")


def lessons(db, limit, course, workers):
    query = "SELECT url FROM lessons WHERE status IN ('pending', 'error')"
    params = []
    if course:
        query += " AND course_slug = ?"
        params.append(course)
    query += " LIMIT ?"
    params.append(limit or -1)

    urls = [row["url"] for row in db.execute(query, params)]
    total = len(urls)
    errors = 0
    for i, (url, html) in enumerate(fetch_all(urls, workers), 1):
        if html is None:
            store.set_status(db, "lessons", "url", url, "error")
            errors += 1
        else:
            store.save_lesson(db, url, parsers.parse_lesson(html))
        if i % 50 == 0 or i == total:
            print(f"{i}/{total} lessons, errors: {errors}")


def extract(db):
    rows = db.execute("SELECT id, content_html FROM lessons WHERE status = 'done'").fetchall()
    total = 0
    for i, row in enumerate(rows, 1):
        blocks = parsers.parse_blocks(row["content_html"])
        store.save_blocks(db, row["id"], blocks)
        total += len(blocks)
        if i % 500 == 0 or i == len(rows):
            print(f"{i}/{len(rows)} lessons, {total} blocks")


def stats(db):
    for table in ("courses", "lessons"):
        rows = db.execute(f"SELECT status, COUNT(*) AS n FROM {table} GROUP BY status")
        print(table + ":", ", ".join(f"{row['status']}={row['n']}" for row in rows) or "empty")
    rows = db.execute("SELECT kind, COUNT(*) AS n FROM blocks GROUP BY kind")
    print("blocks:", ", ".join(f"{row['kind']}={row['n']}" for row in rows) or "empty")
    chapters = db.execute("SELECT COUNT(*) FROM chapters").fetchone()[0]
    covers = db.execute("SELECT COUNT(*) FROM courses WHERE cover_path IS NOT NULL").fetchone()[0]
    words = db.execute("SELECT COALESCE(SUM(word_count), 0) FROM lessons").fetchone()[0]
    print(f"chapters: {chapters}")
    print(f"covers: {covers}")
    print(f"words: {words}")


def export(db, out):
    rows = db.execute(
        """
        SELECT l.id, c.title AS course, c.category, c.level, ch.title AS chapter,
               l.title, l.url, l.description, l.content_text
        FROM lessons l
        JOIN chapters ch ON ch.id = l.chapter_id
        JOIN courses c ON c.slug = l.course_slug
        WHERE l.status = 'done'
        ORDER BY c.slug, ch.position, l.position
        """
    ).fetchall()
    out.parent.mkdir(exist_ok=True)
    count = 0
    with open(out, "w", encoding="utf-8") as f:
        for row in rows:
            lesson = dict(row)
            blocks = db.execute(
                "SELECT kind, language, content, caption FROM blocks WHERE lesson_id = ? ORDER BY position",
                (lesson.pop("id"),),
            )
            lesson["blocks"] = [dict(block) for block in blocks]
            f.write(json.dumps(lesson, ensure_ascii=False) + "\n")
            count += 1
    print(f"exported {count} lessons to {out}")
