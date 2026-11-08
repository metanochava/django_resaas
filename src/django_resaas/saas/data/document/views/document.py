from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from django_resaas.saas.models.document import Document, DocumentFile
from django_resaas.saas.data.document.serializers.document import DocumentSerializer
from django_resaas.saas.core.base.views import BaseAPIView, registerView
from django_resaas.saas.core.decorators.action import resaas_action
from django_resaas.saas.core.exceptions import ResaasAPIException

MAX_FILES_PER_UPLOAD = 20


def add_document_files(request, document, files):
    """Stores each uploaded file as a DocumentFile of `document` (a document
    may have several files). Shared by the documents/{id}/files/ action, the
    Person add_document action and the person registration service."""
    for upload in files or []:
        if not upload:
            continue
        DocumentFile.objects.create(
            document=document,
            arquivo=upload,
            name=getattr(upload, "name", "") or "",
            state="Active",
            created_by=getattr(request, "user", None),
            updated_by=getattr(request, "user", None),
        )


@registerView('documents')
class DocumentAPIView(BaseAPIView):
    serializer_class = DocumentSerializer
    queryset = Document.objects.all().order_by('-id')
    lookup_field = "id"

    # ------------------------------------------------------------
    # FILES OF A DOCUMENT (sub-resource documents/{id}/files/)
    # The same permission as changing the document; the document comes
    # from the scoped queryset (get_object), so only this tenant's.
    # ------------------------------------------------------------
    @resaas_action(detail=True, methods=["post"], url_path="files", label="Add files",
                   icon="attach_file", permission="change_document", visible=False)
    def files(self, request, *args, **kwargs):
        """multipart: files=<file> (repeated). Answers the document with all
        its files."""
        document = self.get_object()
        uploads = request.FILES.getlist("files")
        if not uploads:
            raise ResaasAPIException("Choose at least one file.", code="no_files",
                                     status_code=status.HTTP_400_BAD_REQUEST)
        if len(uploads) > MAX_FILES_PER_UPLOAD:
            raise ResaasAPIException("Too many files at once.", code="too_many_files",
                                     status_code=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            add_document_files(request, document, uploads)
        return Response(DocumentSerializer(document, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)

    @resaas_action(detail=True, methods=["delete"], url_path=r"files/(?P<file_id>[^/.]+)",
                   label="Remove file", icon="delete", permission="change_document", visible=False)
    def remove_file(self, request, file_id=None, *args, **kwargs):
        document = self.get_object()
        row = DocumentFile.objects.filter(document=document, id=file_id).first()
        if row is None:
            raise ResaasAPIException("File not found.", code="file_not_found",
                                     status_code=status.HTTP_404_NOT_FOUND)
        row.delete(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
