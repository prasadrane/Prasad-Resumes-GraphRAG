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

def _find_litellm_cli() -> str:
    """Resolve the ``litellm`` CLI from the active venv rather than bare PATH."""
    candidate = shutil.which("litellm")
    if candidate:
        return candidate
    # On Windows the venv ships .exe; on Unix it sits next to this interpreter.
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    candidates = [
        os.path.join(exe_dir, "litellm"),
        os.path.join(exe_dir, "litellm.exe"),
        os.path.join(exe_dir, "..", "bin", "litellm"),
    ]
    for c in candidates:
        resolved = os.path.normpath(c)
        if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
            return resolved
    raise RuntimeError(
        "LiteLLM CLI not found in system PATH or beside this interpreter. "
        "Ensure ``litellm`` is installed in the active virtual environment."
    )


def start_proxy_server(config_path: Path, port: int = 8002):
    """Launch LiteLLM proxy server using specified config."""
    if not config_path.exists():
        raise FileNotFoundError(f"LiteLLM config file not found: {config_path}")

    litellm_bin = _find_litellm_cli()

    cmd = [
        litellm_bin,
        "--config", str(config_path),
        "--port", str(port),
    ]
    print(f"[LiteLLM Proxy] Starting server on port {port} using config {config_path.name}...")
    subprocess.run(cmd)
