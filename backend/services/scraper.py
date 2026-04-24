import random
import time
from contextlib import suppress
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus, urljoin

from backend.services.normalization import build_search_query


@dataclass
class ScraperConfig:
    headless: bool = True
    retry_count: int = 2
    min_delay_seconds: float = 1.2
    max_delay_seconds: float = 2.6
    page_load_timeout_seconds: int = 30


class ProductScraper:
    def __init__(self, max_results_per_source: int = 10, config: ScraperConfig | None = None) -> None:
        self.max_results_per_source = max_results_per_source
        self.config = config or ScraperConfig()

    def scrape(self, structured_query: dict[str, Any], sources: list[str] | None = None) -> dict[str, Any]:
        sources = sources or ["amazon", "flipkart"]
        query = build_search_query(structured_query)
        products: list[dict[str, Any]] = []
        errors: list[str] = []

        try:
            driver, by = self._create_driver()
        except Exception as exc:
            return {
                "products": [],
                "errors": [
                    "Selenium browser setup failed. Install Chrome or Edge and ensure Selenium can start a driver.",
                    str(exc),
                ],
            }

        try:
            for source in sources:
                try:
                    if source == "amazon":
                        products.extend(self._with_retry(lambda: self._scrape_amazon(driver, by, query)))
                    elif source == "flipkart":
                        products.extend(self._with_retry(lambda: self._scrape_flipkart(driver, by, query)))
                except Exception as exc:
                    errors.append(f"{source}: {exc}")
        finally:
            with suppress(Exception):
                driver.quit()

        return {"products": products, "errors": errors}

    def _create_driver(self):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.common.by import By
            from selenium.common.exceptions import WebDriverException
        except Exception as exc:
            raise RuntimeError("The selenium package is not installed. Run pip install -r requirements.txt.") from exc

        common_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-sandbox",
            "--window-size=1366,900",
            "--lang=en-IN",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        ]

        chrome_options = ChromeOptions()
        if self.config.headless:
            chrome_options.add_argument("--headless=new")
        for arg in common_args:
            chrome_options.add_argument(arg)

        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(self.config.page_load_timeout_seconds)
            return driver, By
        except WebDriverException as chrome_error:
            try:
                from selenium.webdriver.edge.options import Options as EdgeOptions

                edge_options = EdgeOptions()
                if self.config.headless:
                    edge_options.add_argument("--headless=new")
                for arg in common_args:
                    edge_options.add_argument(arg)
                driver = webdriver.Edge(options=edge_options)
                driver.set_page_load_timeout(self.config.page_load_timeout_seconds)
                return driver, By
            except Exception as edge_error:
                raise RuntimeError(f"Chrome failed: {chrome_error}; Edge failed: {edge_error}") from edge_error

    def _with_retry(self, scrape_call):
        last_error: Exception | None = None
        for attempt in range(self.config.retry_count + 1):
            try:
                return scrape_call()
            except Exception as exc:
                last_error = exc
                if attempt < self.config.retry_count:
                    time.sleep(self.config.min_delay_seconds + attempt)
        raise last_error or RuntimeError("Scraping failed")

    def _scrape_amazon(self, driver, by, query: str) -> list[dict[str, Any]]:
        url = f"https://www.amazon.in/s?k={quote_plus(query)}"
        driver.get(url)
        self._human_delay()

        cards = driver.find_elements(by.CSS_SELECTOR, "div[data-component-type='s-search-result']")
        products = []
        for card in cards[: self.max_results_per_source * 2]:
            title = self._text(card, by, ["h2 span", "span.a-size-medium"])
            price = self._text(card, by, [".a-price .a-offscreen", ".a-price-whole"])
            if not title or not price:
                continue

            rating = self._text(card, by, ["span.a-icon-alt"])
            reviews = self._text(card, by, ["span.a-size-base.s-underline-text", "a[href*='customerReviews'] span"])
            image = self._attr(card, by, "img.s-image", "src")
            link = self._attr(card, by, "a.a-link-normal.s-no-outline", "href") or self._attr(card, by, "h2 a", "href")

            products.append(
                {
                    "title": title,
                    "price": price,
                    "rating": rating,
                    "reviews": reviews,
                    "image": image,
                    "url": urljoin("https://www.amazon.in", link or ""),
                    "source": "Amazon",
                }
            )
            if len(products) >= self.max_results_per_source:
                break
        return products

    def _scrape_flipkart(self, driver, by, query: str) -> list[dict[str, Any]]:
        url = f"https://www.flipkart.com/search?q={quote_plus(query)}"
        driver.get(url)
        self._human_delay()
        self._close_flipkart_login(driver, by)

        cards = driver.find_elements(by.CSS_SELECTOR, "div[data-id]")
        products = []
        for card in cards[: self.max_results_per_source * 2]:
            title = self._text(
                card,
                by,
                [
                    "div.RG5Slk",
                    "div.KzDlHZ",
                    "a.IRpwTa",
                    "a.wjcEIp",
                    "div._4rR01T",
                    "a[title]",
                ],
            )
            if not title:
                title = self._attr(card, by, "a[title]", "title")

            price = self._text(card, by, ["div.hZ3P6w", "div.Nx9bqj", "div._30jeq3", "div._25b18c div"])
            if not title or not price:
                continue

            rating = self._text(card, by, ["span.CjyrHS", "div.MKiFS6", "div.XQDdHH", "div._3LWZlK"])
            reviews = self._text(card, by, ["span.PvbNMB", "span.Wphh3N", "span._2_R_DZ"])
            image = self._attr(card, by, "img", "src")
            link = self._attr(card, by, "a[href]", "href")

            products.append(
                {
                    "title": title,
                    "price": price,
                    "rating": rating,
                    "reviews": reviews,
                    "image": image,
                    "url": urljoin("https://www.flipkart.com", link or ""),
                    "source": "Flipkart",
                }
            )
            if len(products) >= self.max_results_per_source:
                break
        return products

    def _close_flipkart_login(self, driver, by) -> None:
        for selector in ["button._2KpZ6l._2doB4z", "button[aria-label='Close']"]:
            with suppress(Exception):
                driver.find_element(by.CSS_SELECTOR, selector).click()
                time.sleep(0.5)
                return

    def _text(self, element, by, selectors: list[str]) -> str:
        for selector in selectors:
            with suppress(Exception):
                matched = element.find_element(by.CSS_SELECTOR, selector)
                text = matched.text.strip()
                if text:
                    return text
                for attribute in ("textContent", "innerText", "aria-label", "title"):
                    value = matched.get_attribute(attribute)
                    if value and value.strip():
                        return value.strip()
        return ""

    def _attr(self, element, by, selector: str, attribute: str) -> str:
        with suppress(Exception):
            value = element.find_element(by.CSS_SELECTOR, selector).get_attribute(attribute)
            return value.strip() if value else ""
        return ""

    def _human_delay(self) -> None:
        time.sleep(random.uniform(self.config.min_delay_seconds, self.config.max_delay_seconds))
