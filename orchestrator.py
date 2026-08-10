#!/usr/bin/env python3
"""
Automarket Master Orchestrator
--------------------------------
Connects to Brave Browser via Chrome DevTools Protocol (CDP), scrapes
Facebook Marketplace items, and queries a local native llama-server for
structured JSON deal extraction.
"""

import sys
import time
import json
import argparse
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Default configurations
DEFAULT_LLAMA_SERVER_URL = "http://127.0.0.1:8080/v1/chat/completions"
DEFAULT_BRAVE_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_TARGET_URL = "https://www.facebook.com/marketplace/105570466142447/search/?query=32gb%20sodimm%20ddr5"
DEFAULT_USER_QUERY = "Find 32GB SODIMM DDR5 RAM deals"


def check_cdp_connection(cdp_url, retries=15, delay=1.5):
    """Check if Brave CDP port is open and responding, retrying while user accepts permission popup if needed."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(f"{cdp_url}/json/version", timeout=3)
            if resp.status_code == 200:
                return True, resp.json().get("Browser", "Connected")
        except Exception:
            pass

        if attempt == 1:
            print(f"[CDP] Waiting for connection on {cdp_url}...")
            print("      (If a popup banner appears in Brave asking to ALLOW remote debugging, please click ALLOW)")
        elif attempt % 3 == 0:
            print(f"[CDP] Retrying connection to {cdp_url} (attempt {attempt}/{retries})...")
        time.sleep(delay)

    return False, "Connection timed out. Check if Brave was started with './launch_brave.sh' and any popup accepted."


def check_llama_server(server_url):
    """Check if llama-server endpoint is reachable."""
    # Attempt a GET or OPTIONS request on base host/port or models endpoint
    base_url = server_url.split("/v1/")[0] if "/v1/" in server_url else server_url
    models_url = f"{base_url}/v1/models"
    health_url = f"{base_url}/health"

    for url in [health_url, models_url, base_url]:
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code in [200, 404, 405]:
                return True, f"HTTP {resp.status_code}"
        except Exception:
            continue
    return False, "Connection refused or timed out"


def scrape_marketplace_page(target_url, cdp_url, scroll_wait_seconds=5, max_items=25):
    """
    Connects to Brave Browser via CDP, navigates to target URL,
    scrolls down to lazy-load elements, and extracts Marketplace listings.
    """
    print(f"[CDP] Connecting to Brave Browser at {cdp_url}...")
    
    cdp_ok, cdp_msg = check_cdp_connection(cdp_url)
    if not cdp_ok:
        raise ConnectionError(
            f"Could not connect to Brave DevTools at {cdp_url}. Details: {cdp_msg}\n"
            f"-> Chromium requires '--remote-debugging-port=9222' to be passed when Brave is FIRST opened.\n"
            f"-> RUN: './launch_brave.sh' to re-launch Brave with CDP active on your main profile."
        )

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            raise RuntimeError(f"Playwright failed to connect over CDP ({cdp_url}): {e}")

        contexts = browser.contexts
        if not contexts:
            context = browser.new_context()
        else:
            context = contexts[0]

        page = context.new_page()

        print(f"[Scraper] Navigating to target URL:\n  {target_url}")
        page.goto(target_url, wait_until="domcontentloaded")

        print("[Scraper] Scrolling down to trigger lazy loading...")
        for i in range(3):
            page.mouse.wheel(0, 1500)
            time.sleep(1)

        print(f"[Scraper] Waiting {scroll_wait_seconds} seconds for content to populate...")
        time.sleep(scroll_wait_seconds)

        # Extract HTML content & parse with BeautifulSoup
        raw_html = page.content()
        soup = BeautifulSoup(raw_html, "html.parser")

        items_summary = []
        seen_links = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/marketplace/item/" in href:
                clean_url = f"https://www.facebook.com{href.split('?')[0]}"
                if clean_url in seen_links:
                    continue
                seen_links.add(clean_url)

                text = a.get_text(separator=" | ", strip=True)
                if text:
                    items_summary.append(f"Title/Info: {text} | Link: {clean_url}")

        page.close()
        print(f"[Scraper] Extracted {len(items_summary)} marketplace item listing(s).")
        
        if not items_summary:
            print("[Warning] No item links matching '/marketplace/item/' found. Returning raw text summary...")
            text_snippet = soup.get_text(separator="\n", strip=True)[:3000]
            return text_snippet

        selected_items = items_summary[:max_items]
        print(f"[Scraper] Passing top {len(selected_items)} items to llama-server.")
        return "\n".join(selected_items)


def query_llama_server(scraped_text, search_query, server_url):
    """
    Sends HTTP POST request to llama-server's OpenAI-compatible endpoint.
    """
    print(f"[LLM] Querying llama-server at {server_url}...")

    server_ok, server_msg = check_llama_server(server_url)
    if not server_ok:
        print(f"[Warning] Health check on {server_url} reported: {server_msg}. Attempting POST call...")

    payload = {
        "model": "qwen2.5-7b",
        "messages": [
            {
                "role": "system",
                "content": "You are a JSON data extraction assistant. Extract marketplace deals cleanly."
            },
            {
                "role": "user",
                "content": f"""User Request: "{search_query}"

Extract matching items from the raw data below into a clean JSON array of objects with keys:
- title
- price
- specs (capacity/RAM/VRAM/condition if available)
- link

Raw Scraped Data:
{scraped_text}

Return ONLY valid JSON format without markdown explanation wrappers.
"""
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1500
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(server_url, json=payload, headers=headers, timeout=120)
    except requests.exceptions.ConnectionError:
        raise Exception(
            f"Failed to connect to llama-server at {server_url}.\n"
            f"-> Make sure your compiled llama-server binary is running and listening on the expected port."
        )

    if response.status_code == 200:
        result = response.json()
        try:
            content = result["choices"][0]["message"]["content"]
            return content
        except (KeyError, IndexError) as parse_err:
            raise Exception(f"Unexpected JSON response structure from llama-server: {result} ({parse_err})")
    else:
        raise Exception(f"llama-server returned HTTP error {response.status_code}: {response.text}")


def main():
    parser = argparse.ArgumentParser(description="Automarket Marketplace AI Scraper & Orchestrator")
    parser.add_argument("--target-url", default=DEFAULT_TARGET_URL, help="Target search URL on Facebook Marketplace")
    parser.add_argument("--query", default=DEFAULT_USER_QUERY, help="User query describing desired items to filter")
    parser.add_argument("--server-url", default=DEFAULT_LLAMA_SERVER_URL, help="Open OpenAI-compatible llama-server URL endpoint")
    parser.add_argument("--cdp-url", default=DEFAULT_BRAVE_CDP_URL, help="Brave Browser CDP endpoint URL")
    parser.add_argument("--scroll-wait", type=int, default=5, help="Seconds to wait after scrolling for lazy loaded content")
    parser.add_argument("--max-items", type=int, default=25, help="Maximum scraped items to include in LLM context prompt")
    parser.add_argument("--output", help="Optional output filepath to save extracted JSON result")
    parser.add_argument("--check-health", action="store_true", help="Run health check on CDP and llama-server ports and exit")

    args = parser.parse_args()

    if args.check_health:
        print("=== Health Diagnostic Check ===")
        cdp_ok, cdp_info = check_cdp_connection(args.cdp_url)
        print(f"Brave CDP ({args.cdp_url}): {'[OK] ' + str(cdp_info) if cdp_ok else '[FAILED] ' + str(cdp_info)}")

        llama_ok, llama_info = check_llama_server(args.server_url)
        print(f"Llama Server ({args.server_url}): {'[OK] ' + str(llama_info) if llama_ok else '[FAILED] ' + str(llama_info)}")
        sys.exit(0 if (cdp_ok and llama_ok) else 1)

    print("=== Automarket AI Pipeline Starting ===")
    
    # Step 1: Scrape page via Brave CDP
    try:
        scraped_content = scrape_marketplace_page(
            target_url=args.target_url,
            cdp_url=args.cdp_url,
            scroll_wait_seconds=args.scroll_wait,
            max_items=args.max_items
        )
    except Exception as scrape_err:
        print(f"\n[ERROR] Scraping failed: {scrape_err}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Extract items using llama-server
    try:
        extracted_result = query_llama_server(
            scraped_text=scraped_content,
            search_query=args.query,
            server_url=args.server_url
        )
    except Exception as llm_err:
        print(f"\n[ERROR] LLM Query failed: {llm_err}", file=sys.stderr)
        sys.exit(1)

    print("\n=================== ORCHESTRATED AI RESULT ===================")
    print(extracted_result)
    print("==============================================================")

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(extracted_result)
            print(f"[Output] Result saved to: {args.output}")
        except Exception as save_err:
            print(f"[Warning] Failed to save output to {args.output}: {save_err}")


if __name__ == "__main__":
    main()
