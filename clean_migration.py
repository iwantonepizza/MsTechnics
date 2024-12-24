import os
import shutil


def clean_migrations(project_path):
    """
    Удаляет все файлы миграций из указанного Django-проекта, кроме системных папок и __init__.py.

    :param project_path: Путь к корню проекта.
    """
    migration_dirs_deleted = 0
    files_deleted = 0

    for root, dirs, files in os.walk(project_path):
        # Исключаем папки, начинающиеся с точки
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        if 'migrations' in dirs:
            migrations_path = os.path.join(root, 'migrations')

            # Удаляем все файлы миграций, кроме __init__.py
            for file in os.listdir(migrations_path):
                file_path = os.path.join(migrations_path, file)
                if file != '__init__.py' and file.endswith('.py'):
                    os.remove(file_path)
                    files_deleted += 1

            # Проверяем, пустая ли папка после удаления
            if len(os.listdir(migrations_path)) == 0:
                shutil.rmtree(migrations_path)
                migration_dirs_deleted += 1

    print(f"Удалено {files_deleted} файлов миграций.")
    print(f"Удалено {migration_dirs_deleted} папок миграций (если они были пустыми).")


if __name__ == "__main__":
    # Укажите путь к корню вашего Django-проекта
    project_root = "C:/PyProjects/MsServiceControl"
    clean_migrations(project_root)

