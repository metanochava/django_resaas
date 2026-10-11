"""pytest fixtures for projects and modules built on RESAAS.

    # conftest.py
    pytest_plugins = ["django_resaas.testing.pytest_plugin"]

    def test_invoices(bootstrap_tenant):
        tenant = bootstrap_tenant("alice", modules=("sales",))
        assert tenant["client"].get("/api/sales/invoices/").status_code == 200
"""
import pytest

from django_resaas import testing


@pytest.fixture
def activate_module():
    """activate_module(entity, name) - see django_resaas.testing.activate_module."""
    return testing.activate_module


@pytest.fixture
def bootstrap_tenant():
    """bootstrap_tenant(username, modules=()) - see django_resaas.testing.bootstrap_tenant."""
    return testing.bootstrap_tenant


@pytest.fixture(autouse=True)
def _fresh_cache():
    """Every test starts with an empty Django cache: rate limits (throttles of
    the public endpoints, OTP attempt counters) are counted there, and every
    test client comes from the same address - a count must not leak from one
    test into the next."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()
