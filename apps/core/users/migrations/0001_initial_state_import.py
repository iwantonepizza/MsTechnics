"""T-2-012: импорт существующей таблицы user в новый app."""
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models
import django.contrib.auth.models
import django.contrib.auth.validators


class Migration(migrations.Migration):
    initial = True
    replaces = [("user", "0001_initial")]
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("main", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.CreateModel(
                    name="MsUser",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("password", models.CharField(max_length=128, verbose_name="password")),
                        ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                        ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
                        ("username", models.CharField(error_messages={"unique": "A user with that username already exists."}, help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.", max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name="username")),
                        ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                        ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                        ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                        ("is_staff", models.BooleanField(default=False, help_text="Designates whether the user can log into this admin site.", verbose_name="staff status")),
                        ("is_active", models.BooleanField(default=True, help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.", verbose_name="active")),
                        ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                        ("permission", models.CharField(choices=[("monitoring", "Мониторинг"), ("control", "Контроль"), ("service", "Сервис"), ("all", "Все"), ("admin", "Админ"), ("technical", "Техник"), ("none_type", "Никакие")], default="none_type", max_length=20, verbose_name="Уровень доступа")),
                        ("telegram_id", models.CharField(blank=True, max_length=10, null=True, verbose_name="Айди телеграм")),
                        ("groups", models.ManyToManyField(blank=True, help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.", related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                        ("user_permissions", models.ManyToManyField(blank=True, help_text="Specific permissions for this user.", related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
                        ("allowed_city", models.ManyToManyField(blank=True, to="main.cities", verbose_name="Разрешенные города")),
                    ],
                    options={"verbose_name": "Пользователя", "verbose_name_plural": "Пользователи", "db_table": "user", "abstract": False},
                    managers=[("objects", django.contrib.auth.models.UserManager())],
                ),
                migrations.CreateModel(
                    name="ConcreteMsUser",
                    fields=[
                        ("msuser_ptr", models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to="user.msuser")),
                    ],
                    options={"verbose_name": "user", "verbose_name_plural": "users", "abstract": False},
                    bases=("user.msuser",),
                    managers=[("objects", django.contrib.auth.models.UserManager())],
                ),
            ],
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
                        ("allowed_city", models.ManyToManyField(blank=True, to="main.cities")),
                        ("groups", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.group")),
                        ("user_permissions", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.permission")),
                    ],
                    options={"db_table": "user", "verbose_name": "Пользователь"},
                    managers=[("objects", django.contrib.auth.models.UserManager())],
                ),
            ],
        ),
    ]
