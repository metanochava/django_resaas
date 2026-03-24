import uuid
import os

def upload_path(pasta=""):

    def wrapper(instance, file_name):
        ext = os.path.splitext(file_name)[1].lower()
        unique_name = f"{uuid.uuid4()}{ext}"

        pasta_clean = pasta.strip("/")
        instance_id = instance.id or "tmp"

        return (
            f"{instance.entidade.tipo_entidade.id}/"
            f"{instance.entidade.id}/"
            f"{instance_id}/"
            f"{pasta_clean}/{unique_name}"
            if pasta_clean else
            f"{instance.entidade.tipo_entidade.id}/"
            f"{instance.entidade.id}/"
            f"{instance_id}/{unique_name}"
        )

    return wrapper