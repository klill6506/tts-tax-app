from django.contrib import admin

from .models import TrialBalanceRow, TrialBalanceUpload


class TrialBalanceRowInline(admin.TabularInline):
    model = TrialBalanceRow
    extra = 0
    fields = ("row_number", "account_number", "account_name", "debit", "credit")
    readonly_fields = ("row_number", "account_number", "account_name", "debit", "credit")


@admin.register(TrialBalanceUpload)
class TrialBalanceUploadAdmin(admin.ModelAdmin):
    list_display = (
        "original_filename",
        "tax_year",
        "status",
        "row_count",
        "uploaded_by",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("original_filename",)
    inlines = [TrialBalanceRowInline]
