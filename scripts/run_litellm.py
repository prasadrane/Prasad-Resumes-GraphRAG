#!/usr/bin/env python3
"""
run_litellm.py — Entrypoint wrapper for starting the LiteLLM proxy server.
Imports modular launcher from src.proxy.
"""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.proxy.litellm_runner import start_proxy_server

CONFIG_PATH = ROOT_DIR / "config" / "litellm-config.yaml"

if not CONFIG_PATH.exists():
    CONFIG_PATH = ROOT_DIR / "litellm-config.yaml"

def main():
    start_proxy_server(CONFIG_PATH, port=8002)

if __name__ == "__main__":
    main()
