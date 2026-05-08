"""T-2-012: импорт существующей таблицы user в новый app."""
from django.db import migrations, models
import django.contrib.auth.models
import django.contrib.auth.validators


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core_references", "0001_initial_state_import"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="MsUser",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("password", models.CharField(max_length=128, verbose_name="password")),
                        ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                        ("is_superuser", models.BooleanField(default=False)),
                        ("username", models.CharField(max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()])),
                        ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                        ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                        ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                        ("is_staff", models.BooleanField(default=False)),
                        ("is_active", models.BooleanField(default=True)),
                        ("date_joined", models.DateTimeField(auto_now_add=True, null=True)),
                        ("permission", models.CharField(choices=[("monitoring","Мониторинг"),("control","Контроль"),("service","Сервис"),("all","Все"),("admin","Админ"),("technical","Техник"),("none_type","Никакие")], default="none_type", max_length=20)),
                        ("telegram_id", models.CharField(blank=True, max_length=20, null=True)),
                        ("max_id", models.CharField(blank=True, max_length=50, null=True)),
                        ("allowed_city", models.ManyToManyField(blank=True, to="core_references.cities")),
                        ("groups", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.group")),
                        ("user_permissions", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.permission")),
                    ],
                    options={"db_table": "user", "verbose_name": "Пользователь"},
                    managers=[("objects", django.contrib.auth.models.UserManager())],
                ),
            ],
        ),
    ]
