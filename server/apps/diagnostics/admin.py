from django.contrib import admin

from .models import DiagnosticFinding, DiagnosticRule, DiagnosticRun


@admin.register(DiagnosticRule)
class DiagnosticRuleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "severity", "is_active")
    list_filter = ("severity", "is_active")
    search_fields = ("code", "name")


class FindingInline(admin.TabularInline):
    model = DiagnosticFinding
    extra = 0
    fields = ("severity", "rule", "message", "is_resolved")
    readonly_fields = ("severity", "rule", "message")


@admin.register(DiagnosticRun)
class DiagnosticRunAdmin(admin.ModelAdmin):
    list_display = ("tax_year", "status", "finding_count", "run_by", "started_at")
    list_filter = ("status",)
    inlines = [FindingInline]
