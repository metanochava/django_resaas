# =========================
# Django Core
# =========================
from django.contrib import admin
from django.contrib.auth import get_user_model

# Força a importação de django.contrib.auth.admin AGORA, para garantir
# que o seu admin.site.register(Group, GroupAdmin) já correu antes do
# unregister() abaixo.
import django.contrib.auth.admin  # noqa: F401

from django.contrib.auth.models import Group as DjangoAuthGroup
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.admin import GenericTabularInline


# =========================
# Remove Django Group
# =========================
if admin.site.is_registered(DjangoAuthGroup):
    admin.site.unregister(DjangoAuthGroup)


# =========================
# Base
# =========================
from django_resaas.saas.core.base.admin import (
    BaseAdmin,
    all_fields,
)


# =========================
# Local Models
# =========================
from .models import (
    Document,
    Person,
    PersonContact,
)

from django_resaas.saas.models.document import DocumentType

from django_resaas.saas.models.translation import Translation
from django_resaas.saas.models.language import Language

from django_resaas.saas.models.entity import Entity
from django_resaas.saas.models.entity_user import EntityUser
from django_resaas.saas.models.entity_app import EntityApp
from django_resaas.saas.models.entity_group import EntityGroup

from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.branch_user import BranchUser
from django_resaas.saas.models.branch_user_group import BranchUserGroup
from django_resaas.saas.models.branch_group import BranchGroup

from django_resaas.saas.models.entity_type import EntityType
from django_resaas.saas.models.entity_type_app import EntityTypeApp
from django_resaas.saas.models.entity_type_model import EntityTypeModel
from django_resaas.saas.models.entity_type_group import EntityTypeGroup
from django_resaas.saas.models.entity_model import EntityModel

from django_resaas.saas.models.file import File
from django_resaas.saas.models.user_login import UserLogin
from django_resaas.saas.models.app import App
from django_resaas.saas.models.front_end import FrontEnd
from django_resaas.saas.models.model_extra_action import ModelExtraAction

from django_resaas.saas.models.theme import Theme
from django_resaas.saas.models.theme_surface import ThemeSurface
from django_resaas.saas.models.typography import Typography
from django_resaas.saas.models.layout_setting import LayoutSetting
from django_resaas.saas.models.animation_setting import AnimationSetting
from django_resaas.saas.models.cors_allowed_origin import CorsAllowedOrigin

# RESAAS Group
from django_resaas.saas.models.group import Group as ResaasGroup

# Security
from django_resaas.saas.models.audit_log import AuditLog
from django_resaas.saas.models.user_temporary_password import (
    UserTemporaryPassword,
)


# =========================
# Admin Config
# =========================
User = get_user_model()

admin.site.site_title = 'Django Rest SaaS'
admin.site.index_title = 'Django Rest SaaS'


# =========================
# Inlines
# =========================
class DocumentInline(GenericTabularInline):
    model = Document
    extra = 1


# =========================
# Document
# =========================
@admin.register(DocumentType)
class DocumentTypeAdmin(BaseAdmin):
    list_display = (
        'name',
        'detalhes',
    )

    search_fields = ("__all__",)


@admin.register(Document)
class DocumentAdmin(BaseAdmin):
    list_display = (
        'tipo',
        'numero',
        'data_emissao',
        'data_validade',
    )

    list_filter = ('tipo',)

    search_fields = ("__all__",)


# =========================
# RESAAS Group
# =========================
@admin.register(ResaasGroup)
class GroupAdmin(BaseAdmin):

    filter_horizontal = (
        'permissions',
    )

    def get_list_display(self, request):
        return all_fields(self.model)

    list_display_links = ('id',)

    search_fields = ("__all__",)


# =========================
# Core Models
# =========================
@admin.register(Translation)
class TranslationAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    list_display_links = ('id',)

    search_fields = ("__all__",)


@admin.register(Theme)
class ThemeAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    list_display_links = ('id',)

    search_fields = ("__all__",)


@admin.register(ThemeSurface)
class ThemeSurfaceAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    list_display_links = ('id',)

    search_fields = ("__all__",)


@admin.register(LayoutSetting)
class LayoutSettingAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    list_display_links = ('id',)

    search_fields = ("__all__",)


@admin.register(CorsAllowedOrigin)
class CorsAllowedOriginAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    list_display_links = ('id',)

    search_fields = ("__all__",)


@admin.register(Typography)
class TypographyAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    list_display_links = ('id',)

    search_fields = ("__all__",)


@admin.register(AnimationSetting)
class AnimationSettingAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    list_display_links = ('id',)

    search_fields = ("__all__",)


# =========================
# Entity & Relations
# =========================
@admin.register(EntityGroup)
class EntityGroupAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


@admin.register(Entity)
class EntityAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    list_display_links = (
        'id',
        'name',
    )

    search_fields = [
        'name',
    ]


@admin.register(EntityUser)
class EntityUserAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)


@admin.register(EntityApp)
class EntityAppAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


@admin.register(EntityType)
class EntityTypeAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    list_display_links = (
        'id',
        'name',
    )

    search_fields = ("__all__",)


@admin.register(EntityTypeApp)
class EntityTypeAppAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


@admin.register(EntityTypeModel)
class EntityTypeModelAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


@admin.register(EntityTypeGroup)
class EntityTypeGroupAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


@admin.register(EntityModel)
class EntityModelAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


# =========================
# Branch
# =========================
@admin.register(Branch)
class BranchAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    list_display_links = (
        'id',
        'name',
    )

    search_fields = ("__all__",)


@admin.register(BranchGroup)
class BranchGroupAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


@admin.register(BranchUser)
class BranchUserAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


@admin.register(BranchUserGroup)
class BranchUserGroupAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


# =========================
# Others
# =========================
@admin.register(File)
class FileAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


@admin.register(UserLogin)
class UserLoginAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


@admin.register(FrontEnd)
class FrontEndAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


@admin.register(Language)
class LanguageAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


@admin.register(ModelExtraAction)
class ModelExtraActionAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


@admin.register(App)
class AppAdmin(BaseAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)


# =========================================================
# Security
# =========================================================


# =========================
# Audit Log
# =========================
@admin.register(AuditLog)
class AuditLogAdmin(BaseAdmin):
    """
    Audit logs are immutable.

    They may be inspected through Django Admin,
    but must never be created, edited or deleted manually.
    """

    def get_list_display(self, request):
        return all_fields(self.model)

    list_display_links = ('id',)

    readonly_fields = ()

    def get_readonly_fields(self, request, obj=None):
        return all_fields(self.model)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # True allows opening the object detail page.
        # All fields remain readonly.
        return True

    def has_delete_permission(self, request, obj=None):
        return False


# =========================
# Temporary Password
# =========================
@admin.register(UserTemporaryPassword)
class UserTemporaryPasswordAdmin(BaseAdmin):
    """
    Administrative view of temporary-password state.

    The encrypted value is never displayed in the list and cannot
    be edited through Django Admin.

    Temporary passwords must be created/replaced/revealed through
    the RESAAS temporary-password service.
    """

    list_display = (
        'id',
        'user',
        'entity',
        'expires_at',
        'created_by',
        'created_at',
        'has_encrypted_password',
    )

    list_display_links = (
        'id',
        'user',
    )

    list_filter = (
        'expires_at',
        'created_at',
        'entity',
    )

    search_fields = (
        'user__username',
        'user__email',
        'entity__name',
        'created_by__username',
        'created_by__email',
    )

    readonly_fields = (
        'id',
        'user',
        'entity',
        'encrypted',
        'expires_at',
        'created_by',
        'created_at',
    )

    @admin.display(
        boolean=True,
        description='Encrypted password',
    )
    def has_encrypted_password(self, obj):
        return bool(obj.encrypted)

    def has_add_permission(self, request):
        # Creation must go through temporary_password_service.issue()
        return False

    def has_change_permission(self, request, obj=None):
        # Allow opening detail page.
        # readonly_fields prevents modification.
        return True

    def has_delete_permission(self, request, obj=None):
        # Do not bypass the temporary-password lifecycle.
        return False


# =========================
# User
# =========================
@admin.register(User)
class UserAdmin(BaseAdmin):

    def get_list_display(self, request):
        exclude = [
            'password',
        ]

        return [
            field
            for field in all_fields(self.model)
            if field not in exclude
        ]

    list_display_links = (
        'id',
        'username',
        'email',
    )

    search_fields = [
        'username',
        'mobile',
        'email',
    ]

    readonly_fields = (
        'password',
    )


# =========================
# Permission
# =========================
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = [
        'id',
        'name',
    ]


# =========================
# Person
# =========================
@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)

    inlines = [
        DocumentInline,
    ]


@admin.register(PersonContact)
class PersonContactAdmin(admin.ModelAdmin):

    def get_list_display(self, request):
        return all_fields(self.model)

    search_fields = ("__all__",)