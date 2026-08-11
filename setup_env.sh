#!/usr/bin/env bash
set -e
echo "Setting up Conda environment..."
/opt/miniconda/bin/conda create -n ai-orchestrator python=3.11 -y || true
/opt/miniconda/envs/ai-orchestrator/bin/pip install -r requirements.txt
/opt/miniconda/envs/ai-orchestrator/bin/playwright install chromium
echo "Setup complete! Activate with: source /opt/miniconda/bin/activate ai-orchestrator"
