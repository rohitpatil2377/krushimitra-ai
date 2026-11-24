"""Test environment, set before ANY test module imports the app.

This file exists because of a real bug it caused: settings are read once at import time and
cached, so whichever test module imported `app.main` first decided the database for the whole
run. Alphabetically that was `test_capture_context`, which set no DATABASE_URL — so the twin
tests silently ran against the developer's own `data/krushimitra.db`, accumulated farmers across
runs, and then failed on the second run with data from the first.

pytest imports conftest before collecting tests, which makes this the only place the environment
can be set reliably. Everything lands in one temp directory that the OS cleans up.
"""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="krushi-tests-")

os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["CAPTURE_DIR"] = os.path.join(_TMP, "captures")
os.environ["MARKET_HISTORY_DIR"] = os.path.join(_TMP, "market")
# Keep every provider on its mock: a test run must never make a billable call or depend on the
# network, whatever happens to be in the developer's .env.
os.environ["VISION_PROVIDER"] = "mock"
os.environ["WEATHER_PROVIDER"] = "mock"
os.environ["MARKET_PROVIDER"] = "mock"
