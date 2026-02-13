from django.contrib import admin

from .models import FormDefinition, FormFieldValue, FormLine, FormSection, TaxReturn


class FormSectionInline(admin.TabularInline):
    model = FormSection
    extra = 0


class FormLineInline(admin.TabularInline):
    model = FormLine
    extra = 0
    fields = ("line_number", "label", "field_type", "mapping_key", "is_computed", "sort_order")


@admin.register(FormDefinition)
class FormDefinitionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "tax_year_applicable")
    inlines = [FormSectionInline]


@admin.register(FormSection)
class FormSectionAdmin(admin.ModelAdmin):
    list_display = ("form", "code", "title", "sort_order")
    list_filter = ("form",)
    inlines = [FormLineInline]


class FieldValueInline(admin.TabularInline):
    model = FormFieldValue
    extra = 0
    fields = ("form_line", "value", "is_overridden")
    readonly_fields = ("form_line",)


@admin.register(TaxReturn)
class TaxReturnAdmin(admin.ModelAdmin):
    list_display = ("tax_year", "form_definition", "status", "created_by", "created_at")
    list_filter = ("status", "form_definition")
    inlines = [FieldValueInline]
