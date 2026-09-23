"""Validação estrutural de `DASHBOARD` (declarado em <app>/dashboard.py).

Corre uma única vez por dashboard, durante a descoberta (discovery.py) -
nunca a cada request. Um erro aqui significa "configuração inválida",
não "erro de import" (esse é tratado em discovery.py e nunca é
escondido).
"""

from django_resaas.saas.core.dashboards.exceptions import DashboardConfigError

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}

SUPPORTED_FILTER_TYPES = {
    "text", "search", "select", "multi_select", "autocomplete",
    "boolean", "date", "date_range", "month", "year",
    "number", "number_range", "entity", "branch", "status",
}

# Tipos de widget conhecidos pelo motor (o frontend tem o mesmo registry
# em widgetRegistry.js). Um tipo desconhecido NÃO é erro de configuração
# - é aceite (forward-compatible: permite declarar um dashboard.py para
# um tipo de widget que só o frontend ainda vai suportar), mas o widget
# perde a garantia de contrato de resposta normalizado.
KNOWN_WIDGET_TYPES = {
    "stat", "bar_chart", "line_chart", "pie_chart",
    "table", "list", "calendar",
}

# Tipos de action suportados pelo DashboardActionResolver genérico do
# frontend (quasar_resaas/services/dashboardActions.js). "route" reusa
# o vue-router já existente - nunca inventa rotas novas aqui, o
# dashboard.py de cada app é que aponta para rotas REAIS já
# registadas.
SUPPORTED_ACTION_TYPES = {"route", "refresh", "fullscreen", "dialog"}

# Quasar grid: every row of cards must add up to exactly this many columns.
GRID_COLUMNS = 12
GRID_BREAKPOINTS = ("xs", "sm", "md", "lg", "xl")

REQUIRED_DASHBOARD_FIELDS = ("name", "label")
REQUIRED_WIDGET_FIELDS = ("name", "type", "provider")
REQUIRED_ACTION_FIELDS = ("name", "type")


class DashboardValidator:

    @classmethod
    def validate(cls, config, *, app_label):
        if not isinstance(config, dict):
            raise DashboardConfigError(
                f"'{app_label}.dashboard.DASHBOARD' deve ser um dict.",
                code="invalid_dashboard_type",
            )

        schema_version = config.get("schema_version")

        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise DashboardConfigError(
                f"'{app_label}.dashboard.DASHBOARD' tem schema_version "
                f"'{schema_version}' desconhecida. Suportadas: "
                f"{sorted(SUPPORTED_SCHEMA_VERSIONS)}.",
                code="unsupported_schema_version",
            )

        for field in REQUIRED_DASHBOARD_FIELDS:
            if not config.get(field):
                raise DashboardConfigError(
                    f"'{app_label}.dashboard.DASHBOARD' não define "
                    f"'{field}', que é obrigatório.",
                    fields={field: ["Este campo é obrigatório."]},
                )

        cls._validate_filters(
            config.get("filters") or [],
            context=f"{app_label}.dashboard.DASHBOARD.filters",
        )

        global_filter_names = {
            f["name"] for f in (config.get("filters") or [])
        }

        cls._validate_widgets(
            config.get("widgets") or [],
            global_filter_names=global_filter_names,
            app_label=app_label,
        )

        cls._validate_layout(config.get("widgets") or [], app_label=app_label)

        permission = config.get("permission")
        if permission is not None and not isinstance(permission, str):
            raise DashboardConfigError(
                f"'{app_label}.dashboard.DASHBOARD.permission' deve ser "
                "uma string (codename) ou omitido.",
                fields={"permission": ["Deve ser uma string."]},
            )

        cls._validate_tooltip(
            config.get("tooltip"),
            context=f"'{app_label}.dashboard.DASHBOARD'",
        )

    @classmethod
    def _validate_widgets(cls, widgets, *, global_filter_names, app_label):
        if not isinstance(widgets, list):
            raise DashboardConfigError(
                f"'{app_label}.dashboard.DASHBOARD.widgets' deve ser uma "
                "lista.",
            )

        seen_names = set()

        for widget in widgets:
            if not isinstance(widget, dict):
                raise DashboardConfigError(
                    f"Cada widget de '{app_label}.dashboard.DASHBOARD' "
                    "deve ser um dict.",
                )

            for field in REQUIRED_WIDGET_FIELDS:
                if not widget.get(field):
                    raise DashboardConfigError(
                        f"Widget de '{app_label}' não define '{field}', "
                        "que é obrigatório.",
                        fields={field: ["Este campo é obrigatório."]},
                    )

            name = widget["name"]

            if name in seen_names:
                raise DashboardConfigError(
                    f"Widget duplicado '{name}' em '{app_label}.dashboard"
                    ".DASHBOARD.widgets'.",
                    code="duplicate_widget",
                    fields={"name": [f"Widget '{name}' já existe."]},
                )
            seen_names.add(name)

            permission_mode = widget.get("permission_mode", "any")
            if permission_mode not in ("all", "any"):
                raise DashboardConfigError(
                    f"Widget '{name}' de '{app_label}' tem "
                    f"permission_mode inválido: '{permission_mode}'. "
                    "Use 'all' ou 'any'.",
                    fields={"permission_mode": ["Use 'all' ou 'any'."]},
                )

            widget_filters = widget.get("filters") or []
            widget_filter_names = cls._validate_filters(
                widget_filters,
                context=f"widget '{name}' de '{app_label}'",
            )

            colliding = widget_filter_names & global_filter_names
            if colliding:
                raise DashboardConfigError(
                    f"Widget '{name}' de '{app_label}' declara filtro(s) "
                    f"{sorted(colliding)} com o mesmo nome de filtro(s) "
                    "globais do dashboard - use nomes distintos.",
                    code="duplicate_filter",
                    fields={"filters": [
                        f"Nome(s) já usados como filtro global: "
                        f"{sorted(colliding)}."
                    ]},
                )

            for accepted in widget.get("accepts_filters") or []:
                if (
                    accepted not in global_filter_names
                    and accepted not in widget_filter_names
                ):
                    raise DashboardConfigError(
                        f"Widget '{name}' de '{app_label}' declara "
                        f"accepts_filters=['{accepted}'] mas não existe "
                        "nenhum filtro global nem próprio com esse nome.",
                        fields={"accepts_filters": [
                            f"Filtro '{accepted}' não existe."
                        ]},
                    )

            widget_context = f"widget '{name}' de '{app_label}'"

            cls._validate_tooltip(widget.get("tooltip"), context=widget_context)

            cls._validate_actions_list(
                widget.get("actions"), context=f"{widget_context}.actions"
            )
            cls._validate_actions_list(
                widget.get("row_actions"), context=f"{widget_context}.row_actions"
            )

            if widget.get("primary_action") is not None:
                cls._validate_action(
                    widget["primary_action"], context=f"{widget_context}.primary_action"
                )

            if widget.get("item_action") is not None:
                cls._validate_action(
                    widget["item_action"], context=f"{widget_context}.item_action"
                )

    @staticmethod
    def effective_span(cols, breakpoint):
        """Columns a widget takes at `breakpoint`, as the frontend renders them
        (WidgetContainer.vue): xs is always a full row (`col-12`); sm falls back
        to the declared xs; every larger breakpoint inherits the nearest smaller
        declared one; no `cols` at all means `col-12 col-md-6`."""
        if not cols:
            return 12 if breakpoint in ("xs", "sm") else 6

        if breakpoint == "xs":
            return 12

        span = cols.get("xs", 12) if "sm" not in cols else cols["sm"]

        for name in GRID_BREAKPOINTS[2:GRID_BREAKPOINTS.index(breakpoint) + 1]:
            span = cols.get(name, span)

        return span

    @classmethod
    def _validate_layout(cls, widgets, *, app_label):
        """RULE: at every breakpoint, the widgets (in `order`) fill rows of
        exactly GRID_COLUMNS columns - a row that adds up to less (or a card
        that would overflow into the next row) is a configuration error.

        Checked on the declared widgets. A widget the current user cannot see
        (permissions) is removed at request time, so a row can still end up
        short for that user; that cannot be known here."""
        ordered = sorted(
            (w for w in widgets if isinstance(w, dict)),
            key=lambda w: w.get("order", 999),
        )

        for widget in ordered:
            cols = widget.get("cols")

            if cols is None:
                continue

            if not isinstance(cols, dict):
                raise DashboardConfigError(
                    f"Widget '{widget['name']}' of '{app_label}' has invalid 'cols': "
                    "expected a dict such as {'xs': 12, 'md': 4}.",
                    fields={"cols": ["Must be a dict."]},
                )

            for breakpoint, span in cols.items():
                if (
                    breakpoint not in GRID_BREAKPOINTS
                    or isinstance(span, bool)
                    or not isinstance(span, int)
                    or not 1 <= span <= GRID_COLUMNS
                ):
                    raise DashboardConfigError(
                        f"Widget '{widget['name']}' of '{app_label}' has invalid cols "
                        f"{breakpoint!r}: {span!r}. Breakpoints: {list(GRID_BREAKPOINTS)}; "
                        f"each span must be an integer from 1 to {GRID_COLUMNS}.",
                        code="invalid_widget_cols",
                        fields={"cols": [f"Invalid value for {breakpoint!r}."]},
                    )

        for breakpoint in GRID_BREAKPOINTS:
            row, total = [], 0

            for widget in ordered:
                span = cls.effective_span(widget.get("cols"), breakpoint)

                if total + span > GRID_COLUMNS:
                    cls._raise_incomplete_row(app_label, breakpoint, row, total)

                row.append(widget["name"])
                total += span

                if total == GRID_COLUMNS:
                    row, total = [], 0

            if row:
                cls._raise_incomplete_row(app_label, breakpoint, row, total)

    @staticmethod
    def _raise_incomplete_row(app_label, breakpoint, row, total):
        raise DashboardConfigError(
            f"'{app_label}.dashboard.DASHBOARD' has a row that adds up to {total} "
            f"columns at breakpoint '{breakpoint}' (widgets {row}); every row must "
            f"add up to exactly {GRID_COLUMNS}. Adjust the widgets' 'cols'.",
            code="dashboard_row_not_full",
            fields={"cols": [f"Row at '{breakpoint}' adds up to {total}, not {GRID_COLUMNS}."]},
        )

    @classmethod
    def _validate_filters(cls, filters, *, context):
        if not isinstance(filters, list):
            raise DashboardConfigError(
                f"Filtros de {context} devem ser uma lista.",
            )

        seen_names = set()

        for filter_def in filters:
            if not isinstance(filter_def, dict):
                raise DashboardConfigError(
                    f"Cada filtro de {context} deve ser um dict.",
                )

            name = filter_def.get("name")
            filter_type = filter_def.get("type")

            if not name:
                raise DashboardConfigError(
                    f"Filtro de {context} não define 'name'.",
                    fields={"name": ["Este campo é obrigatório."]},
                )

            if name in seen_names:
                raise DashboardConfigError(
                    f"Filtro duplicado '{name}' em {context}.",
                    code="duplicate_filter",
                    fields={"name": [f"Filtro '{name}' já existe."]},
                )
            seen_names.add(name)

            if filter_type not in SUPPORTED_FILTER_TYPES:
                raise DashboardConfigError(
                    f"Filtro '{name}' de {context} tem tipo desconhecido: "
                    f"'{filter_type}'. Suportados: "
                    f"{sorted(SUPPORTED_FILTER_TYPES)}.",
                    code="unsupported_filter_type",
                    fields={"type": ["Tipo de filtro não suportado."]},
                )

            cls._validate_tooltip(filter_def.get("tooltip"), context=f"filtro '{name}' de {context}")

        return seen_names

    @classmethod
    def _validate_tooltip(cls, tooltip, *, context):
        """tooltip é só metadata de apresentação (nunca identificador
        técnico/de permissão - ver docs/architecture/dashboards.md) -
        a única validação que faz sentido aqui é o tipo."""

        if tooltip is not None and not isinstance(tooltip, str):
            raise DashboardConfigError(
                f"'tooltip' de {context} deve ser uma string ou omitido.",
                fields={"tooltip": ["Deve ser uma string."]},
            )

    @classmethod
    def _validate_action(cls, action_def, *, context):
        if not isinstance(action_def, dict):
            raise DashboardConfigError(f"Uma action de {context} deve ser um dict.")

        for field in REQUIRED_ACTION_FIELDS:
            if not action_def.get(field):
                raise DashboardConfigError(
                    f"Action de {context} não define '{field}', que é obrigatório.",
                    fields={field: ["Este campo é obrigatório."]},
                )

        action_name = action_def["name"]
        action_type = action_def["type"]

        if action_type not in SUPPORTED_ACTION_TYPES:
            raise DashboardConfigError(
                f"Action '{action_name}' de {context} tem type desconhecido: "
                f"'{action_type}'. Suportados: {sorted(SUPPORTED_ACTION_TYPES)}.",
                code="unsupported_action_type",
                fields={"type": ["Tipo de action não suportado."]},
            )

        if action_type == "route" and not isinstance(action_def.get("route"), dict):
            raise DashboardConfigError(
                f"Action '{action_name}' de {context} é do tipo 'route' mas "
                "não define 'route' (dict com pelo menos 'name').",
                fields={"route": ["Obrigatório para type='route'."]},
            )

        permission_mode = action_def.get("permission_mode", "any")
        if permission_mode not in ("all", "any"):
            raise DashboardConfigError(
                f"Action '{action_name}' de {context} tem permission_mode "
                f"inválido: '{permission_mode}'. Use 'all' ou 'any'.",
                fields={"permission_mode": ["Use 'all' ou 'any'."]},
            )

        cls._validate_tooltip(action_def.get("tooltip"), context=f"action '{action_name}' de {context}")

    @classmethod
    def _validate_actions_list(cls, actions, *, context):
        if actions is None:
            return

        if not isinstance(actions, list):
            raise DashboardConfigError(f"'{context}' deve ser uma lista.")

        seen_names = set()

        for action_def in actions:
            cls._validate_action(action_def, context=context)

            name = action_def["name"]

            if name in seen_names:
                raise DashboardConfigError(
                    f"Action duplicada '{name}' em '{context}'.",
                    code="duplicate_action",
                    fields={"name": [f"Action '{name}' já existe."]},
                )
            seen_names.add(name)
