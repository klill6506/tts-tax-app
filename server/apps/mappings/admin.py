from django.contrib import admin

from .models import MappingRule, MappingTemplate


class MappingRuleInline(admin.TabularInline):
    model = MappingRule
    extra = 1
    fields = ("match_mode", "match_value", "target_line", "target_description", "priority")


@admin.register(MappingTemplate)
class MappingTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "firm", "client", "is_default", "rule_count", "created_at")
    list_filter = ("is_default", "firm")
    search_fields = ("name",)
    inlines = [MappingRuleInline]

    @admin.display(description="Rules")
    def rule_count(self, obj):
        return obj.rules.count()
