"""The WS subscription cap has to cover one screen.

The instruments panel browses 100 rows and subscribes them all, so a cap
below that told the user "30 symbols will not stream" for doing nothing
but opening the Stocks tab. The two caps also have to agree: the
frontend pre-trims to its own constant, so a lower one there wastes
capacity the server would have granted, and a higher one gets the whole
batch rejected.

    pytest -q backend/tests/test_ws_subscription_cap.py
"""

from __future__ import annotations

import pathlib
import re

from app.core.config import settings

# What one instruments panel asks for in a single browse.
PANEL_BROWSE_ROWS = 100


def test_cap_covers_a_full_browse_with_headroom():
    """Plus the user's watchlist and an option chain on the same socket."""
    assert settings.WS_MAX_SUBSCRIPTIONS_PER_CONN >= PANEL_BROWSE_ROWS
    assert settings.WS_MAX_SUBSCRIPTIONS_PER_CONN > PANEL_BROWSE_ROWS + 20


def test_frontend_mirrors_the_backend_cap():
    """A mismatch is silent in both directions: too low wastes capacity,
    too high makes the server reject the batch and the panel shows no
    quotes at all."""
    src = (
        pathlib.Path(__file__).resolve().parents[2]
        / "frontend-user"
        / "lib"
        / "useMarketStream.ts"
    ).read_text()
    m = re.search(r"const MAX_SUBSCRIPTIONS = (\d+);", src)
    assert m, "frontend cap constant not found — did it get renamed?"
    assert int(m.group(1)) == settings.WS_MAX_SUBSCRIPTIONS_PER_CONN


def test_panel_cap_fits_inside_the_connection_cap():
    src = (
        pathlib.Path(__file__).resolve().parents[2]
        / "frontend-user"
        / "components"
        / "trading"
        / "InstrumentsPanel.tsx"
    ).read_text()
    m = re.search(r"const LIVE_TOKEN_CAP = (\d+);", src)
    assert m, "panel cap constant not found — did it get renamed?"
    assert int(m.group(1)) <= settings.WS_MAX_SUBSCRIPTIONS_PER_CONN
