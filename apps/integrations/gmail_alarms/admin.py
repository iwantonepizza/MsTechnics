from django.contrib import admin

from .models import AlarmEvent


@admin.register(AlarmEvent)
class AlarmEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "type",
        "display",
        "receiving_card_no",
        "occurred_at",
        "resolved_at",
    )
    list_filter = ("type", "display", "resolved_at")
    search_fields = ("device_id", "screen_name_raw", "raw_email_subject", "gmail_message_id")
    readonly_fields = ("received_at",)
