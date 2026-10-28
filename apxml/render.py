from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@viz-js/viz@3.11.0/lib/viz-standalone.js"></script>
<style>
body { margin: 0; background: white; }
#out { display: inline-block; padding: 16px; background: white; }
</style>
</head>
<body><div id="out"></div></body>
</html>
"""

DRAW = """async ([kind, content]) => {
    const out = document.getElementById("out");
    Plotly.purge(out);
    out.innerHTML = "";
    if (kind === "chart") {
        const figure = JSON.parse(content);
        await Plotly.newPlot(out, figure.data, figure.layout, {staticPlot: true});
    } else {
        const viz = await Viz.instance();
        out.appendChild(viz.renderSVGElement(content));
    }
}"""


def draw_all(items):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 1000}, device_scale_factor=2)
        page.set_content(PAGE)
        for kind, content, path in items:
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                page.evaluate(DRAW, [kind, content])
                page.locator("#out").screenshot(path=path)
                yield path, True
            except PlaywrightError:
                yield path, False
        browser.close()
