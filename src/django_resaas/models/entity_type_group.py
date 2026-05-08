from django.db import models
from django_resaas.core.base.models import TimeModel


class EntityTypeGroup(TimeModel):
    entity_type = models.ForeignKey(
        "django_resaas.EntityType",
        on_delete=models.CASCADE,
        related_name="entity_type_groups"
    )

    group = models.ForeignKey(
        "auth.Group",
        on_delete=models.CASCADE,
        related_name="group_entity_types"
    )

    class Meta:
        unique_together = ('entity_type', 'group')  # 🔥 evita duplicados

    class RESAAS:
        label_field = "group__name"

    def __str__(self):
        return str(self.group.name)