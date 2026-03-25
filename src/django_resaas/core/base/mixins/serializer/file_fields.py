import os
from django.db import models
from django_resaas.core.utils.full_path import FullPath


class FileFieldsMixin:

    permanent_fields_files = []

    def _file_representation(self, request, file, field_name):
        if not file:
            return None

        try:
            url = FullPath.url(
                request,
                file.url,
                temporary=field_name not in self.permanent_fields_files
            )

            name = os.path.basename(file.name)
            ext = os.path.splitext(name)[1].lstrip('.').lower()

            return {
                "url": url,
                "name": name,
                "ext": ext,
                "size": getattr(file, "size", None),
            }
        except Exception:
            return None