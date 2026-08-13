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

        print("[Scraper] Scrolling until no new items are found after 3 consecutive scrolls...")
        collected_items = {}
        no_increase_count = 0

        for scroll_step in range(100):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.keyboard.press("PageDown")
            time.sleep(1.0)

            # Extract items currently in DOM before Facebook unmounts/virtualizes them
            raw_items = page.evaluate('''() => {
                const anchors = Array.from(document.querySelectorAll('a[href*="/marketplace/item/"]'));
                return anchors.map(a => {
                    const href = a.getAttribute('href') || '';
                    const cleanPath = href.split('?')[0];
                    const fullUrl = cleanPath.startsWith('http') ? cleanPath : 'https://www.facebook.com' + cleanPath;
                    const text = (a.innerText || a.textContent || '').trim().replace(/[\\r\\n]+/g, ' | ');
                    return { url: fullUrl, text: text };
                }).filter(item => item.url && item.text);
            }''')

            new_items = 0
            for item in raw_items:
                url = item["url"]
                text = item["text"]
                if url not in collected_items:
                    collected_items[url] = f"Title: {text} | Link: {url}"
                    new_items += 1

            total_count = len(collected_items)
            print(f"[Scraper] Scroll {scroll_step + 1}: {total_count} total unique items collected (+{new_items} new).")

            if new_items > 0:
                no_increase_count = 0
            else:
                no_increase_count += 1
                if no_increase_count >= 3:
                    print("[Scraper] No new items found after 3 consecutive scrolls. Stopping scroll.")
                    break

        page.close()

        items = list(collected_items.values())
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
