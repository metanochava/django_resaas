from django.core.management.base import BaseCommand
from django_saas.core.services.user_service import UserService
from django_saas.core.services.bootstrap_service import BootstrapService
from django_saas.core.services.idioma_service import IdiomaService
from django_saas.core.services.frontend_service import FrontEndService
from django_saas.core.services.traducao_service import TraducaoService





class Command(BaseCommand):
    help = "Bootstrap inicial do SaaS"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 Bootstrap SaaS \n\n"))

        tipo_entidade = input("Digite seu nome do Tipo de Entidade: ")
        entidade = input("Digite seu nome da Entidade: ")
        sucursal = input("Digite seu nome da Sucursal: ")
        grupo = input("Digite seu nome do Grupo: ")

        user = UserService.get_or_create_superuser(self.stdout, style=self.style)
 
        
        result = BootstrapService.run(tipo_entidade, entidade, sucursal, user, grupo, stdout=self.stdout, style=self.style)
        self.stdout.write(
            self.style.SUCCESS(f"✔ Superuser criado: \t {user.email} \n")
        )
        self.stdout.write(
            self.style.NOTICE(f"👤 Username: \t {user.username} \n")
        )
        IdiomaService.load_defaults( stdout=self.stdout, style=self.style )

        FrontEndService.load_defaults( stdout=self.stdout,  style=self.style  )

        TraducaoService.load_defaults( stdout=self.stdout, style=self.style )

        
        self.stdout.write(self.style.SUCCESS("\n 🛠 ⚙️ Sistema pronto para uso\n"))
