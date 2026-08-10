"""
Phase 1 security regression tests for the local UI server (src.web.app:app).

These pin the fix to the legacy PDF route so a future refactor cannot
silently re-introduce path traversal or containment bypass.
"""

import httpx


def test_legacy_pdf_route_rejects_traversal_segments(app_server):
    # %2e%2e decodes to ".." server-side; kept percent-encoded so the HTTP
    # client does not normalize the dot segments away before sending.
    resp = httpx.get(f"{app_server}/api/pdf/%2e%2e/%2e%2e", timeout=30.0)
    assert resp.status_code == 403


def test_legacy_pdf_route_still_serves_real_pdfs(app_server):
    # Ensure the default resume artifacts exist first.
    prep = httpx.get(f"{app_server}/api/default-resume", timeout=120.0)
    assert prep.status_code == 200

    resp = httpx.get(
        f"{app_server}/api/pdf/Default/Prasad_Rane_Default_Resume.pdf",
        timeout=30.0,
    )
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("application/pdf")
    assert resp.content.startswith(b"%PDF")
