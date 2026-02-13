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


@admin.register(TrialBalanceRow)
class TrialBalanceRowAdmin(admin.ModelAdmin):
    list_display = ("row_number", "account_name", "account_number", "debit", "credit", "upload")
    list_filter = ("upload",)
    search_fields = ("account_name", "account_number")
    ordering = ("upload", "row_number")
