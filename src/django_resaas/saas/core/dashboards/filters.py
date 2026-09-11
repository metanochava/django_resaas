"""Validação e parsing de filtros de dashboard/widget.

Convenções adoptadas (documentadas aqui porque não havia precedente
único no projecto a reutilizar):

- multi_select: chave repetida (`status=confirmed&status=pending`) -
  não vírgula. Escolhida porque é exactamente o que
  `quasar_resaas/services/api.js`'s `url()` já serializa para arrays
  (`URLSearchParams.append` por item) e o que `DjangoFilterBackend`
  já espera nas outras listagens da plataforma.
- date_range / number_range: cada filtro `name` do tipo `date_range`
  é enviado como dois parâmetros `{name}_from`/`{name}_to`
  (`number_range` como `{name}_min`/`{name}_max`), porque um dashboard
  pode ter vários filtros deste tipo (ex.: `period` e `contract_date`)
  - um único par fixo `data_inicio`/`data_fim`
  (TenantDashboardAPIView.require_period, pensado para UM período por
  dashboard) não escala para múltiplos filtros deste tipo.
- entity/branch: o valor nunca vem do cliente - é sempre fixado ao
  contexto do request (request.entity_id/branch_id). Se o cliente
  enviar um valor diferente, é erro de validação (nunca ultrapassa o
  tenant silenciosamente).
- Parâmetro desconhecido (que não corresponde a nenhum filtro
  aceite por este widget) é erro 400, não ignorado - normalmente
  indica um bug do frontend.
"""

from datetime import datetime

from django_resaas.saas.core.dashboards.exceptions import DashboardFilterError

# Parâmetros reservados pelo próprio motor (scope de
# TenantDashboardAPIView, paginação de ResaasPagination, negociação de
# formato do DRF) - nunca tratados como "filtro desconhecido".
RESERVED_PARAMS = {"scope", "page", "page_size", "format"}


def _choice_values(choices):
    return {
        c.get("value") if isinstance(c, dict) else c
        for c in (choices or [])
    }


def _parse_date(raw, *, field):
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise DashboardFilterError(
            f"Data inválida em '{field}': '{raw}' (esperado YYYY-MM-DD).",
            fields={field: ["Data inválida (esperado YYYY-MM-DD)."]},
        )


def _parse_month(raw, *, field):
    try:
        return datetime.strptime(raw, "%Y-%m").date().replace(day=1)
    except (ValueError, TypeError):
        raise DashboardFilterError(
            f"Mês inválido em '{field}': '{raw}' (esperado YYYY-MM).",
            fields={field: ["Mês inválido (esperado YYYY-MM)."]},
        )


def _parse_year(raw, *, field):
    try:
        year = int(raw)
    except (ValueError, TypeError):
        raise DashboardFilterError(
            f"Ano inválido em '{field}': '{raw}'.",
            fields={field: ["Ano inválido."]},
        )
    if year < 1900 or year > 2200:
        raise DashboardFilterError(
            f"Ano fora do intervalo aceite: '{raw}'.",
            fields={field: ["Ano fora do intervalo aceite."]},
        )
    return year


def _parse_number(raw, *, field):
    try:
        return float(raw) if "." in str(raw) else int(raw)
    except (ValueError, TypeError):
        raise DashboardFilterError(
            f"Número inválido em '{field}': '{raw}'.",
            fields={field: ["Número inválido."]},
        )


class DashboardFilterService:

    @staticmethod
    def resolve_widget_filter_defs(dashboard_config, widget_config):
        """Filtros efectivamente disponíveis para ESTE widget: filtros
        globais que o widget aceitou via `accepts_filters`, mais os
        filtros próprios do widget (âmbito `scope: widget`)."""

        global_filters = {
            f["name"]: f for f in dashboard_config.get("filters") or []
        }
        widget_own = {
            f["name"]: f for f in widget_config.get("filters") or []
        }
        accepted_names = set(widget_config.get("accepts_filters") or [])

        resolved = {
            name: widget_own.get(name, global_filters.get(name))
            for name in accepted_names
            if name in global_filters or name in widget_own
        }

        for name, filter_def in widget_own.items():
            resolved.setdefault(name, filter_def)

        return resolved

    @staticmethod
    def param_names(name, filter_type):
        if filter_type == "date_range":
            return {f"{name}_from", f"{name}_to"}
        if filter_type == "number_range":
            return {f"{name}_min", f"{name}_max"}
        return {name}

    @classmethod
    def validate_and_parse(cls, filter_defs, request):
        """`filter_defs`: {name: filter_def} - normalmente o resultado
        de resolve_widget_filter_defs(). Devolve {name: valor_tipado}.
        Levanta DashboardFilterError (400) para qualquer parâmetro
        desconhecido ou inválido."""

        allowed_params = set()
        for name, filter_def in filter_defs.items():
            allowed_params |= cls.param_names(name, filter_def["type"])

        fields = {}

        for key in request.query_params.keys():
            if key in RESERVED_PARAMS or key in allowed_params:
                continue
            fields.setdefault(key, []).append(
                "Filtro desconhecido para este widget."
            )

        parsed = {}

        for name, filter_def in filter_defs.items():
            try:
                value = cls._parse_one(name, filter_def, request)
            except DashboardFilterError as exc:
                for field, messages in exc.fields.items():
                    fields.setdefault(field, []).extend(messages)
                continue

            if value is not None:
                parsed[name] = value

        if fields:
            raise DashboardFilterError("Filtros inválidos.", fields=fields)

        return parsed

    @classmethod
    def _parse_one(cls, name, filter_def, request):
        filter_type = filter_def["type"]
        required = bool(filter_def.get("required"))

        if filter_type == "date_range":
            raw_from = request.query_params.get(f"{name}_from")
            raw_to = request.query_params.get(f"{name}_to")

            if not raw_from and not raw_to:
                if required:
                    raise DashboardFilterError(
                        f"'{name}' é obrigatório.",
                        fields={f"{name}_from": ["Obrigatório."]},
                    )
                return None

            date_from = _parse_date(raw_from, field=f"{name}_from") if raw_from else None
            date_to = _parse_date(raw_to, field=f"{name}_to") if raw_to else None

            if date_from and date_to and date_from > date_to:
                raise DashboardFilterError(
                    f"'{name}_from' não pode ser depois de '{name}_to'.",
                    fields={f"{name}_from": ["Intervalo de datas inválido."]},
                )

            return {"from": date_from, "to": date_to}

        if filter_type == "number_range":
            raw_min = request.query_params.get(f"{name}_min")
            raw_max = request.query_params.get(f"{name}_max")

            if raw_min is None and raw_max is None:
                if required:
                    raise DashboardFilterError(
                        f"'{name}' é obrigatório.",
                        fields={f"{name}_min": ["Obrigatório."]},
                    )
                return None

            value_min = _parse_number(raw_min, field=f"{name}_min") if raw_min is not None else None
            value_max = _parse_number(raw_max, field=f"{name}_max") if raw_max is not None else None

            if value_min is not None and value_max is not None and value_min > value_max:
                raise DashboardFilterError(
                    f"'{name}_min' não pode ser maior que '{name}_max'.",
                    fields={f"{name}_min": ["Intervalo numérico inválido."]},
                )

            return {"min": value_min, "max": value_max}

        raw = request.query_params.get(name)

        if filter_type == "multi_select":
            values = request.query_params.getlist(name)
            if not values:
                if required:
                    raise DashboardFilterError(
                        f"'{name}' é obrigatório.", fields={name: ["Obrigatório."]}
                    )
                return None
            choices = _choice_values(filter_def.get("choices"))
            if choices:
                invalid = [v for v in values if v not in choices]
                if invalid:
                    raise DashboardFilterError(
                        f"Valor(es) inválido(s) para '{name}': {invalid}.",
                        fields={name: [f"Valores inválidos: {invalid}."]},
                    )
            return values

        # entity/branch resolvem sempre ao contexto do request, mesmo
        # quando o cliente não envia nada - nunca "sem valor" (None),
        # porque um provider que use este filtro para scoping tem de
        # o receber sempre. Por isso ficam antes do `raw is None`
        # genérico dos restantes tipos.
        if filter_type == "entity":
            if raw and str(raw) != str(request.entity_id):
                raise DashboardFilterError(
                    "Não é possível filtrar por outra entity.",
                    code="cross_tenant_filter",
                    fields={name: ["Fora do contexto do tenant actual."]},
                )
            return str(request.entity_id)

        if filter_type == "branch":
            if raw and str(raw) != str(request.branch_id):
                raise DashboardFilterError(
                    "Não é possível filtrar por outra branch.",
                    code="cross_tenant_filter",
                    fields={name: ["Fora do contexto do tenant actual."]},
                )
            return str(request.branch_id) if request.branch_id else None

        if raw is None:
            if required:
                raise DashboardFilterError(
                    f"'{name}' é obrigatório.", fields={name: ["Obrigatório."]}
                )
            return None

        if filter_type == "date":
            return _parse_date(raw, field=name)

        if filter_type == "month":
            return _parse_month(raw, field=name)

        if filter_type == "year":
            return _parse_year(raw, field=name)

        if filter_type == "number":
            return _parse_number(raw, field=name)

        if filter_type == "boolean":
            if str(raw).lower() in ("true", "1", "yes"):
                return True
            if str(raw).lower() in ("false", "0", "no"):
                return False
            raise DashboardFilterError(
                f"Valor booleano inválido em '{name}': '{raw}'.",
                fields={name: ["Use true/false."]},
            )

        if filter_type in ("select", "status"):
            choices = _choice_values(filter_def.get("choices"))
            if choices and raw not in choices:
                raise DashboardFilterError(
                    f"Valor inválido para '{name}': '{raw}'.",
                    fields={name: [f"Valor inválido: '{raw}'."]},
                )
            return raw

        # text / search / autocomplete - texto livre, sem mais validação.
        return raw
