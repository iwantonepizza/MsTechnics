"""
T-3-fix-001: убираем префикс application_ из имён ApplicationStatus.

До:  application_sent_to_control, application_apply_in_control,
     application_sent_to_service, application_work_in_service, application_unable
После: sent_to_control, apply_in_control, sent_to_service, work_in_service, unable

НЕ трогаем: done, archive_done, archive_unable — у них префикса нет.
"""
from django.db import migrations

RENAMES = [
    ("application_sent_to_control",  "sent_to_control"),
    ("application_apply_in_control", "apply_in_control"),
    ("application_sent_to_service",  "sent_to_service"),
    ("application_work_in_service",  "work_in_service"),
    ("application_unable",           "unable"),
]


def forwards(apps, schema_editor):
    Status = apps.get_model("workflow_applications", "ApplicationStatus")
    for old, new in RENAMES:
        count = Status.objects.filter(name=old).update(name=new)
        if count:
            print(f"  renamed: {old!r} → {new!r} ({count} records)")


def reverse(apps, schema_editor):
    Status = apps.get_model("workflow_applications", "ApplicationStatus")
    for old, new in RENAMES:
        Status.objects.filter(name=new).update(name=old)


class Migration(migrations.Migration):
    dependencies = [
        ("workflow_applications", "0003_panel_fk_to_id"),
    ]
    operations = [
        migrations.RunPython(forwards, reverse),
    ]
