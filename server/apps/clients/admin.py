from django.contrib import admin

from .models import Client, ClientEntityLink, Entity, TaxYear


class EntityInline(admin.TabularInline):
    model = Entity
    extra = 0
    fields = ("name", "entity_type", "created_at")
    readonly_fields = ("created_at",)


class ClientEntityLinkInline(admin.TabularInline):
    model = ClientEntityLink
    fk_name = "client"
    extra = 0
    fields = ("entity", "role", "ownership_percentage", "is_primary")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "firm", "status", "entity_count", "created_at")
    list_filter = ("status", "firm")
    search_fields = ("name",)
    inlines = [EntityInline, ClientEntityLinkInline]

    @admin.display(description="Entities")
    def entity_count(self, obj):
        return obj.entities.count()


class TaxYearInline(admin.TabularInline):
    model = TaxYear
    extra = 0
    fields = ("year", "status", "created_by", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ("name", "client", "entity_type", "tax_year_count", "created_at")
    list_filter = ("entity_type",)
    search_fields = ("name", "client__name")
    inlines = [TaxYearInline]

    @admin.display(description="Tax Years")
    def tax_year_count(self, obj):
        return obj.tax_years.count()


@admin.register(TaxYear)
class TaxYearAdmin(admin.ModelAdmin):
    list_display = ("entity", "year", "status", "created_by", "created_at")
    list_filter = ("status", "year")
    search_fields = ("entity__name", "entity__client__name")
