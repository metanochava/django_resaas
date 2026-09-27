from django.conf import settings
from django.db import models

from django_resaas.saas.core.base.models import TimeModel


class SiteContactMessage(TimeModel):
    """A message sent through the contact form of an Entity's public site.

    The Entity comes from the site the visitor is on (the request Origin
    matched against Entity.site, like GET site/), never from the request
    body. There is no Branch: a public visitor does not choose one and
    nothing may be picked on their behalf, so staff see the messages of
    their whole Entity (BaseAPIView scopes by entity_id only).
    """

    STATUS_NEW = "new"
    STATUS_HANDLED = "handled"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_HANDLED, "Handled"),
    ]

    entity = models.ForeignKey(
        "django_resaas.Entity",
        on_delete=models.CASCADE,
        related_name="site_contact_messages",
        editable=False,
    )
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    message = models.TextField()
    # the host the form was sent from (e.g. clinicaamal.co.mz)
    site = models.CharField(max_length=255, editable=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    handled_at = models.DateTimeField(null=True, blank=True, editable=False)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="handled_site_contact_messages",
        editable=False,
    )

    def __str__(self):
        return f"{self.name} ({self.site})"

    class Meta:
        verbose_name = "Site contact message"
        verbose_name_plural = "Site contact messages"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["entity", "status", "created_at"])]

    class RESAAS:
        label_field = "name"
        search_fields = ["name", "phone", "email", "message"]
        crud = True
