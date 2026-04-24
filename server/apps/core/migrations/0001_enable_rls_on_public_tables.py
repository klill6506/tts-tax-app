"""
Enable Row Level Security on all tax-app public-schema tables.

Context
-------
The tts-tax-app and sherpa-1099 app share a single Supabase project
(tmqypsbmswishqkngbrl). The 1099 app's tables already have RLS enabled.
The tax app's Django-created tables did not, which left 60 tables with
real client PII (709 clients, 321 returns, 92K form values) unprotected
against any connection made via the Supabase anon key or a user JWT.

Django itself connects as the Postgres superuser role through the
pgbouncer pooler, which BYPASSES RLS — so enabling RLS here does not
affect Django ORM queries. The protection applies to connections made
via PostgREST / supabase-js / the anon key, which should see zero rows
by default-deny.

Policies are intentionally NOT created in this migration. Default-deny
is the safe starting state. Per-table policies will be added in later
migrations if/when a table needs to be exposed via the REST API.

This migration is idempotent: ALTER TABLE ... ENABLE ROW LEVEL SECURITY
is a no-op if RLS is already enabled.
"""

from django.db import migrations


# All public-schema tables created by the tax app that had
# rls_enabled = false as of 2026-04-21.
# The 1099 app's tables (filers, recipients, forms_1099, tenants, etc.)
# are intentionally excluded — they already have RLS enabled and are
# owned by a separate production app.
RLS_TABLES = [
    # Django internals
    "django_migrations",
    "django_content_type",
    "django_admin_log",
    "django_session",
    # Django auth
    "auth_permission",
    "auth_group",
    "auth_group_permissions",
    "auth_user",
    "auth_user_groups",
    "auth_user_user_permissions",
    # Tax-app models
    "ai_help_helpquery",
    "audit_auditentry",
    "brain_notes",
    "clients_client",
    "clients_cliententitylink",
    "clients_entity",
    "clients_taxyear",
    "depreciation_asset",
    "depreciation_assetevent",
    "depreciation_computeddeprline",
    "depreciation_computedrollup",
    "depreciation_regimepolicy",
    "diagnostics_diagnosticfinding",
    "diagnostics_diagnosticrule",
    "diagnostics_diagnosticrun",
    "documents_clientdocument",
    "firms_firm",
    "firms_firmmembership",
    "firms_preparer",
    "firms_printpackage",
    "imports_trialbalancerow",
    "imports_trialbalanceupload",
    "mappings_mappingrule",
    "mappings_mappingtemplate",
    "portal_accesslog",
    "portal_document",
    "portal_documentrequest",
    "portal_magiclinktoken",
    "portal_message",
    "portal_portaluser",
    "returns_depreciationasset",
    "returns_disposition",
    "returns_formdefinition",
    "returns_formfieldvalue",
    "returns_formline",
    "returns_formsection",
    "returns_interestincome",
    "returns_lineitemdetail",
    "returns_officer",
    "returns_otherdeduction",
    "returns_partner",
    "returns_partnerallocation",
    "returns_preparerinfo",
    "returns_prioryearreturn",
    "returns_rentalproperty",
    "returns_shareholder",
    "returns_shareholderloan",
    "returns_taxpayer",
    "returns_taxreturn",
    "returns_w2income",
]


def _enable_rls_sql() -> str:
    lines = [
        f'ALTER TABLE IF EXISTS public."{t}" ENABLE ROW LEVEL SECURITY;'
        for t in RLS_TABLES
    ]
    return "\n".join(lines)


def _disable_rls_sql() -> str:
    lines = [
        f'ALTER TABLE IF EXISTS public."{t}" DISABLE ROW LEVEL SECURITY;'
        for t in RLS_TABLES
    ]
    return "\n".join(lines)


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=_enable_rls_sql(),
            reverse_sql=_disable_rls_sql(),
        ),
    ]
