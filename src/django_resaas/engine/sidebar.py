ALL = [
{
'MENU' : "Engine",
'ICON' : "menu",  # 🔥 mais dev

'SUBMENUS' : [
    {
        "menu": "Dashboard",
        "icon": "space_dashboard",  # mais moderno
        "role": "view_django_resaas_dashboard",
        "route": "view_django_resaas_dashboard",
    },
    {
        # Rota já registada em quasar_resaas/router/restRoutes.js
        # ("view_core_dashboard" -> pages/core/DashBoard.vue, "Access
        # Control Dashboard") mas sem entrada de sidebar nenhuma e sem
        # a permissão sequer existir na BD - página inacessível por
        # completo (nem por menu nem por URL directo). Regista-se
        # também a permissão em MODULE_PERMISSIONS (engine/core/
        # signals/permissions.py), tal como já acontece para
        # view_hr_dashboard/view_django_resaas_dashboard.
        "menu": "Access Control",
        "icon": "admin_panel_settings",
        "role": "view_core_dashboard",
        "route": "view_core_dashboard",
    },
    {
        "menu": "Permission",
        "icon": "verified_user",  # 🔥 segurança
        "role": "list_permission",
        "route": "list_permission",
        "add_role": "add_permission",
        "add_route": "add_permission",
        # 'crud': { 'module': 'auth', 'model': 'Permission' }
    },
    {
        "menu": "Group",
        "icon": "groups",  # melhor que group
        "role": "list_group",
        "route": "list_group",
        "add_role": "add_group",
        "add_route": "add_group",
        # 'crud': { 'module': 'auth', 'model': 'Group' }
    },
    {
        "menu": "File",
        "icon": "folder_open",  # melhor UX
        "role": "list_file",
        "route": "list_file",
        "add_role": "add_file",
        "add_route": "add_file",
        'crud': { 'module': 'django_resaas', 'model': 'File' }
    },
    {
        "menu": "Translation",
        "icon": "translate",
        "role": "list_translation",
        "route": "list_translation",
        "add_role": "add_translation",
        "add_route": "add_translation",
        'crud': { 'module': 'django_resaas', 'model': 'Translation' }
    },
    {
        "menu": "EntityType",
        "icon": "apartment",  # mais semântico
        "role": "list_entitytype",
        "route": "list_entitytype",
        "add_role": "add_entitytype",
        "add_route": "add_entitytype",
        # 'crud': { 'module': 'django_resaas', 'model': 'EntityType' }
    },    
    {
        "menu": "Entity",
        "icon": "domain",  # 🔥 empresa
        "role": "list_entity",
        "route": "list_entity",
        "add_role": "add_entity",
        "add_route": "add_entity",
        # 'crud': { 'module': 'django_resaas', 'model': 'Entity' }
    },  
    {
        "menu": "Branch",
        "icon": "store",  # melhor que house
        "role": "list_branch",
        "route": "list_branch",
        "add_role": "add_branch",
        "add_route": "add_branch",
        # 'crud': { 'module': 'django_resaas', 'model': 'Branch' }
    }, 
    {
        "menu": "User",
        "icon": "account_circle",  # mais moderno
        "role": "list_user",
        "route": "list_user",
        "add_role": "add_user",
        "add_route": "add_user",
        # 'crud': { 'module': 'django_resaas', 'model': 'User' }
    },  
    {
        "menu": "App",
        "icon": "view_module",  # 🔥 dev style
        "role": "list_App",
        "route": "list_App",
        "add_role": "add_App",
        "add_route": "add_App",
        'crud': { 'module': 'django_resaas', 'model': 'App' }
    },
    {
        "menu": "Model",
        "icon": "data_object",  # 🔥 DEV PERFEITO
        "role": "list_model",
        "route": "list_model",
        "add_role": "add_model",
        "add_route": "add_model",
        'crud': { 'module': 'django_resaas', 'model': 'Model' }
    }, 
    {
        "menu": "Cometario",
        "icon": "chat_bubble_outline",
        "role": "list_cometario",
        "route": "list_cometario",
        "add_role": "add_cometario",
        "add_route": "add_cometario",
        'crud': { 'module': 'django_resaas', 'model': 'Cometario' }
    },

    {
        "menu": "Crud",
        "icon": "build",  # 🔥 melhor que construction
        "role": "view_crud",
        "route": "view_crud",
    },

    {
        "menu": "Dev",
        "icon": "code",  # 🔥 ESSENCIAL
        "role": "view_dev",
        "submenu": [
            {
                "menu": "Criar App",
                "icon": "add_box",
                "role": "add_app",
                "route": "add_app",
            },
            {
                "menu": "Scaffold",
                "icon": "developer_mode",  # 🔥 MUITO BOM
                "role": "view_scaffold",
                "route": "view_scaffold",
            },       
        ]
    },
]
}
]