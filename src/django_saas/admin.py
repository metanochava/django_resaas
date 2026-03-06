# =========================
# Django
# =========================
from django_saas.core.base.admin import BaseAdmin
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from django.contrib.contenttypes.admin import GenericTabularInline
from .models import Documento


class DocumentoInline(GenericTabularInline):
    model = Documento
    extra = 1


# =========================
# ds – models
# =========================
from django_saas.models.traducao import Traducao
from django_saas.models.idioma import Idioma
from django_saas.models.entidade import Entidade
from django_saas.models.entidade_user import EntidadeUser
from django_saas.models.entidade_modulo import EntidadeModulo
from django_saas.models.entidade_group import EntidadeGroup

from django_saas.models.sucursal import Sucursal
from django_saas.models.sucursal_user import SucursalUser
from django_saas.models.sucursal_user_group import SucursalUserGroup
from django_saas.models.sucursal_group import SucursalGroup

from django_saas.models.tipo_entidade import TipoEntidade
from django_saas.models.tipo_entidade_modulo import TipoEntidadeModulo
from django_saas.models.tipo_entidade_modelo import TipoEntidadeModelo
from django_saas.models.entidade_modelo import EntidadeModelo
from django_saas.models.ficheiro import Ficheiro
from django_saas.models.user_login import UserLogin
from django_saas.models.modulo import Modulo
from django_saas.models.front_end import FrontEnd
from django_saas.models.modelo_extra import ModeloExtra
from django_saas.models.documento import TipoDocumento, Documento


# =========================
# User model
# =========================
User = get_user_model()

admin.site.site_title = 'Auth'
admin.site.index_title = 'Mytech Auth Rest'


def all_fields(model):
    return [field.name for field in model._meta.fields]

@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'detalhes')
    
@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'numero', 'data_emissao', 'data_validade')
    list_filter = ('tipo',)

@admin.register(Traducao)
class TraducaoAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


@admin.register(EntidadeGroup)
class EntidadeGroupAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


@admin.register(Ficheiro)
class FicheiroAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)

@admin.register(TipoEntidadeModelo)
class TipoEntidadeModeloAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)

@admin.register(EntidadeModelo)
class EntidadeModeloAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)
    search_fields = ['id', 'name']

from .models import Pessoa

@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    inlines = [DocumentoInline]


@admin.register(FrontEnd)
class FrontEndAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


@admin.register(Idioma)
class IdiomaAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)
    search_fields = ['id', 'nome']


@admin.register(TipoEntidade)
class TipoEntidadeAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'nome')
    search_fields = ['nome']


from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
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
    search_fields = ['local_nome', 'dispositivo', 'user']


@admin.register(Entidade)
class EntidadeAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'nome')
    search_fields = ['nome']

    def admin_list(self, obj):
        return ', '.join(u.username for u in obj.admins.all())
    admin_list.short_description = 'admins'


@admin.register(EntidadeUser)
class EntidadeUserAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'user')
    search_fields = ['user']


@admin.register(Sucursal)
class SucursalAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'nome')
    search_fields = ['nome']


@admin.register(SucursalGroup)
class SucursalGroupAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'sucursal', 'group')
    search_fields = ['sucursal', 'group']


@admin.register(SucursalUser)
class SucursalUserAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'sucursal', 'user')
    search_fields = ['sucursal', 'user']


@admin.register(SucursalUserGroup)
class SucursalUserGroupAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'sucursal', 'user', 'group')
    search_fields = ['sucursal', 'user', 'group']


@admin.register(EntidadeModulo)
class EntidadeModuloAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'entidade', 'modulo')
    search_fields = ['entidade', 'modulo']


@admin.register(TipoEntidadeModulo)
class TipoEntidadeModuloAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'tipo_entidade', 'modulo')
    search_fields = ['tipo_entidade', 'modulo']

@admin.register(ModeloExtra)
class ModeloExtraAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id', 'modelo')
    search_fields = [ 'icon', 'modelo', 'url', 'datails', 'permission']

@admin.register(Modulo)
class ModuloAdmin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)


