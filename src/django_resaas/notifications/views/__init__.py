# Importing every view module here runs their @register_view decorators
# (VIEW_REGISTRY population), the same import-side-effect pattern
# hr/views/__init__.py uses. django_resaas/urls.py imports this package
# before calling build_saas_urls().

from .rule import NotificationRuleAPIView
from .template import NotificationTemplateAPIView
from .preference import NotificationPreferenceAPIView
from .settings import NotificationSettingsAPIView
from .outbox import NotificationOutboxAPIView
from .delivery_attempt import NotificationDeliveryAttemptAPIView
from .catalog import NotificationCatalogAPIView
from .dashboard import NotificationsDashboardAPIView

__all__ = [
    "NotificationRuleAPIView",
    "NotificationTemplateAPIView",
    "NotificationPreferenceAPIView",
    "NotificationSettingsAPIView",
    "NotificationOutboxAPIView",
    "NotificationDeliveryAttemptAPIView",
    "NotificationCatalogAPIView",
    "NotificationsDashboardAPIView",
]
