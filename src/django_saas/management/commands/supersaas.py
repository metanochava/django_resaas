from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from getpass import getpass
from django_saas.models.tipo_entidade import TipoEntidade
from django_saas.models.entidade import Entidade
from django_saas.models.sucursal import Sucursal
from django_saas.models.entidade_user import EntidadeUser
from django_saas.models.sucursal_user import SucursalUser
from django_saas.models.sucursal_user_group import SucursalUserGroup
from django.contrib.auth.models import Group
from django_saas.core.services.frontend_service import FrontEndService
from django_saas.core.services.idioma_service import IdiomaService
from django_saas.models.modulo import Modulo
from django_saas.models.tipo_entidade_modulo import TipoEntidadeModulo
from django_saas.models.entidade_modulo import EntidadeModulo

from django_saas.models.tipo_entidade_group import TipoEntidadeGroup
from django_saas.models.entidade_group import EntidadeGroup
from django_saas.models.sucursal_group import SucursalGroup

User = get_user_model()


class Command(BaseCommand):
    help = "Cria um superuser estático se não existir"

    def handle(self, *args, **options):
        email = "root@co.mz"
        username = "root"

        FrontEndService.load_defaults( stdout=self.stdout,  style=self.style  )
        IdiomaService.load_defaults( stdout=self.stdout, style=self.style )

        user = User.objects.filter(email=email).first()
        exist = False
        if user :
            exist = True
            self.stdout.write(
                self.style.WARNING("\nSuperuser já existe")
            )
            self.stdout.write(
                self.style.HTTP_INFO("  Username: \t") + self.style.SUCCESS(user.username)
            )
            self.stdout.write(
                self.style.HTTP_INFO("  Email: \t") + self.style.SUCCESS(user.email) 
            )

            self.stdout.write(
                self.style.WARNING("\n")
            )




        # 🔐 pedir password pelo teclado (sem mostrar)
        while True:
            password = getpass("Password do superuser: ")
            password_confirm = getpass("Confirme a password: ")

            if not password:
                self.stdout.write(
                    self.style.ERROR("A password não pode estar vazia")
                )
                continue

            if password != password_confirm:
                self.stdout.write(
                    self.style.ERROR("As passwords não coincidem")
                )
                continue

            break
        if not exist:
            user = User.objects.create_superuser(
                email=email,
                username=username,
                password=password,
            )

            user.set_password(password)
            user.is_verified_email= True
            user.save()


        data = {
            "tipo_entidade": "SaaS",
            "entidade": "Mytech",
            "sucursal": "Sede",
            "grupo": ["Guest", "SuperAdmin", "Admin"],
        }

        # ------------------------
        # 1. TipoEntidade
        # ------------------------
        tipo_entidade, _ = TipoEntidade.objects.get_or_create(
            nome=data["tipo_entidade"],
            defaults={"estado": 1}
        )

        # ------------------------
        # 2. Entidade
        # ------------------------
        entidade, created_entidade = Entidade.objects.get_or_create(
            nome=data["entidade"],
            tipo_entidade=tipo_entidade
        )

        # ManyToMany → DEPOIS
        entidade.admins.add(user)

        EntidadeUser.objects.get_or_create(
            user=user,
            entidade=entidade
        )

        # ------------------------
        # 3. Sucursal
        # ------------------------
        sucursal, _ = Sucursal.objects.get_or_create(
            nome=data["sucursal"],
            entidade=entidade
        )

        SucursalUser.objects.get_or_create(
            user=user,
            sucursal=sucursal
        )

        # ------------------------
        # 4. Grupo
        # ------------------------
        for g in data["grupo"]:

            grupo, _ = Group.objects.get_or_create(
                name=g
            )

            SucursalUserGroup.objects.get_or_create(
                user=user,
                sucursal=sucursal,
                group=grupo
            )

            user.groups.add(grupo)

            TipoEntidadeGroup.objects.get_or_create(
                tipo_entidade=tipo_entidade,
                group=grupo
            )

            EntidadeGroup.objects.get_or_create(
                entidade=entidade,
                group=grupo
            )

            SucursalGroup.objects.get_or_create(
                sucursal=sucursal,
                group=grupo
            )

        self.stdout.write(self.style.WARNING(f"\n"))

        for name in ['django_saas',]:
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

            self.stdout.write(self.style.WARNING(f"✔ {'Modulo:':20} {modulo.nome}"))

        self.stdout.write(self.style.HTTP_INFO(f""))
        self.stdout.write(self.style.HTTP_INFO(f""))
        self.stdout.write(self.style.HTTP_INFO(f"{'':10} {'✔ Superuser criado:'}"))
        self.stdout.write(self.style.HTTP_INFO(f""))
        self.stdout.write(self.style.HTTP_INFO(f"{'Email:':20} {user.email}"))
        self.stdout.write(self.style.SUCCESS(f"{'User:':20} {user.username}"))
        self.stdout.write(self.style.HTTP_SUCCESS(f"{'TipoEntidade:':20} {tipo_entidade.nome}"))
        self.stdout.write(self.style.HTTP_NOT_MODIFIED(f"{'Entidade:':20} {entidade.nome}"))
        self.stdout.write(self.style.HTTP_SERVER_ERROR(f"{'Sucursal:':20} {sucursal.nome}"))
        self.stdout.write(self.style.WARNING(f"{'Grupos:':20} {data['grupo']}"))
        self.stdout.write(self.style.ERROR("⚠️  Guarde estas credenciais com segurança"))
        self.stdout.write(self.style.HTTP_INFO(f""))
        self.stdout.write(self.style.HTTP_INFO(f""))



       