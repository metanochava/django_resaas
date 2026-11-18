from django.db import models

from django_resaas.saas.core.base.models import TimeModel


class _MobileTab(TimeModel):
    """A tab of the bottom bar shown on phone-sized screens instead of the
    footer (WhatsApp-like). Shown only to a profile whose effective
    permissions include `permission`, while `app` is active for the Entity
    Type and entitled - core/services/mobile_tab_service.py; the frontend
    never decides. At most MAX_TABS are shown, then "More" (the drawer)."""

    label = models.CharField(max_length=40)
    icon = models.CharField(max_length=60, default="circle")
    route = models.CharField(max_length=120, help_text="The route name, e.g. list_lesson")
    permission = models.CharField(max_length=120, help_text="The codename needed, e.g. list_lesson")
    app = models.CharField(max_length=80, help_text="The app label, e.g. pedagogica")
    order = models.PositiveSmallIntegerField(default=10)
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ["order", "label"]


class EntityTypeMobileTab(_MobileTab):
    """The tabs an Entity Type offers (the template, Root's)."""

    entity_type = models.ForeignKey("django_resaas.EntityType", on_delete=models.CASCADE, related_name="mobile_tabs")

    class Meta(_MobileTab.Meta):
        verbose_name = "Entity type mobile tab"
        verbose_name_plural = "Entity type mobile tabs"
        constraints = [models.UniqueConstraint(fields=["entity_type", "route"], name="saas_et_mobile_tab_route")]

    class RESAAS:
        label_field = "label"
        search_fields = ["label", "route", "app"]
        crud = True


class EntityMobileTab(_MobileTab):
    """An Entity's own tabs (its Admin's): when an Entity has any active one,
    they replace its Entity Type's."""

    entity = models.ForeignKey("django_resaas.Entity", on_delete=models.CASCADE, related_name="mobile_tabs")

    class Meta(_MobileTab.Meta):
        verbose_name = "Entity mobile tab"
        verbose_name_plural = "Entity mobile tabs"
        constraints = [models.UniqueConstraint(fields=["entity", "route"], name="saas_entity_mobile_tab_route")]

    class RESAAS:
        label_field = "label"
        search_fields = ["label", "route", "app"]
        crud = True
