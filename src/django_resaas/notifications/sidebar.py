ALL = [{
    'MENU': "Notifications",
    'ICON': "notifications",

    'SUBMENUS': [
        {
            "icon": "space_dashboard",
            "menu": "Dashboard",
            "role": "view_notifications_dashboard",
            "route": "view_notifications_dashboard",
        },
        {
            "add_role": "add_notificationrule",
            "add_route": "add_notificationrule",
            "icon": "rule",
            "menu": "Rules",
            "role": "list_notificationrule",
            "route": "list_notificationrule",
        },
        {
            "add_role": "add_notificationtemplate",
            "add_route": "add_notificationtemplate",
            "icon": "description",
            "menu": "Templates",
            "role": "list_notificationtemplate",
            "route": "list_notificationtemplate",
        },
        {
            "add_role": "add_notificationpreference",
            "add_route": "add_notificationpreference",
            "icon": "tune",
            "menu": "Preferences",
            "role": "list_notificationpreference",
            "route": "list_notificationpreference",
        },
        {
            "add_role": "add_notificationsettings",
            "add_route": "add_notificationsettings",
            "icon": "settings",
            "menu": "Settings",
            "role": "list_notificationsettings",
            "route": "list_notificationsettings",
        },
        # Outbox/Delivery Attempts são read-only por desenho (ver
        # notifications/views/outbox.py e delivery_attempt.py -
        # create/update/partial_update/destroy devolvem sempre 405) -
        # por isso não têm add_role/add_route, tal como Payroll Run/
        # Leave Calendar em hr/sidebar.py seguem a mesma convenção
        # para workflows não-CRUD.
        {
            "icon": "outbox",
            "menu": "Outbox",
            "role": "list_notificationoutbox",
            "route": "list_notificationoutbox",
        },
        {
            "icon": "history",
            "menu": "Delivery Attempts",
            "role": "list_notificationdeliveryattempt",
            "route": "list_notificationdeliveryattempt",
        },
    ]
}]
