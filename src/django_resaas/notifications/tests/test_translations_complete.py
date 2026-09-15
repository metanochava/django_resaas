"""Same guard as hr/tests/test_translations_complete.py: notifications
had no lang/ directory at all before this fix, and sidebar.py's menu
values / dashboard.py's widget labels reach tdc()/Translate.tdc() as
lookup keys - both must be canonical English and translated into
pt-pt/fr-fr/es-es (via notifications' own lang/<code>.py, or the
shared saas core one)."""
import re

import pytest

from django_resaas.notifications.sidebar import ALL as NOTIF_SIDEBAR
from django_resaas.notifications.dashboard import DASHBOARD as NOTIF_DASHBOARD
from django_resaas.notifications.enums import Channel, Category, Priority, OutboxStatus, ErrorType
from django_resaas.notifications.lang import ptpt as notif_ptpt
from django_resaas.notifications.lang import frfr as notif_frfr
from django_resaas.notifications.lang import eses as notif_eses
from django_resaas.saas.lang import ptpt as saas_ptpt
from django_resaas.saas.lang import frfr as saas_frfr
from django_resaas.saas.lang import eses as saas_eses

pytestmark = pytest.mark.django_db

NON_ENGLISH_CHARS = re.compile(r"[àâãçéêíóôõúÀ-ÿ]")

PT = {**saas_ptpt.key_value, **notif_ptpt.key_value}
FR = {**saas_frfr.key_value, **notif_frfr.key_value}
ES = {**saas_eses.key_value, **notif_eses.key_value}


def _sidebar_menu_labels(entries):
    for entry in entries:
        if "menu" in entry:
            yield entry["menu"]
        if "submenu" in entry:
            yield from _sidebar_menu_labels(entry["submenu"])


def _dashboard_labels(dashboard):
    yield dashboard["label"]
    for widget in dashboard["widgets"]:
        yield widget["label"]


def _choice_labels():
    for enum in (Channel, Category, Priority, OutboxStatus, ErrorType):
        for _, label in enum.choices:
            yield label


ALL_LABELS = sorted(set(
    list(_sidebar_menu_labels(NOTIF_SIDEBAR))
    + list(_dashboard_labels(NOTIF_DASHBOARD))
    + list(_choice_labels())
))


@pytest.mark.parametrize("label", ALL_LABELS)
def test_label_is_canonical_english(label):
    assert not NON_ENGLISH_CHARS.search(label), (
        f"notifications label {label!r} looks non-English - "
        "canonical strings must originate in English (CLAUDE.md #82)"
    )


@pytest.mark.parametrize("label", ALL_LABELS)
def test_label_is_translated(label):
    for lang_name, lang in (("pt-pt", PT), ("fr-fr", FR), ("es-es", ES)):
        assert label in lang, f"{label!r} has no {lang_name} translation"
