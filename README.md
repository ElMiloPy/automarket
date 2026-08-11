# 🚗 Automarket

Minimalist local AI orchestrator for scraping Facebook Marketplace via **Brave CDP** and parsing deals with **native `llama-server`** (or via **MCP Server**).

---

## ⚡ Quick Start

```bash
# 1. Launch Brave Browser with CDP on port 9222
./launch_brave.sh

# 2. Run compiled llama-server on port 8080
./llama-server -m /path/to/model.gguf --port 8080 -c 8192 -ngl 99

# 3. Execute Scraper & LLM Pipeline
source /opt/miniconda/bin/activate ai-orchestrator
python orchestrator.py
```

---

## 🔌 llama-server Web UI + MCP

Start the MCP server to chat with your local LLM in `llama-server`'s Web UI and trigger Marketplace searches automatically:

```bash
python mcp_server.py
```
- In `llama-server` Web UI -> **MCP Servers**: add `http://127.0.0.1:8000/sse`.
