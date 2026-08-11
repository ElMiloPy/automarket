#!/usr/bin/env python3
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"
CDP_URL = "http://127.0.0.1:9222"


def scrape_marketplace(query: str, cdp_url: str = CDP_URL) -> str:
    encoded_query = urllib.parse.quote(query)
    target_url = f"https://www.facebook.com/marketplace/105570466142447/search/?query={encoded_query}"

    print(f"[Scraper] Navigating to: {target_url}")
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = (browser.contexts[0] if browser.contexts else browser.new_context()).new_page()
        page.goto(target_url, wait_until="domcontentloaded")

        print("[Scraper] Scrolling until 'Results from outside your search' appears...")
        for _ in range(40):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.keyboard.press("PageDown")
            time.sleep(1.0)

            content = page.content()
            if "Results from outside your search" in content or "Resultados fuera de tu búsqueda" in content:
                print("[Scraper] End of search results reached.")
                break

        soup = BeautifulSoup(page.content(), "html.parser")
        page.close()

        items, seen = [], set()
        for a in soup.find_all("a", href=True):
            if "/marketplace/item/" in a["href"]:
                url = f"https://www.facebook.com{a['href'].split('?')[0]}"
                if url not in seen and a.get_text(strip=True):
                    seen.add(url)
                    items.append(f"Title: {a.get_text(' | ', strip=True)} | Link: {url}")

        print(f"[Scraper] Extracted all {len(items)} items.")
        return "\n".join(items) if items else "No items found."


def query_llama_server(scraped_text: str, query: str, server_url: str = LLAMA_URL) -> str:
    payload = {
        "model": "qwen2.5-7b",
        "messages": [
            {"role": "system", "content": "Extract marketplace deals into a JSON array (title, price, specs, link)."},
            {"role": "user", "content": f"Query: {query}\n\nData:\n{scraped_text}"}
        ],
        "temperature": 0.1,
        "max_tokens": 2500
    }
    resp = requests.post(server_url, json=payload, headers={"Content-Type": "application/json"}, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def main():
    query = "32gb sodimm ddr5"
    scraped = scrape_marketplace(query)
    result = query_llama_server(scraped, query)
    print("\n--- AI EXTRACTED RESULT ---")
    print(result)


if __name__ == "__main__":
    main()
