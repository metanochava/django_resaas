# =========================
# Django Core
# =========================
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.admin import GenericTabularInline

# =========================
# Base
# =========================
from django_resaas.core.base.admin import BaseAdmin, all_fields

# =========================
# Local Models
# =========================
from .models import Document, Person
from django_resaas.models.document import DocumentType

from django_resaas.models.translation import Translation
from django_resaas.models.language import Language
from django_resaas.models.entity import Entity
from django_resaas.models.entity_user import EntityUser
from django_resaas.models.entity_app import EntityApp
from django_resaas.models.entity_group import EntityGroup

from django_resaas.models.branch import Branch
from django_resaas.models.branch_user import BranchUser
from django_resaas.models.branch_user_group import BranchUserGroup
from django_resaas.models.branch_group import BranchGroup

from django_resaas.models.entity_type import EntityType
from django_resaas.models.entity_type_app import EntityTypeApp
from django_resaas.models.entity_type_model import EntityTypeModel
from django_resaas.models.entity_type_group import EntityTypeGroup
from django_resaas.models.entity_model import EntityModel

from django_resaas.models.file import File
from django_resaas.models.user_login import UserLogin
from django_resaas.models.app import App
from django_resaas.models.front_end import FrontEnd
from django_resaas.models.model_extra_action import ModelExtraAction

from django_resaas.models.theme import Theme, Typography
from django_resaas.models.layout_setting import LayoutSetting, AnimationSetting
from django_resaas.models.cors_allowed_origin import CorsAllowedOrigin

# 🔥 IMPORT CORRETO DO TEU GROUP
from django_resaas.models.group import Group as ResaasGroup


# =========================
# Admin Config
# =========================
User = get_user_model()

admin.site.site_title = 'Django Rest SaaS'
admin.site.index_title = 'Django Rest SaaS'


# =========================
# 🔥 REMOVE GROUP PADRÃO DO DJANGO
# =========================



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
    list_display = ('name', 'detalhes')


@admin.register(Document)
class DocumentAdmin(BaseAdmin):
    list_display = ('tipo', 'numero', 'data_emissao', 'data_validade')
    list_filter = ('tipo',)


# =========================
# 🔥 TEU GROUP (UUID)
# =========================
@admin.register(ResaasGroup)
class GroupAdmin(BaseAdmin):
    filter_horizontal = ('permissions',)

    def get_list_display(self, request):
        return all_fields(self.model)

    list_display_links = ('id',)


# =========================
# Core Models
# =========================
@admin.register(Translation)
class TranslationAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


@admin.register(Theme)
class ThemeAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


@admin.register(LayoutSetting)
class LayoutSettingAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


@admin.register(CorsAllowedOrigin)
class CorsAllowedOriginAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


@admin.register(Typography)
class TypographyAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


@admin.register(AnimationSetting)
class AnimationSettingAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


# =========================
# Entity & Relations
# =========================
@admin.register(EntityGroup)
class EntityGroupAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(Entity)
class EntityAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'name')
    search_fields = ['name']


@admin.register(EntityUser)
class EntityUserAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(EntityApp)
class EntityAppAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(EntityType)
class EntityTypeAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'name')


@admin.register(EntityTypeApp)
class EntityTypeAppAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(EntityTypeModel)
class EntityTypeModelAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(EntityTypeGroup)
class EntityTypeGroupAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(EntityModel)
class EntityModelAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


# =========================
# Branch
# =========================
@admin.register(Branch)
class BranchAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'name')


@admin.register(BranchGroup)
class BranchGroupAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(BranchUser)
class BranchUserAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(BranchUserGroup)
class BranchUserGroupAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


# =========================
# Others
# =========================
@admin.register(File)
class FileAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(UserLogin)
class UserLoginAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(FrontEnd)
class FrontEndAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(Language)
class LanguageAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(ModelExtraAction)
class ModelExtraActionAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(App)
class AppAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


# =========================
# User
# =========================
@admin.register(User)
class UserAdmin(BaseAdmin):

    def get_list_display(self, request):
        exclude = ['password']
        return [f for f in all_fields(self.model) if f not in exclude]

    list_display_links = ('id', 'username', 'email')
    search_fields = ['username', 'mobile', 'email']
    readonly_fields = ('password',)


# =========================
# Permission
# =========================
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    search_fields = ['id', 'name']


# =========================
# Person
# =========================
@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    inlines = [DocumentInline]