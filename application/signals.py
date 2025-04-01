
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.timezone import now

from application.models import Application, ApplicationHistoryReport


@receiver(pre_delete, sender=Application)
def save_application_history(sender, instance, **kwargs):
    """Создаёт запись в ApplicationHistoryReport перед удалением заявки."""
    ApplicationHistoryReport.objects.create(
        application_id=instance.id,
        description=f"Заявка {instance.id} удалена",
        comment="Удалена пользователем",
        time=now(),
        user=sender  # Можно заменить на `request.user.username`
    )

