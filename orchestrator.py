#!/usr/bin/env python3
"""
Automarket Orchestrator
-----------------------
Scrapes Facebook Marketplace listings via Brave Browser CDP and extracts
structured JSON deal data using native llama-server.
"""

import sys
import time
import argparse
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DEFAULT_SERVER_URL = "http://127.0.0.1:8080/v1/chat/completions"
DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_MARKETPLACE_URL = "https://www.facebook.com/marketplace/105570466142447/search/?query=32gb%20sodimm%20ddr5"
DEFAULT_QUERY = "Find 32GB SODIMM DDR5 RAM deals"


def check_cdp_health(cdp_url: str) -> bool:
    """Verifies that Brave CDP server responds with HTTP 200."""
    try:
        resp = requests.get(f"{cdp_url}/json/version", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def check_llama_health(server_url: str) -> bool:
    """Verifies that native llama-server endpoint is reachable."""
    base_url = server_url.split("/v1/")[0] if "/v1/" in server_url else server_url
    for path in ["/health", "/v1/models", ""]:
        try:
            resp = requests.get(f"{base_url}{path}", timeout=3)
            if resp.status_code in [200, 404, 405]:
                return True
        except Exception:
            continue
    return False


def scrape_marketplace_page(target_url: str, cdp_url: str = DEFAULT_CDP_URL, scroll_wait: int = 3) -> str:
    """Connects to Brave Browser via CDP, scrolls until 'Results from outside your search' appears, and extracts all Marketplace listings."""
    if not check_cdp_health(cdp_url):
        raise ConnectionError(
            f"Brave CDP port non-responsive at {cdp_url}.\n"
            f"Run './launch_brave.sh' to activate remote debugging on your main profile."
        )

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        print(f"[Scraper] Navigating to: {target_url}")
        page.goto(target_url, wait_until="domcontentloaded")

        print("[Scraper] Scrolling every 1s until 'Results from outside your search' appears...")
        max_scrolls = 40

        for scroll_count in range(1, max_scrolls + 1):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.keyboard.press("PageDown")
            time.sleep(1.0)

            current_count = page.locator('a[href*="/marketplace/item/"]').count()
            print(f"  Scroll {scroll_count}: {current_count} listing(s) loaded so far...")

            page_content = page.content()
            if "Results from outside your search" in page_content or "Resultados fuera de tu búsqueda" in page_content:
                print("[Scraper] Found 'Results from outside your search' divider! Stopping scroll.")
                break

        time.sleep(scroll_wait)
        soup = BeautifulSoup(page.content(), "html.parser")
        page.close()

        items = []
        seen_urls = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/marketplace/item/" in href:
                clean_url = f"https://www.facebook.com{href.split('?')[0]}"
                if clean_url not in seen_urls:
                    seen_urls.add(clean_url)
                    text = a.get_text(separator=" | ", strip=True)
                    if text:
                        items.append(f"Title/Info: {text} | Link: {clean_url}")

        print(f"[Scraper] Extracted all {len(items)} listing(s). Passing all to LLM.")
        return "\n".join(items) if items else soup.get_text(separator="\n", strip=True)[:3000]


def query_llama_server(scraped_text: str, user_query: str, server_url: str = DEFAULT_SERVER_URL) -> str:
    """Sends raw scraped listings to llama-server for structured JSON extraction."""
    print(f"[LLM] Querying llama-server at {server_url}...")

    payload = {
        "model": "qwen2.5-7b",
        "messages": [
            {
                "role": "system",
                "content": "You are a JSON data extraction assistant. Extract marketplace deals cleanly into a JSON array."
            },
            {
                "role": "user",
                "content": f"""User Query: "{user_query}"

Extract matching items into a valid JSON array of objects with keys: title, price, specs, link.

Raw Data:
{scraped_text}

Return ONLY valid JSON format.
"""
            }
        ],
        "temperature": 0.1,
        "max_tokens": 2500
    }

    try:
        resp = requests.post(server_url, json=payload, headers={"Content-Type": "application/json"}, timeout=120)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"llama-server query failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Automarket Marketplace AI Scraper & Orchestrator")
    parser.add_argument("--target-url", default=DEFAULT_MARKETPLACE_URL, help="Target search URL")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="User query for filtering deals")
    parser.add_argument("--server-url", default=DEFAULT_SERVER_URL, help="llama-server endpoint")
    parser.add_argument("--cdp-url", default=DEFAULT_CDP_URL, help="Brave CDP URL")
    parser.add_argument("--scroll-wait", type=int, default=3, help="Seconds to wait after scrolling")
    parser.add_argument("--output", help="Filepath to save extracted JSON result")
    parser.add_argument("--check-health", action="store_true", help="Run health diagnostics and exit")

    args = parser.parse_args()

    if args.check_health:
        cdp_ok = check_cdp_health(args.cdp_url)
        llama_ok = check_llama_health(args.server_url)
        print(f"Brave CDP ({args.cdp_url}): {'[OK]' if cdp_ok else '[FAILED]'}")
        print(f"llama-server ({args.server_url}): {'[OK]' if llama_ok else '[FAILED]'}")
        sys.exit(0 if (cdp_ok and llama_ok) else 1)

    print("=== Automarket AI Pipeline Starting ===")
    scraped_content = scrape_marketplace_page(args.target_url, args.cdp_url, args.scroll_wait)
    result = query_llama_server(scraped_content, args.query, args.server_url)

    print("\n=================== ORCHESTRATED AI RESULT ===================")
    print(result)
    print("==============================================================")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"[Output] Saved result to {args.output}")


if __name__ == "__main__":
    main()
