
MENU = "Hr"
ICON = "menu"
SUBMENUS = [
    {
        "menu": "Dashboard",
        "icon": "dashboard",
        "role": "view_hr_dashboard",
        "route": "view_hr_dashboard",
    },
    {
        "menu": "Employee",
        "icon": "person",  # 🔥 segurança
        "role": "list_employee",
        "route": "list_employee",
        "add_role": "add_employee",
        "add_route": "add_employee",
        # 'crud': { 'module': 'auth', 'model': 'employee' }
    },
]
