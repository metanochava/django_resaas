import uuid
from django.db import models
from django_resaas.core.base.models import TimeModel

from django.contrib.contenttypes.fields import GenericRelation


import uuid
from django.db import models
from django.contrib.contenttypes.fields import GenericRelation


class Person(TimeModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        'django_resaas.User',
        on_delete=models.CASCADE,
        related_name='person',
        null=True,
        blank=True
    )

    # 📌 Dados básicos
    name = models.CharField(max_length=100, null=True)
    surname = models.CharField(max_length=100, null=True)
    full_name = models.CharField(max_length=200, null=True, blank=True)

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
    address = models.ForeignKey(
        'django_resaas.Address',
        on_delete=models.SET_NULL,  # 🔥 melhor que CASCADE
        null=True,
        blank=True,
        related_name='persons'
    )

    # 📌 Documents
    documents = GenericRelation('django_resaas.Document')

    
    def save(self, *args, **kwargs):
        # 🔥 Gera name completo automaticamente
        if self.name and self.surname:
            self.full_name = f"{self.name} {self.surname}".strip()

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


    class Meta:
        verbose_name = 'Person'
        verbose_name_plural = 'Persons'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['email']),
        ]

    class RESAAS:
        label_field = "name surname"
        searchable_fields = ["name", "surname", "email", "full_name"]
        crud = True
        routes={
            'list': "add_person",
            'view': "view_person",
            'add': "add_person",
            'change': "change_person"
        }

    def __str__(self):
        return self.full_name or self.name or ""