#!/usr/bin/env bash
set -e

CONDA_EXE="/opt/miniconda/bin/conda"
ENV_NAME="ai-orchestrator"

echo "=== Automarket Environment Setup ==="

if [ ! -f "$CONDA_EXE" ]; then
    echo "Error: Conda executable not found at $CONDA_EXE"
    exit 1
fi

echo "[1/4] Checking Conda environment '$ENV_NAME'..."
if "$CONDA_EXE" env list | grep -q "^$ENV_NAME "; then
    echo "Environment '$ENV_NAME' already exists."
else
    echo "Creating Conda environment '$ENV_NAME' with Python 3.11..."
    "$CONDA_EXE" create -n "$ENV_NAME" python=3.11 -y
fi

ENV_PYTHON="/opt/miniconda/envs/$ENV_NAME/bin/python"
ENV_PIP="/opt/miniconda/envs/$ENV_NAME/bin/pip"
ENV_PLAYWRIGHT="/opt/miniconda/envs/$ENV_NAME/bin/playwright"

echo "[2/4] Installing Python packages from requirements.txt..."
"$ENV_PIP" install -r requirements.txt

echo "[3/4] Installing Playwright Chromium browser binary..."
"$ENV_PLAYWRIGHT" install chromium

echo "[4/4] Environment setup complete!"
echo ""
echo "To activate this environment in your terminal, run:"
echo "  source /opt/miniconda/bin/activate $ENV_NAME"
