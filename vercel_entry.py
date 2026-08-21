"""
vercel_entry.py — Vercel FastAPI preset entrypoint (diagnostic wrapper).

Loads the canonical FastAPI app from src/web/app.py with boot instrumentation:
cold-start progress goes to the function log, and any import-time failure is
surfaced both in logs and as a visible HTTP 500 response instead of Vercel's
silent FUNCTION_INVOCATION_FAILED. Declared via [tool.vercel] entrypoint in
pyproject.toml. Safe to keep permanently: on successful import it serves the
real app unchanged.
"""

import faulthandler
import sys
import time
import traceback

faulthandler.enable()

print(f"[boot] vercel_entry loading on python {sys.version.split()[0]}", flush=True)
_t0 = time.time()

try:
    from src.web.app import app  # noqa: F401

    print(
        f"[boot] app imported OK in {time.time() - _t0:.1f}s "
        f"({len(app.routes)} routes)",
        flush=True,
    )
except Exception:
    _err = traceback.format_exc()
    print("[boot] APP IMPORT FAILED:\n" + _err, flush=True)
    sys.stderr.flush()

    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse

    app = FastAPI(title="Boot Diagnostics")

    @app.api_route(
        "/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
    )
    async def _boot_failure(path: str):  # noqa: ANN001
        return PlainTextResponse(
            "APPLICATION BOOT FAILURE:\n\n" + _err, status_code=500
        )
