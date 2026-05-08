"""Корневой conftest.py — регистрация фабрик и базовые фикстуры."""
import django
import pytest
from django.conf import settings


@pytest.fixture
def authenticated_client(client, db):
    """Client с залогиненным admin-юзером."""
    from apps.core.users.models import MsUser
    user = MsUser.objects.create_user(
        username="testadmin",
        password="testpassword",
        permission="admin",
    )
    client.force_login(user)
    return client, user
