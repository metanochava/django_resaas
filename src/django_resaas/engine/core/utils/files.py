import uuid
import os


class UploadPath:

    def __init__(self, pasta=""):
        self.pasta = pasta.strip("/") if pasta else ""

    def __call__(self, instance, file_name):
        ext = os.path.splitext(file_name)[1].lower()
        unique_name = f"{uuid.uuid4()}{ext}"

        instance_id = instance.id or "tmp"

        return (
            f"{instance.entity.entity_type.id}/"
            f"{instance.entity.id}/"
            f"{instance_id}/"
            f"{self.pasta}/{unique_name}"
            if self.pasta else
            f"{instance.entity.entity_type.id}/"
            f"{instance.entity.id}/"
            f"{instance_id}/{unique_name}"
        )

    def deconstruct(self):
        return (
            "django_resaas.engine.core.utils.files.UploadPath",
            [],
            {"pasta": self.pasta},
        )

# def upload_path(pasta=""):

#     def wrapper(instance, file_name):
#         ext = os.path.splitext(file_name)[1].lower()
#         unique_name = f"{uuid.uuid4()}{ext}"

#         pasta_clean = pasta.strip("/")
#         instance_id = instance.id or "tmp"

#         return (
#             f"{instance.entity.entity_type.id}/"
#             f"{instance.entity.id}/"
#             f"{instance_id}/"
#             f"{pasta_clean}/{unique_name}"
#             if pasta_clean else
#             f"{instance.entity.entity_type.id}/"
#             f"{instance.entity.id}/"
#             f"{instance_id}/{unique_name}"
#         )

#     return wrapper




def upload_path(pasta=""):
    return UploadPath(pasta)