#!/usr/bin/env python3
"""
Automarket MCP Server
---------------------
Exposes Facebook Marketplace scraping tools via Model Context Protocol (MCP)
with full CORS support for llama-server Web UI.
"""

import uvicorn
import urllib.parse
from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
from orchestrator import scrape_marketplace_page, DEFAULT_CDP_URL

mcp = FastMCP("Automarket Marketplace Scraper")


@mcp.tool()
def search_facebook_marketplace(query: str, cdp_url: str = DEFAULT_CDP_URL) -> str:
    """
    Scrapes Facebook Marketplace for items matching a search query using Brave Browser over CDP.

    Args:
        query: The search term (e.g. '32gb sodimm ddr5' or 'rtx 4090').
        cdp_url: Brave CDP URL (default http://127.0.0.1:9222).
    """
    encoded_query = urllib.parse.quote(query)
    target_url = f"https://www.facebook.com/marketplace/105570466142447/search/?query={encoded_query}"

    print(f"[MCP Tool] Scraper triggered for query: '{query}'")
    try:
        results = scrape_marketplace_page(
            target_url=target_url,
            cdp_url=cdp_url,
            scroll_wait=3
        )
        return f"Scraped Marketplace Listings for query '{query}':\n\n{results}"
    except Exception as err:
        return f"Error scraping Facebook Marketplace: {err}"


# Configure Starlette app with full CORS
app = mcp.http_app(transport="sse", allowed_origins=["*"], allowed_hosts=["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    print("============================================================")
    print(" Automarket MCP Server Running (CORS Enabled)              ")
    print(" Endpoint: http://127.0.0.1:8000/sse                       ")
    print(" Add to llama-server Web UI under 'MCP Servers'            ")
    print("============================================================")
    uvicorn.run(app, host="127.0.0.1", port=8000)
