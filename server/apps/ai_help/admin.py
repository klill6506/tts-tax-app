from django.contrib import admin

from .models import HelpQuery


@admin.register(HelpQuery)
class HelpQueryAdmin(admin.ModelAdmin):
    list_display = ("form_code", "mode", "question", "user", "created_at")
    list_filter = ("form_code", "mode")
    search_fields = ("question", "response")
    readonly_fields = ("id", "user", "firm", "form_code", "section", "question", "response", "mode", "created_at")
