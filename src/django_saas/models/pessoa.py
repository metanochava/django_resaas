import uuid
from django.db import models
from django_saas.core.base.models import TimeModel

from django.contrib.contenttypes.fields import GenericRelation


import uuid
from django.db import models
from django.contrib.contenttypes.fields import GenericRelation


class Pessoa(TimeModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        'django_saas.User',
        on_delete=models.CASCADE,
        related_name='pessoa',
        null=True,
        blank=True
    )

    # 📌 Dados básicos
    nome = models.CharField(max_length=100, null=True)
    apelido = models.CharField(max_length=100, null=True)
    nome_completo = models.CharField(max_length=200, null=True, blank=True)

    # 📌 Identificação
    GENERO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('O', 'Outro'),
    ]

    genero = models.CharField(
        max_length=1,
        choices=GENERO_CHOICES,
        null=True,
        blank=True
    )

    data_nascimento = models.DateField(null=True, blank=True)
    nacionalidade = models.CharField(max_length=100, null=True, blank=True)

    # 📌 Contactos
    email = models.EmailField(null=True, blank=True, unique=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    telefone_alternativo = models.CharField(max_length=20, null=True, blank=True)

    # 📌 Endereço
    endereco = models.ForeignKey(
        'django_saas.Endereco',
        on_delete=models.SET_NULL,  # 🔥 melhor que CASCADE
        null=True,
        blank=True,
        related_name='pessoas'
    )

    # 📌 Documentos
    documentos = GenericRelation('django_saas.Documento')



    # 📌 Extra
    observacoes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Pessoa'
        verbose_name_plural = 'Pessoas'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['nome']),
            models.Index(fields=['email']),
        ]

    def save(self, *args, **kwargs):
        # 🔥 Gera nome completo automaticamente
        if self.nome and self.apelido:
            self.nome_completo = f"{self.nome} {self.apelido}".strip()

        # 🔥 Normaliza email
        if self.email:
            self.email = self.email.lower()

        super().save(*args, **kwargs)

    def idade(self):
        from datetime import date
        if self.data_nascimento:
            today = date.today()
            return today.year - self.data_nascimento.year - (
                (today.month, today.day) < (self.data_nascimento.month, self.data_nascimento.day)
            )
        return None

    def __str__(self):
        return self.nome_completo or self.nome or "Sem nome"