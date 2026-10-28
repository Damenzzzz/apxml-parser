import argparse
from pathlib import Path

from . import commands, config, db as store


def build_parser():
    parser = argparse.ArgumentParser(prog="apxml", description="apxml.com courses parser")
    sub = parser.add_subparsers(dest="command", required=True)

    catalog = sub.add_parser("catalog", help="list of courses (Playwright)")
    catalog.add_argument("--max-pages", type=int, default=50)

    courses = sub.add_parser("courses", help="chapters and lessons of each course (httpx)")
    courses.add_argument("--limit", type=int)
    courses.add_argument("--slug")
    courses.add_argument("--workers", type=int, default=config.WORKERS)

    lessons = sub.add_parser("lessons", help="lesson texts (httpx)")
    lessons.add_argument("--limit", type=int)
    lessons.add_argument("--course")
    lessons.add_argument("--workers", type=int, default=config.WORKERS)

    sub.add_parser("stats", help="what is already in the database")

    export = sub.add_parser("export", help="lessons to JSONL")
    export.add_argument("--out", type=Path, default=config.EXPORT_PATH)
    return parser


def main():
    args = build_parser().parse_args()
    db = store.connect()
    try:
        if args.command == "catalog":
            commands.catalog(db, args.max_pages)
        elif args.command == "courses":
            commands.courses(db, args.limit, args.slug, args.workers)
        elif args.command == "lessons":
            commands.lessons(db, args.limit, args.course, args.workers)
        elif args.command == "stats":
            commands.stats(db)
        elif args.command == "export":
            commands.export(db, args.out)
    except KeyboardInterrupt:
        print("stopped")
    finally:
        db.close()


if __name__ == "__main__":
    main()
