# T-2-026. Удалить `ConcreteMsUser`

> **Тип:** refactor
> **Приоритет:** P2
> **Оценка:** 0.5 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

В `user/models.py` есть `class ConcreteMsUser(MsUser): class Meta: proxy = True` — proxy-модель, которая нигде не используется, но засоряет импорты.

---

## Что сделать

1. Найти все импорты:
   ```bash
   grep -rln "ConcreteMsUser" --include="*.py" .
   ```

2. Если есть ссылки — проверить, можно ли заменить на `MsUser` напрямую. Обычно да, т.к. proxy нет функциональности.

3. Если используется `ConcreteMsUser.objects` — заменить на `MsUser.objects`.

4. Миграция:
   ```python
   # apps/core/users/migrations/00XX_remove_concretemsuser.py
   class Migration(migrations.Migration):
       operations = [
           migrations.DeleteModel(name='ConcreteMsUser'),
       ]
   ```
   
   Поскольку это proxy-модель, нет `db_table` и миграция только в state — Django сам это сделает.

5. Удалить класс из `apps/core/users/models.py`.

6. Удалить из compat-shim `user/models.py`.

---

## Критерии приёмки

- [ ] `grep -rln "ConcreteMsUser"` — пусто
- [ ] Миграция применяется
- [ ] `python manage.py check` — чисто
- [ ] Regression-тесты проходят
