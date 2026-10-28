import csv
import html
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

CHART_PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body>
<div id="chart"></div>
<p>{caption}</p>
<script>
const figure = {figure};
Plotly.newPlot("chart", figure.data, figure.layout);
</script>
</body>
</html>
"""

DIAGRAM_PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/@viz-js/viz@3.11.0/lib/viz-standalone.js"></script>
</head>
<body>
<div id="diagram"></div>
<p>{caption}</p>
<script>
const dot = {dot};
Viz.instance().then(viz => document.getElementById("diagram").appendChild(viz.renderSVGElement(dot)));
</script>
</body>
</html>
"""


def folder_name(position, slug):
    return f"{position:02d}-{slug}"


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
        title = html.escape(lesson["title"])
        caption = html.escape(block["caption"] or "")

        if kind == "code":
            extension = EXTENSIONS.get(block["language"], "txt")
            (folder / f"{name}.{extension}").write_text(block["content"] + "\n", encoding="utf-8")
        elif kind == "chart":
            page = CHART_PAGE.format(title=title, caption=caption, figure=block["content"])
            (folder / f"{name}.html").write_text(page, encoding="utf-8")
        elif kind == "diagram":
            page = DIAGRAM_PAGE.format(title=title, caption=caption, dot=json.dumps(block["content"]))
            (folder / f"{name}.html").write_text(page, encoding="utf-8")
        elif kind == "table":
            with open(folder / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(json.loads(block["content"]))
