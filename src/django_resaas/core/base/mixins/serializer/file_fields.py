import os
import mimetypes
from django.db import models
from django_resaas.core.utils.full_path import FullPath


class FileFieldsMixin:

    permanent_fields_files = []

    # 🔥 identifica tipo do ficheiro
    def _file_kind(self, ext):
        ext = ext.lower()

        if ext in ["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"]:
            return "image"

        if ext in ["pdf"]:
            return "pdf"

        if ext in ["mp4", "avi", "mov", "webm", "mkv"]:
            return "video"

        if ext in ["mp3", "wav", "ogg", "m4a"]:
            return "audio"

        return "file"

    def _file_representation(self, request, file, field_name):
        if not file:
            return None

        try:
            if not request:
                return None

            url = FullPath.url(
                request,
                file.url,
                temporary=field_name not in self.permanent_fields_files
            )

            name = os.path.basename(file.name)
            ext = os.path.splitext(name)[1].lstrip('.').lower()

            # 🔥 MIME TYPE
            mime_type, _ = mimetypes.guess_type(name)

            return {
                "url": url,
                "name": name,
                "ext": ext,
                "kind": self._file_kind(ext),
                "mime_type": mime_type,  # 🔥 NOVO
                "size": getattr(file, "size", None),
            }

        except Exception:
            return None