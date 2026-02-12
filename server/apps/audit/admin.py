from django.contrib import admin

from .models import AuditEntry


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "actor", "action", "model_name", "record_id")
    list_filter = ("action", "model_name")
    search_fields = ("record_id", "actor__username")
    readonly_fields = (
        "id",
        "actor",
        "firm",
        "action",
        "model_name",
        "record_id",
        "changes",
        "timestamp",
    )
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
