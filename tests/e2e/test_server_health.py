"""Smoke test proving the app_server fixture boots the app cleanly."""

import urllib.request


def test_app_boots_and_serves_root(app_server):
    with urllib.request.urlopen(app_server + "/", timeout=10) as resp:
        assert resp.status == 200
