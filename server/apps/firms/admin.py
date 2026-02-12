from django.contrib import admin

from .models import Firm, FirmMembership


class FirmMembershipInline(admin.TabularInline):
    model = FirmMembership
    extra = 1
    fields = ("user", "role", "is_active")


@admin.register(Firm)
class FirmAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "member_count", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    inlines = [FirmMembershipInline]

    @admin.display(description="Members")
    def member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


@admin.register(FirmMembership)
class FirmMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "firm", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "firm")
    search_fields = ("user__username", "user__email", "firm__name")
    raw_id_fields = ("user",)
