"""
litellm_runner.py — LiteLLM server setup and process orchestration.
"""

import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

def check_proxy_health(host: str = "localhost", port: int = 8002, timeout: float = 2.0) -> bool:
    """Check if the LiteLLM proxy is responsive on specified host and port."""
    url = f"http://{host}:{port}/health/readiness"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False

def start_proxy_server(config_path: Path, port: int = 8002):
    """Launch LiteLLM proxy server using specified config."""
    if not config_path.exists():
        raise FileNotFoundError(f"LiteLLM config file not found: {config_path}")
        
    if not shutil.which("litellm"):
        raise RuntimeError("LiteLLM CLI executable not found in system PATH. Ensure litellm is installed in your environment.")

    cmd = [
        "litellm",
        "--config", str(config_path),
        "--port", str(port),
    ]
    print(f"[LiteLLM Proxy] Starting server on port {port} using config {config_path.name}...")
    subprocess.run(cmd)
