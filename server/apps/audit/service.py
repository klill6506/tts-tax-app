"""
Audit logging service.

Usage in viewsets:
    from apps.audit.service import log_create, log_update, log_delete

    def perform_create(self, serializer):
        instance = serializer.save(...)
        log_create(self.request, instance)
"""

from __future__ import annotations

from typing import Any

from django.db import models

from .models import AuditAction, AuditEntry

# Fields that must never appear in audit change logs.
PII_FIELDS = frozenset({
    "ssn", "ein", "itin", "tax_id", "social_security",
    "ssn_encrypted", "ein_encrypted",
})


def _safe_value(field_name: str, value: Any) -> Any:
    """Redact PII fields; convert non-serializable values to strings."""
    if field_name.lower() in PII_FIELDS:
        return "***REDACTED***"
    if isinstance(value, models.Model):
        return str(value.pk)
    return value


def _diff_instance(old: dict, new: dict) -> dict:
    """Return {field: {old, new}} for fields that changed."""
    changes = {}
    for key in new:
        if key in ("updated_at",):
            continue
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            changes[key] = {
                "old": _safe_value(key, old_val),
                "new": _safe_value(key, new_val),
            }
    return changes


def _model_label(instance: models.Model) -> str:
    return instance._meta.label  # e.g. "clients.Client"


def _record_id(instance: models.Model) -> str:
    return str(instance.pk)


def _get_firm(request):
    return getattr(request, "firm", None)


def snapshot(instance: models.Model) -> dict:
    """
    Capture a serializable snapshot of an instance's field values.
    Call this BEFORE saving to capture old state for updates.
    """
    data = {}
    for field in instance._meta.concrete_fields:
        value = getattr(instance, field.attname)
        data[field.attname] = _safe_value(field.attname, value)
    return data


def log_create(request, instance: models.Model) -> AuditEntry:
    return AuditEntry.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        firm=_get_firm(request),
        action=AuditAction.CREATE,
        model_name=_model_label(instance),
        record_id=_record_id(instance),
        changes={},
    )


def log_update(
    request, instance: models.Model, old_snapshot: dict
) -> AuditEntry | None:
    new_snap = snapshot(instance)
    changes = _diff_instance(old_snapshot, new_snap)
    if not changes:
        return None  # Nothing meaningful changed
    return AuditEntry.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        firm=_get_firm(request),
        action=AuditAction.UPDATE,
        model_name=_model_label(instance),
        record_id=_record_id(instance),
        changes=changes,
    )


def log_delete(request, instance: models.Model) -> AuditEntry:
    return AuditEntry.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        firm=_get_firm(request),
        action=AuditAction.DELETE,
        model_name=_model_label(instance),
        record_id=_record_id(instance),
        changes={},
    )
