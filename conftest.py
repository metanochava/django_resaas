"""
Pytest bootstrap for the test suite.

Sets safe defaults for the environment variables `dev.settings` reads via
`os.environ.get(...)` with no fallback (SECRET_KEY, TIME_ZONE, ...), so the
suite runs standalone without requiring a local `.env` file. Real deployments
still supply their own values via `.env` / the environment as usual.
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("TIME_ZONE", "UTC")
os.environ.setdefault("SQL_ENGINE", "sqlite3")
os.environ.setdefault("SQL_DATABASE", ":memory:")
os.environ.setdefault("DOCKER", "YES")  # skip .env loading, we set what we need above

# the fixtures are the framework's public test helpers (django_resaas.testing),
# the same ones projects and modules use
pytest_plugins = ["django_resaas.testing.pytest_plugin"]
