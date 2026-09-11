"""Perfis (Group templates) de administração da plataforma/tenant -
mesmo mecanismo já usado por saude/sales/inventory/farmacia (ver
`saas/core/utils/group_creator.py`).

Estes 3 perfis são de âmbito de PLATAFORMA/TENANT (Entity/Branch), não
de um módulo de negócio - por isso vivem em `saas` (core SaaS
infrastructure, CLAUDE.md #55/#87.11) e não em `hr` ou em qualquer app
de negócio. `hr` está incluído nos seus próprios codenames
(`view_employee`, `view_department`, ...) porque `django_resaas.hr` é
uma capacidade padrão da própria plataforma (CLAUDE.md #13: "HR is
part of the default SaaS platform"), não um módulo de negócio externo
- `group_creator()` só resolve por `codename`, nunca importa modelos
de `hr`, por isso isto continua a funcionar (com menos permissões
concedidas) em qualquer instalação que não tenha `django_resaas.hr`
instalado.

Não confundir com `GROUPS = ["Guest", "Admin", "Root"]` (mesmo
ficheiro) - esses são grupos de bootstrap/teste sem permissões
próprias, usados por `testutils`/fixtures existentes; não são
renomeados nem alterados aqui.

Distinção de âmbito entre os 3 perfis:

- System Administrator: administra a PLATAFORMA (catálogo de Apps,
  EntityType, Entity de qualquer organização, Group globais) - quem
  configura o SaaS em si, não uma organização específica.
- Organization Administrator: administra a SUA Entity (organização) -
  Branches, utilizadores/grupos dessa Entity, staff (Employee/
  Department).
- Branch Administrator: administra a SUA Branch - utilizadores dessa
  branch e staff, sem gerir a Entity nem outras Branches.

O isolamento real de "sua Entity"/"sua Branch" continua a ser feito
pelo tenant scope do request (CLAUDE.md #6/#7/#10), nunca por este
Group - o Group só concede a CAPACIDADE, nunca o âmbito.
"""

CORE_PROFILES = [
    {
        "name": "System Administrator",
        "permissions": [
            "view_entitytype", "add_entitytype", "change_entitytype", "list_entitytype",
            "view_entitytypeapp", "add_entitytypeapp", "change_entitytypeapp", "list_entitytypeapp",
            "view_entitytypegroup", "add_entitytypegroup", "change_entitytypegroup", "list_entitytypegroup",
            "view_app", "add_app", "change_app", "list_app",
            "view_entity", "add_entity", "change_entity", "list_entity",
            "view_group", "add_group", "change_group", "list_group",
            "view_user", "add_user", "change_user", "list_user",
        ],
    },
    {
        "name": "Organization Administrator",
        "permissions": [
            "view_entity", "change_entity",
            "view_branch", "add_branch", "change_branch", "list_branch",
            "view_entityapp", "add_entityapp", "change_entityapp", "list_entityapp",
            "view_entitygroup", "add_entitygroup", "change_entitygroup", "list_entitygroup",
            "view_entityuser", "add_entityuser", "change_entityuser", "list_entityuser",
            "view_group", "add_group", "change_group", "list_group",
            "view_branchuser", "add_branchuser", "change_branchuser", "list_branchuser",
            "view_branchusergroup", "add_branchusergroup", "change_branchusergroup", "list_branchusergroup",
            "view_branchgroup", "add_branchgroup", "change_branchgroup", "list_branchgroup",
            "view_user", "add_user", "change_user", "list_user",
            "view_person", "add_person", "change_person", "list_person",
            "view_employee", "add_employee", "change_employee", "list_employee",
            "view_department", "add_department", "change_department", "list_department",
        ],
    },
    {
        "name": "Branch Administrator",
        "permissions": [
            "view_branch",
            "view_branchuser", "add_branchuser", "change_branchuser", "list_branchuser",
            "view_branchusergroup", "add_branchusergroup", "change_branchusergroup", "list_branchusergroup",
            "view_user", "add_user", "change_user", "list_user",
            "view_person", "list_person",
            "view_employee", "change_employee", "list_employee",
            "view_department", "list_department",
        ],
    },
]
