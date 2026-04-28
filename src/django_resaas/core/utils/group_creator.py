def group_creator(groups=None):
    if groups is None:
        groups = []

    # 🔥 IMPORT LAZY
    from django.contrib.auth.models import Group
    from django_resaas.models.tipo_entidade import TipoEntidade
    from django_resaas.models.entidade import Entidade
    from django_resaas.models.tipo_entidade_group import TipoEntidadeGroup
    from django_resaas.models.entidade_group import EntidadeGroup

    # ------------------------------------------------------
    # 🔥 GARANTE TipoEntidade BASE
    # ------------------------------------------------------
    tipo_entidade, _ = TipoEntidade.objects.get_or_create(
        nome="SaaS",
        estado= 1
    )

    # ------------------------------------------------------
    # 🔥 GARANTE Entidade COM tipo_entidade
    # ------------------------------------------------------
    entidade, _ = Entidade.objects.get_or_create(
        nome="Mytech",
        tipo_entidade=tipo_entidade,  # 🔥 FIX CRÍTICO
        estado= 1
    )

    # ------------------------------------------------------
    # 🔥 CRIA GRUPOS
    # ------------------------------------------------------
    for g in groups:
        group, _ = Group.objects.get_or_create(name=g)

        TipoEntidadeGroup.objects.get_or_create(
            tipo_entidade=tipo_entidade,
            group=group,
            defaults={"estado": 1}
        )

        EntidadeGroup.objects.get_or_create(
            entidade=entidade,
            group=group,
            defaults={"estado": 1}
        )