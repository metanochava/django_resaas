
from django_resaas.models.tipo_entidade import TipoEntidade
from django_resaas.models.entidade import Entidade
from django_resaas.models.tipo_entidade_group import TipoEntidadeGroup
from django_resaas.models.entidade_group import EntidadeGroup

def group_creator(groups = []):
    from django.contrib.auth.models import Group 
    tipo_entidade, _ = TipoEntidade.objects.get_or_create( nome="SaaS", defaults={"estado": 1} )
    entidade, _ = Entidade.objects.get_or_create( nome="Mytech", defaults={"estado": 1} )
    for g in groups:
        grupo, _ = Group.objects.get_or_create(name=g )
        TipoEntidadeGroup.objects.get_or_create( tipo_entidade=tipo_entidade,  group=grupo )
        EntidadeGroup.objects.get_or_create( entidade=entidade,  group=grupo )