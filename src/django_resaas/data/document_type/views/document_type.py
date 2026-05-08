
from rest_framework import viewsets
from django_resaas.models.document import DocumentType
from django_resaas.data.document_type.serializers.document_type import DocumentTypeSerializer


class  DocumentTypeAPIView(viewsets.ModelViewSet):
    serializer_class = DocumentTypeSerializer
    queryset = DocumentType.objects.all()
    def get_queryset(self):
        return self.queryset.filter().order_by('-id')

    def update(self, request, *args, **kwargs):
        partial = request.method == 'PATCH'

        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)