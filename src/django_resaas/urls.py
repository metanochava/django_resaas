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

from django_resaas.data.bootstrap.views.bootstrap import TenantAPIView


# ─────────────────────────────
# User / Auth views
# ─────────────────────────────
from django_resaas.data.user.views.login import LoginAPIView
from django_resaas.data.user.views.logins import LoginsAPIView
from django_resaas.data.user.views.logout import LogoutAPIView
from django_resaas.data.user.views.me import MeAPIView
from django_resaas.data.user.views.verify_email import VerifyEmail
from django_resaas.data.user.views.change_password_email import ChangePasswordEmailAPIView
from django_resaas.data.user.views.change_password_mobile import ChangePasswordMobileAPIView
from django_resaas.data.user.views.request_password_reset_email import RequestPasswordResetEmailAPIView
from django_resaas.data.user.views.password_token_check import PasswordTokenCheckAPIView
from django_resaas.data.user.views.set_new_password import SetNewPasswordAPIView
from django_resaas.data.user.views.mail import MailAPIView

# ─────────────────────────────
# Data / API views
# ─────────────────────────────
from django_resaas.data.entidade.views.entidade import EntidadeAPIView
from django_resaas.data.tipo_entidade.views.tipo_entidade import TipoEntidadeAPIView
from django_resaas.data.group.views.grupo import GrupoAPIView
from django_resaas.data.sucursal.views.sucursal import SucursalAPIView

from django_resaas.data.traducao.views.traducao import TraducaoAPIView
from django_resaas.data.idioma.views.idioma import IdiomaAPIView
from django_resaas.data.ficheiro.views.ficheiro import FicheiroAPIView
from django_resaas.data.permission.views.permission import PermissionAPIView
from django_resaas.data.modelo.views.modelo import ModeloAPIView
from django_resaas.data.user.views.user import UserAPIView
from django_resaas.data.theme.views.theme import ThemeAPIView
from django_resaas.data.layout_setting.views.layout_setting import LayoutSettingAPIView
from django_resaas.management.apicommands.view.scaffold import ScaffoldAPIView
from django_resaas.management.apicommands.view.modulo_schema import ModuloSchemaAPIView, RelationsAPIView

from django_resaas.data.pdf.views.invoice import invoice_pdf

from django_resaas.view import home
from django_resaas.view import deploy_github, deploy_status, deploy_releases, deploy_logs, deploy_rollback
from django_resaas.core.utils.autoload_urls import build_saas_urls




# ─────────────────────────────
# Router
# ─────────────────────────────
routerdjango_resaas = routers.DefaultRouter()
routerauth = routers.DefaultRouter()

routerdjango_resaas.register("ficheiros", FicheiroAPIView, basename="ficheiros")
routerdjango_resaas.register("idiomas", IdiomaAPIView, basename="idiomas")
routerdjango_resaas.register("traducaos", TraducaoAPIView, basename="traducaos")
routerdjango_resaas.register("themes", ThemeAPIView, basename="themes")
routerdjango_resaas.register("layoutsettings", LayoutSettingAPIView, basename="layoutsettings")

routerdjango_resaas.register("tipoentidades", TipoEntidadeAPIView, basename="tipo_entidades")
routerdjango_resaas.register("entidades", EntidadeAPIView, basename="entidades")
routerdjango_resaas.register("sucursals", SucursalAPIView, basename="sucursais")
routerdjango_resaas.register("users", UserAPIView, basename="users")
routerauth.register("groups", GrupoAPIView, basename="groups")
routerauth.register("permissions", PermissionAPIView, basename="permissions")
routerdjango_resaas.register("modelos", ModeloAPIView, basename="modelos")
routerdjango_resaas.register("modulos", ModuloSchemaAPIView, basename="modulos")
routerdjango_resaas.register("scaffolds", ScaffoldAPIView, basename="scaffolds")



urlpatterns = [

    path('', home, name='home'),

    path("deploy/github/", deploy_github),
    path("deploy/status/", deploy_status),
    path("deploy/releases/", deploy_releases),
    path("deploy/logs/", deploy_logs),
    path("deploy/rollback/", deploy_rollback),
    

    path("django_resaas/", include(routerdjango_resaas.urls)),
    path("auth/", include(routerauth.urls)),
    path("django_resaas/relations/", RelationsAPIView.as_view()),


    path("setup/", TenantAPIView.as_view(), name="setup"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("me/", MeAPIView.as_view(), name="me"),

    path("email/verify/", VerifyEmail.as_view(), name="email_verify"),
    path("refresh_token/", TokenRefreshView.as_view(), name="token_refresh"),

    path("logins/", LoginsAPIView.as_view(), name="logins"),

    path("password/change/email/", ChangePasswordEmailAPIView.as_view(), name="change_password_email"),
    path("password/change/mobile/", ChangePasswordMobileAPIView.as_view(), name="change_password_mobile"),
    path("password/reset/email/", RequestPasswordResetEmailAPIView.as_view(), name="request_password_reset_email"),
    path("password/reset/<uidb64>/<token>/", PasswordTokenCheckAPIView.as_view(), name="password_reset_confirm"),
    path("password/reset/complete/", SetNewPasswordAPIView.as_view(), name="password_reset_complete"),

    path("mail/", MailAPIView.as_view(), name="mail"),
    path("pdf/invoice/<int:invoice_id>/", invoice_pdf, name="invoice_pdf"),

]




