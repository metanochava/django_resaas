
from django.db import models
from django.contrib.auth.models import Group
from django_resaas.core.base.models import TimeModel

class Profissao(TimeModel):
    
    nome = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.nome
    
    class RESAAS:
        label_field = "nome"
        # route="view_entidade"