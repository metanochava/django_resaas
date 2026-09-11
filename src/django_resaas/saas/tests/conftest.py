import pytest


@pytest.fixture
def create_product():
    """Creates a dev.demo.Product through the real API (not the ORM
    directly), so every test using it also exercises the full
    BaseAPIView create path - permissions, tenant assignment, etc."""

    def _create(client, name="Widget", sku="WID-1", price="9.99"):
        response = client.post(
            "/api/demo/products/", {"name": name, "sku": sku, "price": price}
        )
        assert response.status_code == 201, response.data
        return response.data["id"]

    return _create
