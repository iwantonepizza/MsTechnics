import pytest
from factory.django import DjangoModelFactory
from rest_framework.test import APIClient

from apps.directory.storage.models import Connectors, PowerBlocks, Wires
from tests.factories import (
    MsUserFactory,
)

pytestmark = pytest.mark.django_db


def _grant_zip_edit_permission(user) -> None:
    """T-7-003: fine-grained права хранятся в MsUser.extra_permissions (JSONField)."""
    user.extra_permissions = sorted({*(user.extra_permissions or []), "can_edit_zip_counts"})
    user.save(update_fields=["extra_permissions"])


class WiresFactory(DjangoModelFactory):
    class Meta:
        model = Wires
        django_get_or_create = ("name",)

    name = "wire-default"
    description = "storage wire"
    count = 5
    low_stock_threshold = 3


class PowerBlocksFactory(DjangoModelFactory):
    class Meta:
        model = PowerBlocks
        django_get_or_create = ("name",)

    name = "power-block-default"
    description = "storage power block"
    count = 5
    low_stock_threshold = 3


class ConnectorsFactory(DjangoModelFactory):
    class Meta:
        model = Connectors
        django_get_or_create = ("name",)

    name = "connector-default"
    description = "storage connector"
    count = 5
    low_stock_threshold = 3


def test_storage_list_returns_low_stock_fields() -> None:
    low_stock_item = WiresFactory(name="wire-low", count=1, low_stock_threshold=3)
    WiresFactory(name="wire-ok", count=4, low_stock_threshold=3)
    user = MsUserFactory(permission="monitoring")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/storage/wires/")

    assert response.status_code == 200
    payload = response.data["results"]
    low_stock_payload = next(item for item in payload if item["id"] == low_stock_item.id)
    assert low_stock_payload["low_stock_threshold"] == 3
    assert low_stock_payload["is_low_stock"] is True


def test_storage_patch_is_forbidden_without_admin_or_extra_permission() -> None:
    wire = WiresFactory(count=2)
    user = MsUserFactory(permission="monitoring")
    client = APIClient()
    client.force_authenticate(user)

    response = client.patch(f"/api/v1/storage/wires/{wire.id}/", {"count": 7}, format="json")

    assert response.status_code == 403
    wire.refresh_from_db()
    assert wire.count == 2


def test_storage_patch_is_allowed_with_can_edit_zip_counts_permission() -> None:
    wire = WiresFactory(count=2, low_stock_threshold=3)
    user = MsUserFactory(permission="monitoring")
    _grant_zip_edit_permission(user)
    client = APIClient()
    client.force_authenticate(user)

    response = client.patch(f"/api/v1/storage/wires/{wire.id}/", {"count": 7}, format="json")

    assert response.status_code == 200
    assert response.data["count"] == 7
    assert response.data["is_low_stock"] is False


def test_power_blocks_and_connectors_models_can_be_created() -> None:
    power_block = PowerBlocksFactory(count=2, low_stock_threshold=5)
    connector = ConnectorsFactory(count=4, low_stock_threshold=3)

    assert power_block.pk is not None
    assert power_block.is_low_stock is True
    assert connector.pk is not None
    assert connector.is_low_stock is False


def test_admin_can_create_power_block_via_api() -> None:
    admin_user = MsUserFactory(permission="admin")
    client = APIClient()
    client.force_authenticate(admin_user)

    response = client.post(
        "/api/v1/storage/power-blocks/",
        {
            "name": "psu-24v",
            "description": "24V запасной блок",
            "count": 2,
            "low_stock_threshold": 3,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["is_low_stock"] is True
