"""
T-3-fix-001: strip the application_ prefix from ApplicationStatus names.
"""

from django.db import migrations


RENAMES = [
    ("application_sent_to_control", "sent_to_control"),
    ("application_apply_in_control", "apply_in_control"),
    ("application_sent_to_service", "sent_to_service"),
    ("application_work_in_service", "work_in_service"),
    ("application_unable", "unable"),
]


def _rewrite_legacy_fk_values(connection, source, target):
    with connection.cursor() as cursor:
        for table_name, column_name in (
            ("panel", "application_status_id"),
            ("application", "status_id"),
        ):
            cursor.execute(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = %s
                  AND column_name = %s
                """,
                [table_name, column_name],
            )
            row = cursor.fetchone()
            if not row or row[0] in {"smallint", "integer", "bigint"}:
                continue

            cursor.execute(
                f"UPDATE {table_name} SET {column_name} = %s WHERE {column_name} = %s",
                [target, source],
            )


def forwards(apps, schema_editor):
    status_model = apps.get_model("workflow_applications", "ApplicationStatus")
    connection = schema_editor.connection
    for old, new in RENAMES:
        count = status_model.objects.filter(name=old).update(name=new)
        _rewrite_legacy_fk_values(connection, old, new)
        if count:
            print(f"  renamed: {old!r} -> {new!r} ({count} records)")


def reverse(apps, schema_editor):
    status_model = apps.get_model("workflow_applications", "ApplicationStatus")
    connection = schema_editor.connection
    for old, new in RENAMES:
        _rewrite_legacy_fk_values(connection, new, old)
        status_model.objects.filter(name=new).update(name=old)


class Migration(migrations.Migration):
    dependencies = [
        ("workflow_applications", "0003_panel_fk_to_id"),
    ]

    operations = [
        migrations.RunPython(forwards, reverse),
    ]
