import os

from django.db import models
from rest_framework import serializers
from django_saas.core.utils.full_path import FullPath

class BaseSerializer(serializers.ModelSerializer):
    """
    Serializer base que protege automaticamente
    todos os FileField e ImageField.
    """

    permanent_fields_files = []

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')

        if not request:
            return data

        permanent = set(getattr(self, 'permanent_fields_files', []))

        for field in instance._meta.fields:
            
            if not isinstance(field, (models.FileField, models.ImageField)):
                continue

            file = getattr(instance, field.name)
            

            if not file:
                data[field.name] = None
                continue

            temporary = field.name not in permanent

            try:
                url = FullPath.url(request, file.url, temporary=temporary)
                filename = os.path.basename(file.name)
                ext = os.path.splitext(filename)[1].lstrip('.').lower()

                data[field.name] = {
                    'url': url,
                    'name': filename,
                    'ext': ext,
                    'size': getattr(file, 'size', None)
                }
            except Exception as e:
                print("❌ ERRO AO PROCESSAR FILE:", e)
                data[field.name] = None

        return data
