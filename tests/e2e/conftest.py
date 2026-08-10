"""
Shared fixtures for end-to-end tests.

`app_server` boots the FastAPI app (src.web.app:app) in a uvicorn subprocess
on a free local port, waits until it responds, yields its base URL, and tears
it down afterward. The baseline suite exercises only deterministic (non-LLM)
endpoints, so no LiteLLM proxy or API keys are required.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def _free_port() -> int:
    """Return an OS-assigned free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_healthy(base_url: str, timeout_s: float = 60.0) -> None:
    """Poll GET / until it returns HTTP 200 or the timeout expires."""
    deadline = time.monotonic() + timeout_s
    last_error = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(base_url + "/", timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception as exc:  # retry until deadline
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(
        f"App at {base_url} did not become healthy within {timeout_s}s: {last_error}"
    )


@pytest.fixture(scope="session")
def app_server():
    """Boot the local UI app in a subprocess and yield its base URL."""
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "src.web.app:app",
            "--host", "127.0.0.1", "--port", str(port),
        ],
        cwd=str(ROOT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_until_healthy(base_url)
    except RuntimeError as exc:
        # Health check failed — drain captured output so the uvicorn
        # traceback is visible in the failure message, not just the urllib
        # error that triggered the timeout.
        proc.terminate()
        tail = ""
        try:
            out, _ = proc.communicate(timeout=2)
            if out:
                tail = out.decode("utf-8", errors="replace")[-4000:]
        except Exception:
            pass
        msg = str(exc)
        if tail:
            msg += f"\n--- subprocess output (tail) ---\n{tail}"
        raise RuntimeError(msg) from exc

    try:
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
