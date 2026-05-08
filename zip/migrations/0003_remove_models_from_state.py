from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("zip", "0002_dailytask_notified_stages"),
        ("directory_displays", "0003_photo_display_state_import"),
        ("directory_panels", "0002_remove_panel_application_status"),
        ("directory_storage", "0001_initial_state_import"),
        ("workflow_daily_tasks", "0001_initial_state_import"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="PhotoDisplay"),
                migrations.DeleteModel(name="Cell"),
                migrations.DeleteModel(name="Panels"),
                migrations.DeleteModel(name="DailyTask"),
                migrations.DeleteModel(name="Wires"),
                migrations.DeleteModel(name="Hubs"),
                migrations.DeleteModel(name="Lamels"),
                migrations.DeleteModel(name="Display"),
                migrations.CreateModel(
                    name="Display",
                    fields=[],
                    options={"proxy": True, "verbose_name": "Экран", "verbose_name_plural": "Экраны"},
                    bases=("directory_displays.display",),
                ),
                migrations.CreateModel(
                    name="Cell",
                    fields=[],
                    options={"proxy": True, "verbose_name": "Ячейка", "verbose_name_plural": "Ячейки"},
                    bases=("directory_displays.cell",),
                ),
                migrations.CreateModel(
                    name="Panels",
                    fields=[],
                    options={"proxy": True, "verbose_name": "Панель", "verbose_name_plural": "Панели"},
                    bases=("directory_panels.panel",),
                ),
                migrations.CreateModel(
                    name="DailyTask",
                    fields=[],
                    options={"proxy": True, "verbose_name": "Задание", "verbose_name_plural": "Задания"},
                    bases=("workflow_daily_tasks.dailytask",),
                ),
                migrations.CreateModel(
                    name="Wires",
                    fields=[],
                    options={"proxy": True, "verbose_name": "Провод", "verbose_name_plural": "Провода"},
                    bases=("directory_storage.wires",),
                ),
                migrations.CreateModel(
                    name="Hubs",
                    fields=[],
                    options={"proxy": True, "verbose_name": "Хаб", "verbose_name_plural": "Хабы"},
                    bases=("directory_storage.hubs",),
                ),
                migrations.CreateModel(
                    name="Lamels",
                    fields=[],
                    options={"proxy": True, "verbose_name": "Ламель", "verbose_name_plural": "Ламели"},
                    bases=("directory_storage.lamels",),
                ),
                migrations.CreateModel(
                    name="PhotoDisplay",
                    fields=[],
                    options={"proxy": True, "verbose_name": "Фото экрана", "verbose_name_plural": "Фото экрана"},
                    bases=("directory_displays.photodisplay",),
                ),
            ],
        ),
    ]
