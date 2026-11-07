"""One tone per state/status value, the same as quasar_resaas
utils/status.js (keep both lists in step): active-like values are
positive, inactive-like values negative, every other known value its own
tone, unknown values grey. Used where the backend renders a state itself
(PDF lists)."""
import re

_TONES = {
    "positive": (
        "active", "activo", "ativo", "enabled", "approved", "accepted", "completed", "complete",
        "done", "paid", "validated", "released", "collected", "received", "won", "success",
        "successful", "sent", "delivered", "posted", "confirmed", "resolved", "hired", "present",
        "available", "enrolled", "attending", "finished", "signed", "verified",
    ),
    "negative": (
        "inactive", "unactive", "deactive", "deactivated", "disabled", "inativo", "inactivo",
        "cancelled", "canceled", "rejected", "failed", "error", "expired", "suspended", "blocked",
        "lost", "void", "voided", "terminated", "dismissed", "missed", "absent", "withdrawn",
        "refused", "declined", "revoked",
    ),
    "warning": (
        "pending", "waiting", "on_hold", "in_progress", "processing", "retry", "queued",
        "under_review", "review", "partial", "partially_received", "partially_paid", "late",
        "probation", "screening", "interview", "dispatching", "reversed", "leave", "overdue",
    ),
    "info": (
        "scheduled", "submitted", "open", "new", "requested", "reserved", "applied", "shortlisted",
        "offered", "ongoing", "referral", "not_started", "checked_in", "reviewed", "calculated",
        "in_service", "called",
    ),
    "grey": ("draft", "closed", "retired", "resigned", "off", "dropped", "other", "archived"),
    "dark": ("deceased",),
}

_TONE_BY_VALUE = {value: tone for tone, values in _TONES.items() for value in values}


def _normalise(value):
    return re.sub(r"[\s-]+", "_", str(value if value is not None else "").strip().lower())


def status_tone(value, label=None):
    """'positive', 'negative', 'warning', 'info', 'grey' or 'dark'."""
    return _TONE_BY_VALUE.get(_normalise(value)) or _TONE_BY_VALUE.get(_normalise(label)) or "grey"
