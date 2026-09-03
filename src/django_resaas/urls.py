"""
URL configuration for dev project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import include
from django.urls import path

from rest_framework import routers

from rest_framework_simplejwt.views import TokenRefreshView




# ─────────────────────────────
# User / Auth views
# ─────────────────────────────
from django_resaas.engine.data.user.views.login import LoginAPIView
from django_resaas.engine.data.user.views.logins import LoginsAPIView
from django_resaas.engine.data.user.views.logout import LogoutAPIView
from django_resaas.engine.data.user.views.me import MeAPIView
from django_resaas.engine.data.user.views.verify_email import VerifyEmail
from django_resaas.engine.data.user.views.change_password_email import ChangePasswordEmailAPIView
from django_resaas.engine.data.user.views.change_password_mobile import ChangePasswordMobileAPIView
from django_resaas.engine.data.user.views.request_password_reset_email import RequestPasswordResetEmailAPIView
from django_resaas.engine.data.user.views.password_token_check import PasswordTokenCheckAPIView
from django_resaas.engine.data.user.views.set_new_password import SetNewPasswordAPIView
from django_resaas.engine.data.user.views.mail import MailAPIView
from django_resaas.engine.data.user.views.register import RegisterAPIView
from django_resaas.engine.data.user.views.register_otp import RequestRegisterOTPView

# ─────────────────────────────
# Data / API views
# ─────────────────────────────
from django_resaas.engine.data.entity.views.entity import EntityAPIView
from django_resaas.engine.data.entity.views.site import SiteAPIView
from django_resaas.engine.data.entity_type.views.entity_type import EntityTypeAPIView
from django_resaas.engine.data.group.views.group import GroupAPIView
from django_resaas.engine.data.branch.views.branch import BranchAPIView
from django_resaas.engine.data.branch_user.views.branch_user import BranchUserAPIView
from django_resaas.engine.data.branch_user_group.views.branch_user_group import BranchUserGroupAPIView
from django_resaas.engine.data.document.views.document import DocumentAPIView
from django_resaas.engine.data.document_type.views.document_type import DocumentTypeAPIView



from django_resaas.engine.data.translation.views.translation import TranslationAPIView
from django_resaas.engine.data.language.views.language import LanguageAPIView
from django_resaas.engine.data.file.views.file import FileAPIView
from django_resaas.engine.data.permission.views.permission import PermissionAPIView
from django_resaas.engine.data.model.views.model import ModelAPIView
from django_resaas.engine.data.app.views.app import AppAPIView
from django_resaas.engine.data.user.views.user import UserAPIView
from django_resaas.engine.data.person.views.person import PersonAPIView
from django_resaas.engine.data.theme.views.theme import ThemeAPIView
from django_resaas.engine.data.layout_setting.views.layout_setting import LayoutSettingAPIView
from django_resaas.engine.management.apicommands.view.scaffold import ScaffoldAPIView
from django_resaas.engine.management.apicommands.view.app_schema import AppSchemaAPIView, RelationsAPIView

# Importing this package runs every @register_view in it (VIEW_REGISTRY
# population), exactly like the direct view imports above - must happen
# before build_saas_urls() runs below.
import django_resaas.notifications.views  # noqa: F401


from django_resaas.engine.data.pdf.views.invoice import invoice_pdf

from django_resaas.view import home
from django_resaas.view import deploy_github, deploy_status, deploy_releases, deploy_logs, deploy_rollback
from django_resaas.engine.core.utils.autoload_urls import build_saas_urls

from django_resaas.engine.data.context.views.context import ResaasContextAPIView




# ─────────────────────────────
# Router
# ─────────────────────────────
routerdjango_resaas = routers.DefaultRouter()
routerauth = routers.DefaultRouter()

routerdjango_resaas.register("files", FileAPIView, basename="files")
routerdjango_resaas.register("languages", LanguageAPIView, basename="languages")
routerdjango_resaas.register("translations", TranslationAPIView, basename="translations")
routerdjango_resaas.register("themes", ThemeAPIView, basename="themes")
routerdjango_resaas.register("layoutsettings", LayoutSettingAPIView, basename="layoutsettings")
routerdjango_resaas.register("documenttypes", DocumentTypeAPIView, basename="documenttypes")
routerdjango_resaas.register("documents", DocumentAPIView, basename="documents")


routerdjango_resaas.register("branchusergroups", BranchUserGroupAPIView, basename="branchusergroups")
routerdjango_resaas.register("branchusers", BranchUserAPIView, basename="branchusers")

routerdjango_resaas.register("entitytypes", EntityTypeAPIView, basename="entitytypes")
routerdjango_resaas.register("entitys", EntityAPIView, basename="entitys")
routerdjango_resaas.register("branchs", BranchAPIView, basename="sucursais")
routerdjango_resaas.register("users", UserAPIView, basename="users")
routerdjango_resaas.register("persons", PersonAPIView, basename="persons")


routerauth.register("groups", GroupAPIView, basename="groups")
routerauth.register("permissions", PermissionAPIView, basename="permissions")

routerdjango_resaas.register("models", ModelAPIView, basename="models")
routerdjango_resaas.register("apps", AppAPIView, basename="apps")
routerdjango_resaas.register("resaasapps", AppSchemaAPIView, basename="resaasapps")
routerdjango_resaas.register("scaffolds", ScaffoldAPIView, basename="scaffolds")






urlpatterns = [

    path('', home, name='home'),
    path(  "resaas/context/", ResaasContextAPIView.as_view(), name="resaas_context" ),
    
    path('hr/', include('django_resaas.hr.urls')),

    path("deploy/github/", deploy_github),
    path("deploy/status/", deploy_status),
    path("deploy/releases/", deploy_releases),
    path("deploy/logs/", deploy_logs),
    path("deploy/rollback/", deploy_rollback),
    

    path("django_resaas/", include(routerdjango_resaas.urls)),
    path("auth/", include(routerauth.urls)),
    path("django_resaas/relations/", RelationsAPIView.as_view()),


    path("site/", SiteAPIView.as_view(), name="site"),

    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("me/", MeAPIView.as_view(), name="me"),

    path("email/verify/", VerifyEmail.as_view(), name="email_verify"),
    path("refresh_token/", TokenRefreshView.as_view(), name="token_refresh"),

    path("logins/", LoginsAPIView.as_view(), name="logins"),

    path("register/", RegisterAPIView.as_view(), name="register"),
    path("register/otp/request/", RequestRegisterOTPView.as_view(), name="register_otp_request"),

    path("password/change/email/", ChangePasswordEmailAPIView.as_view(), name="change_password_email"),
    path("password/change/mobile/", ChangePasswordMobileAPIView.as_view(), name="change_password_mobile"),
    path("password/reset/email/", RequestPasswordResetEmailAPIView.as_view(), name="request_password_reset_email"),
    path("password/reset/<uidb64>/<token>/", PasswordTokenCheckAPIView.as_view(), name="password_reset_confirm"),
    path("password/reset/complete/", SetNewPasswordAPIView.as_view(), name="password_reset_complete"),

    path("mail/", MailAPIView.as_view(), name="mail"),
    path("pdf/invoice/<int:invoice_id>/", invoice_pdf, name="invoice_pdf"),

]

# ─────────────────────────────
# Autoloaded resources (VIEW_REGISTRY)
# ─────────────────────────────
# Must run after urlpatterns above (specifically after `include('django_resaas.hr.urls')`)
# has imported every app's views and run their @registerView decorators.
# Any app's views decorated with @registerView (e.g. hr's) only get routed
# here - dev/urls.py already did this, but an app that installs
# django_resaas and includes only this urls.py did not, so its registered
# resources never appeared there.
saas_router, saas_extra_patterns = build_saas_urls()
urlpatterns += saas_router.urls
urlpatterns += saas_extra_patterns




