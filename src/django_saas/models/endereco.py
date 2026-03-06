import uuid
from django.db import models
from django_saas.core.base.models import TimeModel


class Endereco(TimeModel):
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    rua = models.CharField(max_length=255, null=True, blank=True)
    numero = models.CharField(max_length=50, null=True, blank=True)
    bairro = models.CharField(max_length=100, null=True, blank=True)
    cidade = models.CharField(max_length=100, null=True, blank=True)
    provincia = models.CharField(max_length=100, null=True, blank=True)
    pais = models.CharField(max_length=100, default='Moçambique')
    codigo_postal = models.CharField(max_length=20, null=True, blank=True)
    complemento = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Endereço'
        verbose_name_plural = 'Endereços'
        permissions = ()
        

    def __str__(self):
        return ', '.join(filter(None, [
            self.rua,
            self.numero,
            self.bairro,
            self.cidade,
            self.provincia,
            self.pais,
        ]))
