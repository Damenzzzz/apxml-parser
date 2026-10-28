import csv
import json
import shutil
from pathlib import Path

from . import config

EXTENSIONS = {
    "python": "py", "bash": "sh", "sh": "sh", "shell": "sh", "julia": "jl",
    "sql": "sql", "json": "json", "yaml": "yaml", "dockerfile": "dockerfile",
    "java": "java", "cpp": "cpp", "c++": "cpp", "c": "c", "cuda": "cu",
    "markdown": "md", "csv": "csv", "toml": "toml", "html": "html", "xml": "xml",
    "typescript": "ts", "scala": "scala", "powershell": "ps1",
}

def folder_name(position, slug):
    return f"{position:02d}-{slug}"


def lesson_folder(lesson):
    return (config.FILES_DIR
            / lesson["course_slug"]
            / folder_name(lesson["chapter_position"], lesson["chapter_slug"])
            / folder_name(lesson["position"], lesson["slug"]))


def write_course(course):
    folder = config.FILES_DIR / course["slug"]
    folder.mkdir(parents=True, exist_ok=True)
    info = {key: course[key] for key in course.keys() if key not in ("status", "cover_path")}
    (folder / "course.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    if course["cover_path"] and Path(course["cover_path"]).exists():
        cover = Path(course["cover_path"])
        shutil.copy(cover, folder / f"cover{cover.suffix}")
    return folder


def write_lesson(folder, lesson, blocks):
    folder.mkdir(parents=True, exist_ok=True)
    text = f"# {lesson['title']}\n\n{lesson['url']}\n\n{lesson['content_text'] or ''}\n"
    (folder / "lesson.md").write_text(text, encoding="utf-8")

    counters = {}
    for block in blocks:
        kind = block["kind"]
        counters[kind] = counters.get(kind, 0) + 1
        name = f"{kind}_{counters[kind]:02d}"

        if kind == "code":
            extension = EXTENSIONS.get(block["language"], "txt")
            (folder / f"{name}.{extension}").write_text(block["content"] + "\n", encoding="utf-8")
        elif kind == "table":
            with open(folder / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(json.loads(block["content"]))
