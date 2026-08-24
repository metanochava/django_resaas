from rest_framework.decorators import action


def resaas_action(
    *,
    methods=None,
    detail=False,
    label=None,
    icon=None,
    tooltip=None,
    position=None,
    order=0,
    visible=True,
    autorequest=False,
    url_path=None,
    url_name=None,
):
    """
    Decorator RESAAS para declarar actions customizadas
    em ViewSets/BaseAPIView.

    Regras:
    - o nome da função identifica a action;
    - o nome da função também será usado para gerar
      o codename da permission;
    - este decorator NÃO grava na base de dados;
    - apenas guarda metadata no método;
    - a persistência é responsabilidade do ActionSyncService.
    """

    # =====================================================
    # METHODS
    # =====================================================

    methods = [
        str(method).lower()
        for method in (methods or ["post"])
    ]


    # =====================================================
    # DECORATOR
    # =====================================================

    def decorator(func):

        # =================================================
        # ACTION NAME
        # =================================================

        action_name = func.__name__


        # =================================================
        # URL
        # =================================================

        path = url_path or action_name

        name = url_name or action_name


        # =================================================
        # METADATA
        # =================================================

        metadata = {

            "action": action_name,

            "label": (
                label
                or action_name.replace("_", " ").title()
            ),

            "icon": icon,

            "tooltip": tooltip,

            "position": position,

            "order": order,

            "visible": visible,

            "autorequest": bool(autorequest),

            "methods": methods,

            "detail": bool(detail),

            "url_path": path,

            "url_name": name,

            "managed_by": "decorator",

        }


        # =================================================
        # DRF ACTION
        # =================================================

        decorated = action(
            methods=methods,
            detail=detail,
            url_path=path,
            url_name=name,
        )(func)


        # =================================================
        # RESAAS METADATA
        # =================================================

        decorated._resaas_action = metadata


        # =================================================
        # RETURN
        # =================================================

        return decorated


    return decorator