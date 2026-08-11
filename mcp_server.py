#!/usr/bin/env python3
import uvicorn
from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
from orchestrator import scrape_marketplace

mcp = FastMCP("Automarket")


@mcp.tool()
def search_facebook_marketplace(query: str) -> str:
    """Scrapes Facebook Marketplace for deals matching query."""
    return scrape_marketplace(query)


app = mcp.http_app(transport="sse", allowed_origins=["*"], allowed_hosts=["*"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

if __name__ == "__main__":
    print("Automarket MCP Server listening on http://127.0.0.1:8000/sse")
    uvicorn.run(app, host="127.0.0.1", port=8000)
