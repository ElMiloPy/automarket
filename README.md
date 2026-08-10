# 🚗 Automarket

Automarket is a high-performance local AI orchestrator connecting **Brave Browser (via Playwright CDP)** and **native C++ `llama-server`** to scrape and extract structured JSON deal data from Facebook Marketplace.

---

## 🏗️ Architecture

```
+---------------------------------------------------------------------------------+
|                              PYTHON ORCHESTRATOR                                |
|   1. Controls Brave via Playwright CDP (Port 9222)                             |
|   2. Scrapes, scrolls & parses Facebook Marketplace DOM with BeautifulSoup     |
|   3. Sends HTTP API requests to llama-server (Port 8080) / Exposes MCP Server   |
+---------------------------------------------------------------------------------+
          |                                                       |
          | CDP (Port 9222)                                       | HTTP POST / SSE MCP (Port 8000)
          v                                                       v
+-------------------------------+                       +-------------------------+
|     BRAVE BROWSER (GUI)       |                       |  NATIVE LLAMA-SERVER    |
| (Logged-in User Session/DOM)  |                       |  (C++ Binary + GPU/GGUF)|
+-------------------------------+                       +-------------------------+
```

---

## ⚡ Quick Start

### 1. Environment Setup
```bash
./setup_env.sh
source /opt/miniconda/bin/activate ai-orchestrator
```

### 2. Enable Brave Remote Debugging
```bash
./launch_brave.sh
```

### 3. Run Native `llama-server` (C++)
```bash
./llama-server -m /path/to/model.gguf --port 8080 -c 8192 -ngl 99
```

---

## 🚀 Execution Modes

### Mode A: Python Orchestrator CLI
Run full Marketplace scraping and structured JSON extraction:
```bash
python orchestrator.py
```
*Custom query & output file:*
```bash
python orchestrator.py \
  --target-url "https://www.facebook.com/marketplace/105570466142447/search/?query=32gb%20sodimm%20ddr5" \
  --query "Find 32GB SODIMM DDR5 RAM deals" \
  --output "results.json"
```

### Mode B: `llama-server` Web UI + MCP Integration
Use the Model Context Protocol (MCP) server to chat directly with your local LLM in `llama-server`'s Web UI and trigger scraping tools autonomously:

1. Start the MCP server:
   ```bash
   python mcp_server.py
   ```
2. Open `llama-server` Web UI (`http://127.0.0.1:8080`) -> **Settings** -> **MCP Servers**.
3. Add endpoint: `http://127.0.0.1:8000/sse`.
4. Chat with the LLM in the Web UI: *"Search Facebook Marketplace for 32GB SODIMM DDR5 RAM deals"*.

---

## ⚙️ Diagnostics & Health Check

Verify status of Brave CDP and `llama-server` endpoints:
```bash
python orchestrator.py --check-health
```
