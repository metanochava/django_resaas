
from django.db import models
from django_saas.core.base.models import TimeModel
class TipoEntidadeGroup(TimeModel):
    tipo_entidade = models.ForeignKey("django_saas.TipoEntidade", on_delete=models.CASCADE)
    group = models.ForeignKey("auth.Group", on_delete=models.CASCADE)
    

    class Meta:
        permissions = (
            
        )

    def __str__(self):
        return str(self.group.name)

