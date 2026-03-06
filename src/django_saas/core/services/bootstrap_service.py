from django.contrib.auth.models import Group
from django.db import transaction

from django_saas.models.tipo_entidade import TipoEntidade
from django_saas.models.entidade import Entidade
from django_saas.models.sucursal import Sucursal
from django_saas.models.entidade_user import EntidadeUser
from django_saas.models.sucursal_user import SucursalUser
from django_saas.models.sucursal_user_group import SucursalUserGroup
from django_saas.models.entidade_group import EntidadeGroup
from django_saas.models.sucursal_group import SucursalGroup
from django_saas.models.modulo import Modulo
from django_saas.models.tipo_entidade_modulo import TipoEntidadeModulo
from django_saas.models.entidade_modulo import EntidadeModulo




class BootstrapService:

    @classmethod
    @transaction.atomic
    def run(cls, tipo_entidade, entidade, sucursal, user, grupo, stdout=None, style=None):

        tipo = cls.create_tipo_entidade(tipo_entidade, stdout, style)
        entidade = cls.create_entidade(tipo, entidade, user, stdout, style)
        sucursal = cls.create_sucursal(entidade, sucursal, user, stdout, style)
        grupo = cls.create_grupo(user, entidade, sucursal, stdout, style)

        return {
            "tipo_entidade": tipo,
            "entidade": entidade,
            "sucursal": sucursal,
            "grupo": grupo,
        }

    # ------------------------
    # TipoEntidade
    # ------------------------
    @staticmethod
    def create_tipo_entidade(nome, stdout=None, style=None):
        tipo, _ = TipoEntidade.objects.get_or_create(
            nome=nome,
            defaults={"estado": 1}
        )

        if stdout and style:
            stdout.write(style.SUCCESS(f"✔ {'TipoEntidade:':20} {tipo.nome}"))

        return tipo

    # ------------------------
    # Entidade + EntidadeUser
    # ------------------------
    @staticmethod
    def create_entidade(tipo_entidade, nome, user, stdout=None, style=None):
        entidade, _ = Entidade.objects.get_or_create(
            nome=nome,
            tipo_entidade=tipo_entidade
        )

        entidade.admins.add(user)

        EntidadeUser.objects.get_or_create(
            user=user,
            entidade=entidade
        )

        for name in ['django_saas', 'rh']:
            modulo, _ = Modulo.objects.get_or_create(
                nome=name,
                defaults={"estado": 1}
            )

            tipo_entidade_modulo, _ = TipoEntidadeModulo.objects.get_or_create(
                modulo=modulo,
                tipo_entidade=tipo_entidade,
                defaults={"estado": 1}
            )

            entidade_modulo, _ = EntidadeModulo.objects.get_or_create(
                modulo=modulo,
                entidade=entidade,
                defaults={"estado": 1}
            )

            stdout.write(style.WARNING(f"✔ {'Modulo:':20} {modulo.nome}"))

        if stdout and style:
            stdout.write(style.SUCCESS(f"✔ {'Entidade:':20} {entidade.nome}"))

        return entidade

    # ------------------------
    # Sucursal + SucursalUser
    # ------------------------
    @staticmethod
    def create_sucursal(entidade, nome, user, stdout=None, style=None):
        sucursal, _ = Sucursal.objects.get_or_create(
            nome=nome,
            entidade=entidade
        )

        SucursalUser.objects.get_or_create(
            user=user,
            sucursal=sucursal
        )

        if stdout and style:
            stdout.write(style.SUCCESS(f"✔ {'Sucursal:':20} {sucursal.nome}"))

        return sucursal

    # ------------------------
    # Grupo + SucursalUserGroup
    # ------------------------
    @staticmethod
    def create_grupo(user,entidade, sucursal, stdout=None, style=None):
        grupo, _ = Group.objects.get_or_create(name="Admin")

        # ligar grupo à sucursal
        SucursalGroup.objects.get_or_create(
            sucursal=sucursal,
            group=grupo
        )

        # ligar grupo ao tenant (entidade)
        EntidadeGroup.objects.get_or_create(
            entidade=entidade,
            group=grupo
        )

        user.groups.add(grupo)

        

        SucursalUserGroup.objects.get_or_create(
            user=user,
            sucursal=sucursal,
            group=grupo
        )

        if stdout and style:
            stdout.write(style.SUCCESS(f"✔ {'Grupo:':20} {grupo.name}"))
            stdout.write(style.SUCCESS(f"✔ {'EntidadeGrupo':20} OK"))
            stdout.write(style.SUCCESS(f"✔ {'SucursalGrupo':20} OK"))


        return grupo
