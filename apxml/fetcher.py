import time

import httpx
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from . import config

client = httpx.Client(
    headers={"User-Agent": config.USER_AGENT},
    timeout=config.TIMEOUT,
    follow_redirects=True,
)


def get(url):
    for attempt in range(1, config.RETRIES + 1):
        try:
            response = client.get(url)
        except httpx.HTTPError:
            response = None

        if response is not None and response.status_code == 200:
            time.sleep(config.DELAY)
            return response.text
        if response is not None and response.status_code == 404:
            return None

        time.sleep(5 * attempt)
    return None


def catalog_pages(max_pages):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=config.USER_AGENT)
        for number in range(1, max_pages + 1):
            page.goto(f"{config.BASE_URL}/courses?page={number}")
            try:
                page.wait_for_selector("div.mantine-Card-root h4", timeout=15000)
            except PlaywrightTimeout:
                break
            yield number, page.content()
        browser.close()
