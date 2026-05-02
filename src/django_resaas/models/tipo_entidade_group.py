from django.db import models
from django_resaas.core.base.models import TimeModel


class TipoEntidadeGroup(TimeModel):
    tipo_entidade = models.ForeignKey(
        "django_resaas.TipoEntidade",
        on_delete=models.CASCADE,
        related_name="tipo_entidade_groups"
    )

    group = models.ForeignKey(
        "auth.Group",
        on_delete=models.CASCADE,
        related_name="group_tipo_entidades"
    )

    class Meta:
        unique_together = ('tipo_entidade', 'group')  # 🔥 evita duplicados

    class RESAAS:
        label_field = "group__name"

    def __str__(self):
        return str(self.group.name)