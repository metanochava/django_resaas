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
