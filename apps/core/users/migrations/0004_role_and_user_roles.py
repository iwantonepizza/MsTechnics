from django.db import migrations, models


def create_initial_roles(apps, _schema_editor):
    role_model = apps.get_model("user", "Role")
    for name, description in (
        ("monitoring", "Мониторинг"),
        ("control", "Контроль"),
        ("service", "Сервис"),
        ("admin", "Админ"),
        ("technical", "Техник"),
    ):
        role_model.objects.get_or_create(
            name=name,
            defaults={"description": description},
        )


def backfill_user_roles(apps, _schema_editor):
    role_model = apps.get_model("user", "Role")
    user_model = apps.get_model("user", "MsUser")

    role_by_name = {role.name: role for role in role_model.objects.all()}
    legacy_mapping = {
        "monitoring": ("monitoring",),
        "control": ("control",),
        "service": ("service",),
        "all": ("monitoring", "control", "service"),
        "admin": ("admin",),
        "technical": ("technical",),
        "none_type": (),
    }

    for user in user_model.objects.all().iterator():
        for role_name in legacy_mapping.get(user.permission, ()):
            role = role_by_name.get(role_name)
            if role is not None:
                user.roles.add(role)


class Migration(migrations.Migration):
    dependencies = [
        ("user", "0003_align_user_physical_schema"),
    ]

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=32, unique=True)),
                ("description", models.CharField(blank=True, max_length=128)),
            ],
            options={
                "db_table": "role",
                "verbose_name": "Роль",
                "verbose_name_plural": "Роли",
            },
        ),
        migrations.AddField(
            model_name="msuser",
            name="extra_permissions",
            field=models.JSONField(blank=True, default=list, verbose_name="Дополнительные права"),
        ),
        migrations.AddField(
            model_name="msuser",
            name="roles",
            field=models.ManyToManyField(blank=True, related_name="users", to="user.role", verbose_name="Роли"),
        ),
        migrations.RunPython(create_initial_roles, migrations.RunPython.noop),
        migrations.RunPython(backfill_user_roles, migrations.RunPython.noop),
    ]
