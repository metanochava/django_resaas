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
renomeados aqui. O Admin está em CORE_PROFILES: recebe a administração
da Entity e perde as permissões da lib (PLATFORM_PERMISSIONS).

Distinção de âmbito:

- A PLATAFORMA (EntityType, Entity de qualquer organização, Group globais)
  é do Root: tudo o que é da lib (catálogo de Apps, EntityTypes, scaffold
  e Scaffold IDE - PLATFORM_PERMISSIONS, revogadas ao Admin). Não há um
  perfil "System Administrator" (removido em 2026-10-11).
- Admin: administra a SUA Entity (organização) - Branches, utilizadores e
  perfis dessa Entity; só altera perfis editáveis dessa Entity
  (core/services/group_access_service.py). Substituiu o perfil
  "Organization Administrator" (removido em 2026-10-11).
- Branch Admin: administra a SUA Branch - utilizadores dessa
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

# Scaffold and Scaffold IDE (ScaffoldAPIView, IDEWorkspaceAPIView): they write
# the project's source code - lib work, Root only.
SCAFFOLD_PERMISSIONS = [
    "view_dev", "view_crud", "view_scaffold", "add_scaffold", "change_scaffold", "delete_scaffold",
]

# EntityTypes and their templates (apps, profiles, models) are the platform's
# catalogue. change_entitytype is also what makes a caller "platform level" in
# core/services/group_access_service.py (sees and changes every profile).
_ACTIONS = ("list", "view", "add", "change", "delete", "hard_delete", "restore", "pdf", "pdf_list")
ENTITY_TYPE_PERMISSIONS = [
    f"{action}_{model}"
    for model in ("entitytype", "entitytypeapp", "entitytypegroup", "entitytypemodel")
    for action in _ACTIONS
]

# Root = permissions about the lib/platform; Admin = manages ITS Entity only
# (and, through group_access_service, only the editable profiles of that
# Entity). These are revoked from Admin on every migrate.
PLATFORM_PERMISSIONS = APP_PERMISSIONS + SCAFFOLD_PERMISSIONS + ENTITY_TYPE_PERMISSIONS

# old profile names -> current ones (group_creator renames the existing Group in
# place: same id, members and permissions kept). Modules that add permissions to
# these profiles pass it too, whichever post_migrate runs first.
CORE_RENAMES = {"Branch Admin": "Branch Administrator"}

CORE_PROFILES = [
    {
        # administers ITS Entity (it replaced "Organization Administrator",
        # removed on 2026-10-11): Branches, users, profiles of that Entity.
        # Never the lib/platform permissions (Root's).
        "name": "Admin",
        "revoke": PLATFORM_PERMISSIONS,
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
        "name": "Branch Admin",
        "permissions": [
            "view_branch",
            "view_branchuser", "add_branchuser", "change_branchuser", "list_branchuser",
            "view_branchusergroup", "add_branchusergroup", "change_branchusergroup", "list_branchusergroup",
            "view_user", "add_user", "change_user", "list_user",
            "view_person", "list_person",
        ],
    },
]
