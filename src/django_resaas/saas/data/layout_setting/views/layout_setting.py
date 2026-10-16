
from django_resaas.saas.core.base.access import ActionPermissionMixin, ExplicitAccessMixin
from rest_framework import filters
from rest_framework import viewsets


from django_resaas.saas.models.layout_setting import LayoutSetting
from django_resaas.saas.data.layout_setting.serializers.layout_setting import LayoutSettingSerializer


class LayoutSettingAPIView(ActionPermissionMixin, ExplicitAccessMixin, viewsets.ModelViewSet):
    # PROTECTED: authenticated callers only (no public actions).
    #
    # LayoutSetting rows are global presets (no Entity/Branch field; the
    # layout of an Entity/EntityType/User points at one). Every session
    # reads the catalogue (MainLayout), so reading needs only
    # authentication; changing a preset changes it for every tenant, so
    # writes need the permission (ActionPermissionMixin, fail closed).
    membership_actions = ("list", "retrieve")
    action_permissions = {
        "create": "add_layoutsetting",
        "update": "change_layoutsetting",
        "partial_update": "change_layoutsetting",
        "destroy": "delete_layoutsetting",
    }

    filter_backends = (filters.SearchFilter,)
    serializer_class = LayoutSettingSerializer
    queryset = LayoutSetting.objects.all()

    def get_queryset(self):
        return self.queryset.filter()