from rest_framework import serializers

from .mixins.serializer.dynamic_fields import DynamicFieldsMixin
from .mixins.serializer.utils import SerializerUtilsMixin
from .mixins.serializer.file_fields import FileFieldsMixin
from .mixins.serializer.representation import RepresentationMixin


class BaseSerializer(
    DynamicFieldsMixin,
    SerializerUtilsMixin,
    FileFieldsMixin,
    RepresentationMixin,
    serializers.ModelSerializer
): 
    permanent_fields_files = []
    label_field = None
    value_field = "id"

    DEFAULT_READ_ONLY_FIELDS = (
        "id",
        "entity",
        "branch",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    def get_fields(self):

        fields = super().get_fields()

        for name in self.DEFAULT_READ_ONLY_FIELDS:

            if name in fields:
                fields[name].read_only = True

        return fields