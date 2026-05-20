import pytest
from django.db import connection


@pytest.mark.django_db
def test_physical_fk_columns_are_integer_backed():
    expected_columns = {
        "application": {"status_id"},
        "application_status": {"color_id", "color_text_id", "icon_id"},
        "condition": {"color_id", "color_text_id", "icon_id"},
        "department": {"color_id", "color_text_id", "icon_id"},
        "display": {"city_id"},
        "panel": {"display_id", "condition_id", "department_id"},
        "cell": {"display_id", "panel_id"},
        "departure_status": {"color_id", "icon_id"},
    }
    allowed_field_types = {
        "AutoField",
        "BigAutoField",
        "BigIntegerField",
        "IntegerField",
        "SmallIntegerField",
    }

    with connection.cursor() as cursor:
        for table_name, column_names in expected_columns.items():
            description = connection.introspection.get_table_description(cursor, table_name)
            by_name = {column.name: column for column in description}
            assert column_names.issubset(by_name.keys())

            for column_name in column_names:
                field_type = connection.introspection.get_field_type(
                    by_name[column_name].type_code,
                    by_name[column_name],
                )
                assert field_type in allowed_field_types
