# T-2-025 Wave 2 — Оставшиеся FK (roadmap)

Wave 1 (выполнено): Application.display, Application.panel

Wave 2 (следующий блок):
- Cell.display (to_field='name' → id)
- Cell.panel (to_field='name' → id)
- Display.city (to_field='name' → id)
- Panel.display (to_field='name' → id)
- Panel.department (to_field='name' → id)
- Panel.condition (to_field='name' → id)

Wave 3 (после wave 2):
- ApplicationStatus.color, .color_text, .icon
- Condition.color, .color_text, .icon
- Department.color, .color_text, .icon

Шаблон для каждого FK:
  1. AddField `<fk>_new_id IntegerField(null=True)`
  2. RunPython backfill (name → id через lookup dict)
  3. RemoveField старое поле
  4. RenameField `<fk>_new_id` → `<fk>_id`
  5. SeparateDatabaseAndState добавить правильный FK state
  6. Обновить Python-модель (убрать to_field)

Использовать: apps.shared_migrations.utils.backfill_fk_name_to_id()
