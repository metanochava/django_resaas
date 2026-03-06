from django.conf import settings
from django.db import models
import uuid
# good

from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)

    def soft_delete(self):
        return self.update( deleted_at=timezone.now())

    def restore(self):
        return self.update( deleted_at=None)

    def hard_delete(self):
        return super().delete()


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()

class DeletedManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftBaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()      # só ativos
    all_objects = AllObjectsManager()  # tudo (ativos + apagados)
    deleted_objects = DeletedManager()  #  só apagados

    class Meta:
        abstract = True


    def delete(self, using=None, keep_parents=False, user=None):
        self.deleted_at = timezone.now()
        if user:
            self.updated_by = user
        self.save(update_fields=["deleted_at", "updated_by"])

    def restore(self, user=None):
        self.deleted_at = None
        if user:
            self.updated_by = user
        self.save(update_fields=["deleted_at", "updated_by"])

    def hard_delete(self):
        super().delete()

class TimeModel(SoftBaseModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_created",
        
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_updated"
    )
    
    estado = models.IntegerField(
        default=0,
        null=True,
        choices=((0, 'Inativo'), (1, 'Ativo')),
    )
    class Meta:
        abstract = True

class BaseModel(TimeModel):
    entidade = models.ForeignKey(
        "django_saas.Entidade",
        on_delete=models.CASCADE,
        related_name="%(class)s_entidade"
    )

    sucursal = models.ForeignKey(
        "django_saas.Sucursal",
        on_delete=models.CASCADE,
        related_name="%(class)s_sucursal"
    )


    class Meta:
        abstract = True



