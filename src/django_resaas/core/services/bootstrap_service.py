from django.contrib.auth.models import Group
from django.db import transaction

from django_resaas.models.tipo_entidade import TipoEntidade
from django_resaas.models.entidade import Entidade
from django_resaas.models.sucursal import Sucursal
from django_resaas.models.entidade_user import EntidadeUser
from django_resaas.models.sucursal_user import SucursalUser
from django_resaas.models.sucursal_user_group import SucursalUserGroup
from django_resaas.models.entidade_group import EntidadeGroup
from django_resaas.models.sucursal_group import SucursalGroup
from django_resaas.models.modulo import Modulo
from django_resaas.models.tipo_entidade_modulo import TipoEntidadeModulo
from django_resaas.models.entidade_modulo import EntidadeModulo




class BootstrapService:

    @classmethod
    @transaction.atomic
    def run(cls, tipo_entidade, entidade, sucursal, user, group, stdout=None, style=None):

        tipo = cls.create_tipo_entidade(tipo_entidade, stdout, style)
        entidade = cls.create_entidade(tipo, entidade, user, stdout, style)
        sucursal = cls.create_sucursal(entidade, sucursal, user, stdout, style)
        group = cls.create_group(user, entidade, sucursal, group, stdout, style)

        return {
            "tipo_entidade": tipo,
            "entidade": entidade,
            "sucursal": sucursal,
            "group": group,
        }

    # ------------------------
    # TipoEntidade
    # ------------------------
    @staticmethod
    def create_tipo_entidade(nome, stdout=None, style=None):
        tipo, _ = TipoEntidade.objects.get_or_create(
            nome=nome,
            estado = 1
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
            tipo_entidade=tipo_entidade,
            estado = 1
        )

        entidade.admins.add(user)

        EntidadeUser.objects.get_or_create(
            user=user,
            entidade=entidade,
            estado = 1
        )

        for name in ['rh']:
            modulo, _ = Modulo.objects.get_or_create(
                nome=name,
                estado = 1
            )

            tipo_entidade_modulo, _ = TipoEntidadeModulo.objects.get_or_create(
                modulo=modulo,
                tipo_entidade=tipo_entidade,
                estado = 1
            )

            entidade_modulo, _ = EntidadeModulo.objects.get_or_create(
                modulo=modulo,
                entidade=entidade,
                estado = 1
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
    # Group + SucursalUserGroup
    # ------------------------
    @staticmethod
    def create_group(user,entidade, sucursal, group, stdout=None, style=None):

        group, _ = Group.objects.get_or_create(name=group)

        # ligar group à sucursal
        SucursalGroup.objects.get_or_create(
            sucursal=sucursal,
            group=group,
            estado = 1
        )

        # ligar group ao tenant (entidade)
        EntidadeGroup.objects.get_or_create(
            entidade=entidade,
            group=group,
            estado = 1
        )

        user.groups.add(group)

        SucursalUserGroup.objects.get_or_create(
            user=user,
            sucursal=sucursal,
            group=group,
            estado = 1
        )

        group, _ = Group.objects.get_or_create(name="Guest")

        # ligar group à sucursal
        SucursalGroup.objects.get_or_create(
            sucursal=sucursal,
            group=group,
            estado = 1
        )

        # ligar group ao tenant (entidade)
        EntidadeGroup.objects.get_or_create(
            entidade=entidade,
            group=group,
            estado = 1
        )

        user.groups.add(group)

        
        SucursalUserGroup.objects.get_or_create(
            user=user,
            sucursal=sucursal,
            group=group,
            estado = 1
        )

        if stdout and style:
            stdout.write(style.SUCCESS(f"✔ {'Groups:':20} Guest e Admin"))
            stdout.write(style.SUCCESS(f"✔ {'EntidadeGroup':20} OK"))
            stdout.write(style.SUCCESS(f"✔ {'SucursalGroup':20} OK"))

        return group
