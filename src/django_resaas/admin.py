# =========================
# Django
# =========================
from django_resaas.core.base.admin import BaseAdmin, all_fields
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from django.contrib.contenttypes.admin import GenericTabularInline
from .models import Document


class DocumentInline(GenericTabularInline):
    model = Document
    extra = 1


# =========================
# ds – models
# =========================
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
from django_resaas.models.model_extra import ModelExtra
from django_resaas.models.document import DocumentType, Document


# =========================
# User model
# =========================
User = get_user_model()

admin.site.site_title = 'Django Rest SaaS'
admin.site.index_title = 'Django Rest SaaS'



@admin.register(DocumentType)
class DocumentTypeAdmin(BaseAdmin):
    list_display = ('name', 'detalhes')
    
@admin.register(Document)
class DocumentAdmin(BaseAdmin):
    list_display = ('tipo', 'numero', 'data_emissao', 'data_validade')
    list_filter = ('tipo',)

@admin.register(Translation)
class TranslationAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)

from django_resaas.models.theme import Theme
@admin.register(Theme)
class ThemeAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)

from django_resaas.models.layout_setting import LayoutSetting
@admin.register(LayoutSetting)
class LayoutSettingAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)

from django_resaas.models.cors_allowed_origin import CorsAllowedOrigin
@admin.register(CorsAllowedOrigin)
class CorsAllowedOriginAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


from django_resaas.models.theme import Typography
@admin.register(Typography)
class TypographyAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)

from django_resaas.models.layout_setting import AnimationSetting
@admin.register(AnimationSetting)
class AnimationSettingAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


@admin.register(EntityGroup)
class EntityGroupAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


@admin.register(File)
class FileAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)

@admin.register(EntityTypeModel)
class EntityTypeModelAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)

@admin.register(EntityModel)
class EntityModelAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)
    search_fields = ['id', 'name']

from .models import Person

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    inlines = [DocumentInline]


@admin.register(FrontEnd)
class FrontEndAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(Language)
class LanguageAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)
    search_fields = ['id', 'name']


@admin.register(EntityType)
class EntityTypeAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'name')
    search_fields = ['name']


@admin.register(User)
class UserAdmin( BaseAdmin):
    
    def get_list_display(self, request):
        exclude = ['password']
        fields = all_fields(self.model)
        return [f for f in fields if f not in exclude]

    list_display_links = ('id', 'username', 'email')
    search_fields = ['username', 'mobile', 'email']

    readonly_fields = ('password',)


@admin.register(UserLogin)
class UserLoginAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)
    search_fields = ['local_name', 'dispositivo', 'user']


@admin.register(Entity)
class EntityAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'name')
    search_fields = ['name']

    def admin_list(self, obj):
        return ', '.join(u.username for u in obj.admins.all())
    admin_list.short_description = 'admins'


@admin.register(EntityUser)
class EntityUserAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'user')
    search_fields = ['user']


@admin.register(Branch)
class BranchAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'name')
    search_fields = ['name']


@admin.register(BranchGroup)
class BranchGroupAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'branch', 'group')
    search_fields = ['branch', 'group']


@admin.register(BranchUser)
class BranchUserAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'branch', 'user')
    search_fields = ['branch', 'user']


@admin.register(BranchUserGroup)
class BranchUserGroupAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'branch', 'user', 'group')
    search_fields = ['branch', 'user', 'group']


@admin.register(EntityApp)
class EntityAppAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'entity', 'app')
    search_fields = ['entity', 'app']


@admin.register(EntityTypeApp)
class EntityTypeAppAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'entity_type', 'app')
    search_fields = ['entity_type', 'app']


@admin.register(EntityTypeGroup)
class EntityTypeGroupAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'entity_type', 'group')
    search_fields = ['entity_type', 'group']

@admin.register(ModelExtra)
class ModelExtraAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'model')
    search_fields = [ 'icon', 'model', 'url', 'datails', 'permission']

@admin.register(App)
class AppAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)




