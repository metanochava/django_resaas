from django.conf import settings

from django_resaas.models.model_extra_action import (
    ModelExtraAction
)


class ResaasSchemaBuilder:
    """
    Construtor oficial do RESAAS Schema.

    Responsável por transformar um Model Django
    num contrato declarativo consumível pelo frontend.
    """

    SCHEMA_VERSION = "1.0"


    # =========================================================
    # DEFAULT PERMISSIONS
    # =========================================================

    DEFAULT_PERMISSIONS = {
        "list": "list",
        "view": "view",
        "add": "add",
        "change": "change",
        "delete": "delete",
        "restore": "restore",
        "hard_delete": "hard_delete",
        "pdf": "pdf",
        "pdf_list": "pdf_list",
    }


    # =========================================================
    # INIT
    # =========================================================

    def __init__(
        self,
        Model,
        fields=None,
    ):

        self.Model = Model

        self.fields = fields or []

        self.meta = Model._meta

        self.app = self.meta.app_label

        self.model = self.meta.model_name

        self.resaas = getattr(
            Model,
            "RESAAS",
            None
        )


    # =========================================================
    # HELPER
    # =========================================================

    def get_resaas_value(
        self,
        name,
        default=None
    ):

        if not self.resaas:
            return default

        return getattr(
            self.resaas,
            name,
            default
        )


    # =========================================================
    # MODEL
    # =========================================================

    def build_model(self):

        return {

            "app": self.app,

            "name": self.model,

            "class_name":
                self.Model.__name__,

            "label":
                str(
                    self.meta.verbose_name
                ).title(),

            "label_plural":
                str(
                    self.meta.verbose_name_plural
                ).title(),

            "pk":
                self.meta.pk.name,

            # endpoint padrão da API
            "endpoint":
                f"{self.app}/{self.model}s/",

        }


    # =========================================================
    # PERMISSIONS
    # =========================================================

    def build_permissions(self):

        permissions = {}

        for name, prefix in (
            self.DEFAULT_PERMISSIONS.items()
        ):

            permissions[name] = (
                f"{prefix}_{self.model}"
            )


        # =====================================================
        # CUSTOM ACTION PERMISSIONS
        # =====================================================

        custom = {}

        actions = (
            ModelExtraAction.objects
            .filter(
                app=self.app,
                model=self.model,
            )
            .order_by(
                "order",
                "action"
            )
        )

        for action in actions:

            custom[action.action] = (
                action.permission
            )


        permissions["custom"] = custom

        return permissions


    # =========================================================
    # ACTIONS
    # =========================================================

    def build_actions(self):

        queryset = (
            ModelExtraAction.objects
            .filter(
                app=self.app,
                model=self.model,
            )
            .order_by(
                "order",
                "action"
            )
        )

        actions = []

        base_endpoint = (
            f"{self.app}/{self.model}s"
        )

        for extra in queryset:

            action_path = (
                extra.url
                or extra.action
            ).strip("/")


            # =============================================
            # DETAIL
            # =============================================

            if extra.details:

                endpoint = (
                    f"{base_endpoint}/"
                    f"{{id}}/"
                    f"{action_path}/"
                )

            else:

                endpoint = (
                    f"{base_endpoint}/"
                    f"{action_path}/"
                )


            actions.append({

                # =========================================
                # IDENTITY
                # =========================================

                "action":
                    extra.action,

                "app":
                    extra.app,

                "model":
                    extra.model,


                # =========================================
                # UI
                # =========================================

                "label":
                    extra.label,

                "icon":
                    extra.icon,

                "tooltip":
                    extra.tooltip,

                "position":
                    extra.position,

                "order":
                    extra.order,

                "visible":
                    extra.visible,


                # =========================================
                # HTTP
                # =========================================

                "method":
                    extra.method,

                "details":
                    extra.details,

                "url":
                    extra.url,

                # endpoint já resolvido pelo backend
                "endpoint":
                    endpoint,


                # =========================================
                # SECURITY
                # =========================================

                "permission":
                    extra.permission,

            })

        return actions


    # =========================================================
    # ROUTES
    # =========================================================

    def build_routes(self):

        default = {

            "list":
                f"list_{self.model}",

            "add":
                f"add_{self.model}",

            "change":
                f"change_{self.model}",

            "view":
                f"view_{self.model}",
        }

        routes = self.get_resaas_value(
            "routes",
            default
        )

        return {
            **default,
            **(routes or {})
        }


    # =========================================================
    # FILTERS
    # =========================================================

    def build_filters(self):

        search_fields = (
            self.get_resaas_value(
                "search_fields",
                []
            )
            or []
        )


        configured = (
            self.get_resaas_value(
                "filters",
                None
            )
        )


        # =============================================
        # FIELD NAMES
        # =============================================

        filter_fields = []

        for field in self.fields:

            name = field.get(
                "name"
            )

            if not name:
                continue

            filter_fields.append(
                name
            )


        default = {

            "enabled": True,

            "search": True,

            "search_fields":
                search_fields,

            "fields":
                filter_fields,

        }


        if isinstance(
            configured,
            dict
        ):

            return {
                **default,
                **configured
            }


        return default


    # =========================================================
    # PAGINATION
    # =========================================================

    def build_pagination(self):

        rest_framework = getattr(
            settings,
            "REST_FRAMEWORK",
            {}
        )

        page_size = (
            rest_framework.get(
                "PAGE_SIZE",
                10
            )
            or 10
        )


        default = {

            "enabled": True,

            "page_size":
                page_size,

            "page_size_options": [
                5,
                10,
                20,
                50,
                100,
                200,
                500,
            ],

            "default_ordering":
                "-id",

        }


        configured = (
            self.get_resaas_value(
                "pagination",
                None
            )
        )


        if isinstance(
            configured,
            dict
        ):

            return {
                **default,
                **configured
            }


        return default


    # =========================================================
    # UI
    # =========================================================

    def build_ui(self):

        default = {

            "title":
                str(
                    self.meta
                    .verbose_name_plural
                ).title(),

            "icon":
                self.get_resaas_value(
                    "icon",
                    None
                ),

            "crud":
                self.get_resaas_value(
                    "crud",
                    True
                ),

            "dense":
                True,

            "striped":
                True,

            "show_search":
                True,

            "show_filters":
                True,

            "show_columns":
                True,

            "show_refresh":
                True,

            "show_pdf":
                True,

            "show_pdf_list":
                True,

        }


        configured = (
            self.get_resaas_value(
                "ui",
                None
            )
        )


        if isinstance(
            configured,
            dict
        ):

            return {
                **default,
                **configured
            }


        return default


    # =========================================================
    # PDF
    # =========================================================

    def build_pdf(self):

        default = {

            "enabled": True,

            "detail": True,

            "list": True,

            "detail_permission":
                f"pdf_{self.model}",

            "list_permission":
                f"pdf_list_{self.model}",

            "detail_endpoint":
                (
                    f"{self.app}/"
                    f"{self.model}s/"
                    "{id}/pdf/"
                ),

            "list_endpoint":
                (
                    f"{self.app}/"
                    f"{self.model}s/"
                    "pdflist/"
                ),

        }


        configured = (
            self.get_resaas_value(
                "pdf",
                None
            )
        )


        if isinstance(
            configured,
            dict
        ):

            return {
                **default,
                **configured
            }


        return default


    # =========================================================
    # BUILD
    # =========================================================

    def build(self):

        model = (
            self.build_model()
        )

        actions = (
            self.build_actions()
        )

        permissions = (
            self.build_permissions()
        )

        routes = (
            self.build_routes()
        )

        ui = (
            self.build_ui()
        )

        filters = (
            self.build_filters()
        )

        pagination = (
            self.build_pagination()
        )

        pdf = (
            self.build_pdf()
        )


        return {

            # =============================================
            # CONTRACT
            # =============================================

            "schema_version":
                self.SCHEMA_VERSION,


            # =============================================
            # CORE
            # =============================================

            "model":
                model,

            "fields":
                self.fields,

            "actions":
                actions,

            "permissions":
                permissions,

            "routes":
                routes,

            "ui":
                ui,

            "filters":
                filters,

            "pagination":
                pagination,

            "pdf":
                pdf,


            # =============================================
            # BACKWARD COMPATIBILITY
            # =============================================

            "module":
                self.app,

            "config": {

                "crud":
                    ui["crud"],

                "routes":
                    routes,

            },

        }