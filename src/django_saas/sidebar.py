
MENU = "Core"
ICON = "menu"

SUBMENUS = [
    {
        "menu": "Dashboard",
        "icon": "dashboard",
        "role": "view_django_saas_dashboard",
        "rota": "view_django_saas_dashboard",
    },
    {
        "menu": "Crud",
        "icon": "construction",
        "role": "view_crud",
        "rota": "crud_state",
    },
    {
        "menu": "Ficheiro",
        "icon": "insert_drive_file",
        "role": "list_ficheiro",
        "rota": "list_ficheiro",
        "add_role": "add_ficheiro",
        "add_rota": "add_ficheiro",
        'crud': { 'module': 'django_saas', 'model': 'Ficheiro' }
    },
    {
        "menu": "Traducao",
        "icon": "translate",
        "role": "list_traducao",
        "rota": "list_traducao",
        "add_role": "add_traducao",
        "add_rota": "add_traducao",
        'crud': { 'module': 'django_saas', 'model': 'Traducao' }
    },
    {
        "menu": "TipoEntidade",
        "icon": "corporate_fare",
        "role": "list_tipoentidade",
        "rota": "list_tipoentidade",
        "add_role": "add_tipoentidade",
        "add_rota": "add_tipoentidade",
        'crud': { 'module': 'django_saas', 'model': 'TipoEntidade' }
    },    
    {
        "menu": "Entidade",
        "icon": "home",
        "role": "list_entidade",
        "rota": "list_entidade",
        "add_role": "add_entidade",
        "add_rota": "add_entidade",
        'crud': { 'module': 'django_saas', 'model': 'Entidade' }
    },  
    {
        "menu": "Sucursal",
        "icon": "house",
        "role": "list_sucursal",
        "rota": "list_sucursal",
        "add_role": "add_sucursal",
        "add_rota": "add_sucursal",
        'crud': { 'module': 'django_saas', 'model': 'Sucursal' }
    }, 
    {
        "menu": "Grupo",
        "icon": "group",
        "role": "list_group",
        "rota": "list_group",
        "add_role": "add_group",
        "add_rota": "add_group",
        'crud': { 'module': 'auth', 'model': 'Group' }
    }, 
    {
        "menu": "Permission",
        "icon": "admin_panel_settings",
        "role": "list_permission",
        "rota": "list_permission",
        "add_role": "add_permission",
        "add_rota": "add_permission",
        'crud': { 'module': 'auth', 'model': 'Permission' }
    }, 
    {
        "menu": "User",
        "icon": "person",
        "role": "list_user",
        "rota": "list_user",
        "add_role": "add_user",
        "add_rota": "add_user",
        'crud': { 'module': 'django_saas', 'model': 'User' }
    },  
    # {
    #     "menu": "Modulo",
    #     "icon": "extension",
    #     "role": "list_Modulo",
    #     "rota": "list_Modulo",
    #     "add_role": "add_Modulo",
    #     "add_rota": "add_Modulo",
    #     'crud': { 'module': 'django_saas', 'model': 'Modulo' }
    # },
    # {
    #     "menu": "Modelo",
    #     "icon": "schema",
    #     "role": "list_modelo",
    #     "rota": "list_modelo",
    #     "add_role": "add_modelo",
    #     "add_rota": "add_modelo",
    #     'crud': { 'module': 'django_saas', 'model': 'Modelo' }
    # }, 

    # {
    #     "menu": "Cometario",
    #     "icon": "mode_comment",
    #     "role": "list_cometario",
    #     "rota": "list_cometario",
    #     "add_role": "add_cometario",
    #     "add_rota": "add_cometario",
    #     'crud': { 'module': 'django_saas', 'model': 'Cometario' }
    # },
    {
        "menu": "Dev",
        "icon": "list",
        "role": "view_scaffold",
        "submenu": [
            {
                "menu": "Criar Modulo",
                "icon": "list",
                "role": "add_modulo",
                "rota": "add_modulo",
            },
            {
                "menu": "Scaffold",
                "icon": "list",
                "role": "view_scaffold",
                "rota": "view_scaffold",
            },       
        ]
    },
]