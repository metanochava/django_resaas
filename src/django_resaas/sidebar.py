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
        "menu": "Grupo",
        "icon": "groups",  # melhor que group
        "role": "list_group",
        "rota": "list_group",
        "add_role": "add_group",
        "add_rota": "add_group",
        'crud': { 'module': 'auth', 'model': 'Group' }
    }, 
    {
        "menu": "Permission",
        "icon": "verified_user",  # 🔥 segurança
        "role": "list_permission",
        "rota": "list_permission",
        "add_role": "add_permission",
        "add_rota": "add_permission",
        'crud': { 'module': 'auth', 'model': 'Permission' }
    }, 
    {
        "menu": "Ficheiro",
        "icon": "folder_open",  # melhor UX
        "role": "list_ficheiro",
        "rota": "list_ficheiro",
        "add_role": "add_ficheiro",
        "add_rota": "add_ficheiro",
        'crud': { 'module': 'django_resaas', 'model': 'Ficheiro' }
    },
    {
        "menu": "Traducao",
        "icon": "translate",
        "role": "list_traducao",
        "rota": "list_traducao",
        "add_role": "add_traducao",
        "add_rota": "add_traducao",
        'crud': { 'module': 'django_resaas', 'model': 'Traducao' }
    },
    {
        "menu": "TipoEntidade",
        "icon": "apartment",  # mais semântico
        "role": "list_tipoentidade",
        "rota": "list_tipoentidade",
        "add_role": "add_tipoentidade",
        "add_rota": "add_tipoentidade",
        # 'crud': { 'module': 'django_resaas', 'model': 'TipoEntidade' }
    },    
    {
        "menu": "Entidade",
        "icon": "domain",  # 🔥 empresa
        "role": "list_entidade",
        "rota": "list_entidade",
        "add_role": "add_entidade",
        "add_rota": "add_entidade",
        # 'crud': { 'module': 'django_resaas', 'model': 'Entidade' }
    },  
    {
        "menu": "Sucursal",
        "icon": "store",  # melhor que house
        "role": "list_sucursal",
        "rota": "list_sucursal",
        "add_role": "add_sucursal",
        "add_rota": "add_sucursal",
        # 'crud': { 'module': 'django_resaas', 'model': 'Sucursal' }
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
        "menu": "Modulo",
        "icon": "view_module",  # 🔥 dev style
        "role": "list_Modulo",
        "rota": "list_Modulo",
        "add_role": "add_Modulo",
        "add_rota": "add_Modulo",
        'crud': { 'module': 'django_resaas', 'model': 'Modulo' }
    },
    {
        "menu": "Modelo",
        "icon": "data_object",  # 🔥 DEV PERFEITO
        "role": "list_modelo",
        "rota": "list_modelo",
        "add_role": "add_modelo",
        "add_rota": "add_modelo",
        'crud': { 'module': 'django_resaas', 'model': 'Modelo' }
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
                "menu": "Criar Modulo",
                "icon": "add_box",
                "role": "add_modulo",
                "rota": "add_modulo",
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