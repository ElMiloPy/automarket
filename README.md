# 🚗 Automarket: Native Llama-Server + Brave CDP Orchestrator

Automarket is a high-performance local AI orchestration architecture for scraping and parsing web data (such as Facebook Marketplace) using **Brave Browser (via Playwright CDP)** and a native C++ **`llama-server`** HTTP API.

---

## 🏗️ Architecture Blueprint

```
+---------------------------------------------------------------------------------+
|                              PYTHON ORCHESTRATOR                                |
|   1. Controls Brave via Playwright CDP (Port 9222)                             |
|   2. Scrapes, scrolls & parses DOM with BeautifulSoup                           |
|   3. Sends HTTP API requests to llama-server (Port 8080 or custom port)         |
+---------------------------------------------------------------------------------+
          |                                                       |
          | CDP (Port 9222)                                       | HTTP POST (Open Port)
          v                                                       v
+-------------------------------+                       +-------------------------+
|     BRAVE BROWSER (GUI)       |                       |  NATIVE LLAMA-SERVER    |
| (Logged-in User Session/DOM)  |                       |  (C++ Binary + GPU/GGUF)|
+-------------------------------+                       +-------------------------+
```

---

## 🚀 Quick Start Guide

### Step 1: Environment Setup

Run the automated setup script to create the `ai-orchestrator` Conda environment and install dependencies:

```bash
./setup_env.sh
```

Activate the environment:

```bash
source /opt/miniconda/bin/activate ai-orchestrator
```

---

### Step 2: Start Brave Browser in Debugging Mode (Terminal 1)

Launch Brave Browser with Chrome DevTools Protocol (CDP) enabled on port 9222 using your **main logged-in profile**:

```bash
./launch_brave.sh
```

> ℹ️ `launch_brave.sh` sends the remote debugging request directly to your active Brave session without restarting it. If a prompt banner appears in your Brave browser, simply click **ALLOW**.

---

### Step 3: Launch your compiled `llama-server` (Terminal 2)

Start your compiled `llama-server` listening on your open port (e.g., port 8080):

```bash
./llama-server \
  -m /path/to/your/model.gguf \
  --port 8080 \
  -c 8192 \
  -ngl 99
```

---

### Step 4: Run the Python Orchestrator (Terminal 3)

Activate your Conda environment and run `orchestrator.py`:

```bash
source /opt/miniconda/bin/activate ai-orchestrator
python orchestrator.py
```

---

## ⚙️ CLI Options & Diagnostics

### Run Health Diagnostic

Check if Brave CDP and `llama-server` endpoints are reachable:

```bash
python orchestrator.py --check-health
```

### Custom Queries & Custom Ports

You can specify custom URLs, queries, ports, and output files:

```bash
python orchestrator.py \
  --target-url "https://www.facebook.com/marketplace/105570466142447/search/?query=rtx%204090" \
  --query "Find RTX 4090 graphics cards under $1600" \
  --server-url "http://127.0.0.1:8080/v1/chat/completions" \
  --cdp-url "http://127.0.0.1:9222" \
  --output "results.json"
```

---

## 💡 Why This Architecture is Peak Performance

1. **Native GPU Acceleration**: `llama-server` runs native C++ compiled binary using pure CUDA/AVX without Python overhead.
2. **Standardized OpenAI REST API**: `orchestrator.py` communicates with `llama-server` via `/v1/chat/completions`.
3. **Decoupled Engine**: Modify or restart your Python script without reloading heavy GGUF models in VRAM!

---

## 🔌 llama-server Web UI + MCP Server Integration

`llama-server`'s built-in Web UI supports **MCP (Model Context Protocol)** servers. This allows you to chat with your local LLM directly inside the `llama-server` Web UI, and have the model call the Facebook Marketplace scraper autonomously!

### How to use MCP with `llama-server` Web UI:

1. **Start the MCP Server**:
   ```bash
   python mcp_server.py
   ```
   *The MCP server starts on `http://127.0.0.1:8000/sse`.*

2. **Register in `llama-server` Web UI**:
   - Open your `llama-server` Web UI (`http://127.0.0.1:8080`).
   - Go to **Settings** -> **MCP Servers**.
   - Add a new server endpoint: `http://127.0.0.1:8000/sse` (or command: `python mcp_server.py`).

3. **Chat & Scrape**:
   - Ask the LLM in the Web UI: *"Find 32GB SODIMM DDR5 RAM deals on Facebook Marketplace"*.
   - The LLM will trigger `search_facebook_marketplace`, scrape live via Brave CDP, and display structured results directly in the Web UI chat window!
