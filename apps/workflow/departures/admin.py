"""T-3-005: admin для выездов и контактов."""
from django.contrib import admin
from apps.workflow.departures.models import Departure, Executor, DepartureStatus, Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "description", "phone_number")
    search_fields = ("first_name", "last_name", "phone_number")
    list_filter = ("displays",)
    filter_horizontal = ("displays",)


@admin.register(Executor)
class ExecutorAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "executor_role", "phone_number")
    search_fields = ("first_name", "last_name", "phone_number")


@admin.register(Departure)
class DepartureAdmin(admin.ModelAdmin):
    list_display = ("id", "description", "status", "executor", "time_start", "time_end")
    list_filter = ("status",)
    search_fields = ("description",)


@admin.register(DepartureStatus)
class DepartureStatusAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "order", "is_terminal")
