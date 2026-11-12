from django.conf import settings
from django.db import models

from django_resaas.saas.core.base.models import TimeModel


class FormDefinition(TimeModel):
    """One layer of a form (saas/core/forms): a versioned definition of `key`
    for the platform, an entity type, an Entity or a Branch. The resolved form
    merges the latest published version of each layer, most general first
    (saas/core/forms/merge.py). A published version never changes: a change
    is a new version. Not tenant-bound by itself (platform / entity type
    layers have no Entity) - the views scope it explicitly."""

    LEVEL_PLATFORM = "platform"
    LEVEL_ENTITY_TYPE = "entity_type"
    LEVEL_ENTITY = "entity"
    LEVEL_BRANCH = "branch"
    LEVELS = (LEVEL_PLATFORM, LEVEL_ENTITY_TYPE, LEVEL_ENTITY, LEVEL_BRANCH)
    LEVEL_CHOICES = tuple((level, level.replace("_", " ").capitalize()) for level in LEVELS)

    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CHOICES = ((STATUS_DRAFT, "Draft"), (STATUS_PUBLISHED, "Published"))

    key = models.CharField(max_length=120, db_index=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    entity_type = models.ForeignKey("django_resaas.EntityType", null=True, blank=True, on_delete=models.CASCADE,
                                    related_name="form_definitions")
    entity = models.ForeignKey("django_resaas.Entity", null=True, blank=True, on_delete=models.CASCADE,
                               related_name="form_definitions")
    branch = models.ForeignKey("django_resaas.Branch", null=True, blank=True, on_delete=models.CASCADE,
                               related_name="form_definitions")
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    definition = models.JSONField()
    published_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "Form definition"
        verbose_name_plural = "Form definitions"
        ordering = ["key", "level", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["key", "level", "entity_type", "entity", "branch", "version"],
                                    name="resaas_form_definition_unique_version"),
        ]

    class RESAAS:
        label_field = "key"
        search_fields = ["key"]
        crud = False

    def __str__(self):
        return f"{self.key} ({self.level} v{self.version})"


class FormDraft(TimeModel):
    """What a user typed in a form before submitting it (autosave) - temporary
    state, never business data: the submission goes to the domain endpoint.
    One per user, Entity, form and context (e.g. the record being edited)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="form_drafts")
    entity = models.ForeignKey("django_resaas.Entity", on_delete=models.CASCADE, related_name="form_drafts")
    key = models.CharField(max_length=120)
    context = models.CharField(max_length=120, blank=True, default="")
    data = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Form draft"
        verbose_name_plural = "Form drafts"
        constraints = [
            models.UniqueConstraint(fields=["user", "entity", "key", "context"], name="resaas_form_draft_unique"),
        ]

    class RESAAS:
        label_field = "key"
        search_fields = ["key"]
        crud = False
