"""
conftest.py — Shared pytest fixtures and test configuration.

Key fixture: override_db_check
    The lifespan in main.py calls check_db_connection() at startup.
    In tests there is no real PostgreSQL running, so we mock it to return True.
    This lets TestClient start the app without a live database.

    All actual database operations in tests use the in-memory SQLite engine
    defined in test_phase0.py — completely isolated from production.
"""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def override_db_check():
    """
    Mock check_db_connection() → True for the entire test session.

    Without this, the FastAPI lifespan raises RuntimeError when it cannot
    reach PostgreSQL, causing all TestClient fixtures to fail at setup.

    autouse=True means this fixture runs for EVERY test automatically.
    """
    with patch("app.main.check_db_connection", return_value=True):
        yield