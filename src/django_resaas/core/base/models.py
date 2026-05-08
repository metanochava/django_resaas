from django.conf import settings
from django.db import models
import uuid
from django.utils import timezone
import os 
from .mixins.model.label_value import LabelValueMixin


def file_path(instance, file_name, pasta=""):
    ext = os.path.splitext(file_name)[1].lower()
    unique_name = f"{uuid.uuid4()}{ext}"

    pasta = pasta.strip("/")

    instance_id = instance.id or uuid.uuid4()

    return (
        f"{instance.entity.entity_type.id}/"
        f"{instance.entity.id}/"
        f"{instance_id}/"
        f"{pasta}/{unique_name}" if pasta else
        f"{instance.entity.entity_type.id}/"
        f"{instance.entity.id}/"
        f"{instance_id}/{unique_name}"
    )


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)

    def soft_delete(self):
        now = timezone.now()
        return self.update(deleted_at=now, updated_at=now)

    def restore(self):
        return self.update(deleted_at=None)

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


class SoftBaseModel(LabelValueMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()
    deleted_objects = DeletedManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, user=None):
        self.deleted_at = timezone.now()

        if user and hasattr(self, "updated_by"):
            self.updated_by = user

        fields = ["deleted_at"]

        if hasattr(self, "updated_by"):
            fields.append("updated_by")

        self.save(update_fields=fields)

    def restore(self, user=None):
        self.deleted_at = None

        if user and hasattr(self, "updated_by"):
            self.updated_by = user

        fields = ["deleted_at"]

        if hasattr(self, "updated_by"):
            fields.append("updated_by")

        self.save(update_fields=fields)

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
        choices=((0, 'Inativo'), (1, 'Activo')),
    )

    class Meta:
        abstract = True


class BaseModel(TimeModel):
    entity = models.ForeignKey(
        "django_resaas.Entity",
        on_delete=models.CASCADE,
        related_name="%(class)s_entity"
    )

    branch = models.ForeignKey(
        "django_resaas.Branch",
        on_delete=models.CASCADE,
        related_name="%(class)s_branch"
    )

    class Meta:
        abstract = True