
from django.db import models
from django_resaas.core.base.models import TimeModel
class TipoEntidadeModulo(TimeModel):
    tipo_entidade = models.ForeignKey("django_resaas.TipoEntidade", on_delete=models.CASCADE)
    modulo = models.ForeignKey("django_resaas.Modulo", on_delete=models.CASCADE)

    class Meta:
        permissions = (
            
        )

    def __str__(self):
        return str(self.tipo_entidade.nome) + "  |  " + str(self.modulo.nome)

