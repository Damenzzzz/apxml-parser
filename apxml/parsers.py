import json
import re

from selectolax.lexbor import LexborHTMLParser

from . import config


def to_int(text):
    match = re.search(r"\d+", text or "")
    return int(match.group()) if match else None


def json_ld(tree, kind):
    for script in tree.css('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.text())
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("@type") == kind:
            return data
    return {}


def parse_catalog(html):
    tree = LexborHTMLParser(html)
    courses = []
    for card in tree.css("div.mantine-Card-root"):
        link = card.css_first('a[href^="/courses/"]')
        title = card.css_first("h4")
        if not link or not title:
            continue

        parts = link.attributes["href"].strip("/").split("/")
        if len(parts) != 2 or parts[1] == "roadmap":
            continue

        badges = [b.text(strip=True) for b in card.css(".mantine-Badge-label")]
        description = card.css_first("p[data-line-clamp]")
        meta = [p.text(strip=True) for p in card.css("p[data-inherit]")]

        courses.append({
            "slug": parts[1],
            "title": title.text(strip=True),
            "short_description": description.text(strip=True) if description else None,
            "category": badges[0] if badges else None,
            "level": badges[1] if len(badges) > 1 else None,
            "duration_hours": to_int(meta[0]) if meta else None,
            "prerequisites": meta[1] if len(meta) > 1 else None,
            "url": f"{config.BASE_URL}/courses/{parts[1]}",
        })
    return courses


def parse_course(html, slug):
    tree = LexborHTMLParser(html)
    data = json_ld(tree, "Course")

    instance = data.get("hasCourseInstance") or {}
    if isinstance(instance, list):
        instance = instance[0] if instance else {}
    instructor = instance.get("instructor") or {}
    offers = data.get("offers") or {}

    chapters = {}
    for a in tree.css(f'a[href^="/courses/{slug}/"]'):
        href = a.attributes["href"]
        parts = href.strip("/").split("/")
        title = a.text(strip=True)

        if len(parts) == 3 and parts[2] not in chapters:
            chapters[parts[2]] = {
                "slug": parts[2],
                "title": title,
                "url": config.BASE_URL + href,
                "lessons": [],
            }
        elif len(parts) == 4 and parts[2] in chapters and parts[3] != "quiz":
            lessons = chapters[parts[2]]["lessons"]
            if all(lesson["slug"] != parts[3] for lesson in lessons):
                lessons.append({"slug": parts[3], "title": title, "url": config.BASE_URL + href})

    return {
        "title": data.get("name"),
        "description": data.get("description"),
        "instructor": instructor.get("name"),
        "is_free": str(offers.get("price")) == "0",
        "chapters": list(chapters.values()),
    }


def parse_lesson(html):
    tree = LexborHTMLParser(html)
    h1 = tree.css_first("h1")
    article = json_ld(tree, "Article")
    content = tree.css_first('div.course-content div[class*="courseContent"]')

    result = {
        "title": h1.text(strip=True) if h1 else article.get("headline"),
        "description": article.get("description"),
        "content_html": None,
        "content_text": None,
        "word_count": 0,
    }
    if not content:
        return result

    result["content_html"] = content.html

    for node in content.css(".katex"):
        tex = node.css_first("annotation")
        node.replace_with(f"${tex.text()}$" if tex else node.text())
    for node in content.css("script, style, .graphviz-container"):
        node.decompose()

    text = content.text(separator="")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()

    result["content_text"] = text or None
    result["word_count"] = len(text.split())
    return result
