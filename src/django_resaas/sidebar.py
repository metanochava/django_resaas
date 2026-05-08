MENU = "Core"
ICON = "menu"  # 🔥 mais dev

SUBMENUS = [
    {
        "menu": "Dashboard",
        "icon": "space_dashboard",  # mais moderno
        "role": "view_django_resaas_dashboard",
        "rota": "view_django_resaas_dashboard",
    },
    {
        "menu": "Permission",
        "icon": "verified_user",  # 🔥 segurança
        "role": "list_permission",
        "rota": "list_permission",
        "add_role": "add_permission",
        "add_rota": "add_permission",
        # 'crud': { 'module': 'auth', 'model': 'Permission' }
    },
    {
        "menu": "Group",
        "icon": "groups",  # melhor que group
        "role": "list_group",
        "rota": "list_group",
        "add_role": "add_group",
        "add_rota": "add_group",
        # 'crud': { 'module': 'auth', 'model': 'Group' }
    },
    {
        "menu": "File",
        "icon": "folder_open",  # melhor UX
        "role": "list_file",
        "rota": "list_file",
        "add_role": "add_file",
        "add_rota": "add_file",
        'crud': { 'module': 'django_resaas', 'model': 'File' }
    },
    {
        "menu": "Translation",
        "icon": "translate",
        "role": "list_translation",
        "rota": "list_translation",
        "add_role": "add_translation",
        "add_rota": "add_translation",
        'crud': { 'module': 'django_resaas', 'model': 'Translation' }
    },
    {
        "menu": "EntityType",
        "icon": "apartment",  # mais semântico
        "role": "list_entitytype",
        "rota": "list_entitytype",
        "add_role": "add_entitytype",
        "add_rota": "add_entitytype",
        # 'crud': { 'module': 'django_resaas', 'model': 'EntityType' }
    },    
    {
        "menu": "Entity",
        "icon": "domain",  # 🔥 empresa
        "role": "list_entity",
        "rota": "list_entity",
        "add_role": "add_entity",
        "add_rota": "add_entity",
        # 'crud': { 'module': 'django_resaas', 'model': 'Entity' }
    },  
    {
        "menu": "Branch",
        "icon": "store",  # melhor que house
        "role": "list_branch",
        "rota": "list_branch",
        "add_role": "add_branch",
        "add_rota": "add_branch",
        # 'crud': { 'module': 'django_resaas', 'model': 'Branch' }
    }, 
    {
        "menu": "User",
        "icon": "account_circle",  # mais moderno
        "role": "list_user",
        "rota": "list_user",
        "add_role": "add_user",
        "add_rota": "add_user",
        # 'crud': { 'module': 'django_resaas', 'model': 'User' }
    },  
    {
        "menu": "App",
        "icon": "view_module",  # 🔥 dev style
        "role": "list_App",
        "rota": "list_App",
        "add_role": "add_App",
        "add_rota": "add_App",
        'crud': { 'module': 'django_resaas', 'model': 'App' }
    },
    {
        "menu": "Model",
        "icon": "data_object",  # 🔥 DEV PERFEITO
        "role": "list_model",
        "rota": "list_model",
        "add_role": "add_model",
        "add_rota": "add_model",
        'crud': { 'module': 'django_resaas', 'model': 'Model' }
    }, 
    {
        "menu": "Cometario",
        "icon": "chat_bubble_outline",
        "role": "list_cometario",
        "rota": "list_cometario",
        "add_role": "add_cometario",
        "add_rota": "add_cometario",
        'crud': { 'module': 'django_resaas', 'model': 'Cometario' }
    },

    {
        "menu": "Crud",
        "icon": "build",  # 🔥 melhor que construction
        "role": "view_crud",
        "rota": "crud_state",
    },

    {
        "menu": "Dev",
        "icon": "code",  # 🔥 ESSENCIAL
        "role": "view_scaffold",
        "submenu": [
            {
                "menu": "Criar App",
                "icon": "add_box",
                "role": "add_app",
                "rota": "add_app",
            },
            {
                "menu": "Scaffold",
                "icon": "developer_mode",  # 🔥 MUITO BOM
                "role": "view_scaffold",
                "rota": "view_scaffold",
            },       
        ]
    },
]