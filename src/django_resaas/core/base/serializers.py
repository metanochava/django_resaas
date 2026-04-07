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
): pass