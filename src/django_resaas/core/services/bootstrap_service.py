from django_resaas.models.group import Group
from django.db import transaction

from django_resaas.models.entity_type import EntityType
from django_resaas.models.entity import Entity
from django_resaas.models.branch import Branch
from django_resaas.models.entity_user import EntityUser
from django_resaas.models.branch_user import BranchUser
from django_resaas.models.branch_user_group import BranchUserGroup
from django_resaas.models.entity_group import EntityGroup
from django_resaas.models.branch_group import BranchGroup
from django_resaas.models.app import App
from django_resaas.models.entity_type_app import EntityTypeApp
from django_resaas.models.entity_app import EntityApp




class BootstrapService:

    @classmethod
    @transaction.atomic
    def run(cls, entity_type, entity, branch, user, group, stdout=None, style=None):

        tipo = cls.create_entity_type(entity_type, stdout, style)
        entity = cls.create_entity(tipo, entity, user, stdout, style)
        branch = cls.create_branch(entity, branch, user, stdout, style)
        group = cls.create_group(user, entity, branch, group, stdout, style)

        return {
            "entity_type": tipo,
            "entity": entity,
            "branch": branch,
            "group": group,
        }

    # ------------------------
    # EntityType
    # ------------------------
    @staticmethod
    def create_entity_type(name, stdout=None, style=None):
        tipo, _ = EntityType.objects.get_or_create(
            name=name,
            estado = 1
        )

        if stdout and style:
            stdout.write(style.SUCCESS(f"✔ {'EntityType:':20} {tipo.name}"))

        return tipo

    # ------------------------
    # Entity + EntityUser
    # ------------------------
    @staticmethod
    def create_entity(entity_type, name, user, stdout=None, style=None):
        entity, _ = Entity.objects.get_or_create(
            name=name,
            entity_type=entity_type,
            estado = 1
        )

        entity.admins.add(user)

        EntityUser.objects.get_or_create(
            user=user,
            entity=entity,
            estado = 1
        )

        for name in ['rh']:
            app, _ = App.objects.get_or_create(
                name=name,
                estado = 1
            )

            entity_type_app, _ = EntityTypeApp.objects.get_or_create(
                app=app,
                entity_type=entity_type,
                estado = 1
            )

            entity_app, _ = EntityApp.objects.get_or_create(
                app=app,
                entity=entity,
                estado = 1
            )

            stdout.write(style.WARNING(f"✔ {'App:':20} {app.name}"))

        if stdout and style:
            stdout.write(style.SUCCESS(f"✔ {'Entity:':20} {entity.name}"))

        return entity

    # ------------------------
    # Branch + BranchUser
    # ------------------------
    @staticmethod
    def create_branch(entity, name, user, stdout=None, style=None):
        branch, _ = Branch.objects.get_or_create(
            name=name,
            entity=entity
        )

        BranchUser.objects.get_or_create(
            user=user,
            branch=branch
        )

        if stdout and style:
            stdout.write(style.SUCCESS(f"✔ {'Branch:':20} {branch.name}"))

        return branch

    # ------------------------
    # Group + BranchUserGroup
    # ------------------------
    @staticmethod
    def create_group(user,entity, branch, group, stdout=None, style=None):

        group, _ = Group.objects.get_or_create(name=group)

        # ligar group à branch
        BranchGroup.objects.get_or_create(
            branch=branch,
            group=group,
            estado = 1
        )

        # ligar group ao tenant (entity)
        EntityGroup.objects.get_or_create(
            entity=entity,
            group=group,
            estado = 1
        )

        user.groups.add(group)

        BranchUserGroup.objects.get_or_create(
            user=user,
            branch=branch,
            group=group,
            estado = 1
        )

        group, _ = Group.objects.get_or_create(name="Guest")

        # ligar group à branch
        BranchGroup.objects.get_or_create(
            branch=branch,
            group=group,
            estado = 1
        )

        # ligar group ao tenant (entity)
        EntityGroup.objects.get_or_create(
            entity=entity,
            group=group,
            estado = 1
        )

        user.groups.add(group)

        
        BranchUserGroup.objects.get_or_create(
            user=user,
            branch=branch,
            group=group,
            estado = 1
        )

        if stdout and style:
            stdout.write(style.SUCCESS(f"✔ {'Groups:':20} Guest e Admin"))
            stdout.write(style.SUCCESS(f"✔ {'EntityGroup':20} OK"))
            stdout.write(style.SUCCESS(f"✔ {'BranchGroup':20} OK"))

        return group
