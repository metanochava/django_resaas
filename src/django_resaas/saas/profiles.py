"""Perfis (Group templates) de administração da plataforma/tenant -
mesmo mecanismo já usado por saude/sales/inventory/farmacia (ver
`saas/core/utils/group_creator.py`).

Estes perfis são de âmbito de PLATAFORMA/TENANT (Entity/Branch), não
de um módulo de negócio - por isso vivem em `saas` (core SaaS
infrastructure, CLAUDE.md #55/#87.11) e não em `hr` ou em qualquer app
de negócio. Os perfis só nomeiam permissões do próprio core. Um módulo (ex.: o HR de
uma aplicação) acrescenta as suas a estes mesmos perfis no seu próprio
`profiles.py`: `group_creator()` é aditivo por nome de perfil.

Não confundir com `GROUPS = ["Guest", "Admin", "Root"]` (mesmo
ficheiro) - esses são grupos de bootstrap/teste sem permissões
próprias, usados por `testutils`/fixtures existentes; não são
renomeados aqui - o Admin só aparece em CORE_PROFILES para lhe retirar o
catálogo de Apps (APP_PERMISSIONS).

Distinção de âmbito:

- A PLATAFORMA (EntityType, Entity de qualquer organização, Group globais)
  é administrada pelo grupo Admin; não há um perfil "System Administrator"
  (foi removido em 2026-10-11 por duplicar o Admin). O catálogo de Apps
  (list_app e a página de módulos) é só do Root: APP_PERMISSIONS é
  revogado ao Admin.
- Organization Administrator: administra a SUA Entity (organização) -
  Branches, utilizadores/grupos dessa Entity.
- Branch Administrator: administra a SUA Branch - utilizadores dessa
  branch, sem gerir a Entity nem outras Branches.

O isolamento real de "sua Entity"/"sua Branch" continua a ser feito
pelo tenant scope do request (CLAUDE.md #6/#7/#10), nunca por este
Group - o Group só concede a CAPACIDADE, nunca o âmbito.
"""

# The App catalogue (AppAPIView, AppSchemaAPIView: list/create/delete modules,
# link them to EntityTypes) is Root-only. Root gets every permission from the
# post_migrate signal (core/signals/permissions.py); these are taken away from
# the Admin group, which used to hold them.
APP_PERMISSIONS = [
    "list_app", "view_app", "add_app", "change_app", "delete_app",
    "hard_delete_app", "restore_app", "pdf_app", "pdf_list_app",
]

CORE_PROFILES = [
    {
        # bootstrap group (GROUPS in group_creator.py), not a profile: listed
        # only to take the App catalogue away from it
        "name": "Admin",
        "revoke": APP_PERMISSIONS,
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
        ],
    },
]
