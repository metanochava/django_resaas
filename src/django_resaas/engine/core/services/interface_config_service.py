"""Resolução em cascata da aparência de header/footer:

    User (UserThemeOverride) -> Entity -> EntityType -> default RESAAS

O nível mais específico que tiver algo definido (background != None)
vence por completo para essa área - não há merge campo-a-campo entre
níveis (mesma regra já usada por login_config no frontend: um nível
"tem" ou "não tem" configuração de fundo).

Usado por MeSerializer (config resolvida, pronta a aplicar) e pelos
endpoints de edição/reset do próprio utilizador (UserAPIView).
"""

DEFAULT_CONFIG = {
    "header": {
        "background": {"type": "color", "value": "#1976D2"},
        "overlay": 0,
        "text_color": "#FFFFFF",
    },
    "footer": {
        "background": {"type": "color", "value": "#1976D2"},
        "overlay": 0,
        "text_color": "#FFFFFF",
    },
}

AREAS = ("header", "footer")


class InterfaceConfigService:

    @staticmethod
    def _sources(*, user, entity, entity_type):
        # Ordem = prioridade: o primeiro que tiver config para a área
        # vence. getattr(user, "theme_override", None) é seguro mesmo
        # sem override criado - Django devolve None para o lado "um"
        # de um OneToOne inexistente (RelatedObjectDoesNotExist
        # herda de AttributeError precisamente para isto).
        override = getattr(user, "theme_override", None) if user else None
        return (override, entity, entity_type)

    @classmethod
    def resolve_area(cls, area, *, user=None, entity=None, entity_type=None):
        if area not in AREAS:
            raise ValueError(f"Área de interface desconhecida: '{area}'.")

        for source in cls._sources(user=user, entity=entity, entity_type=entity_type):
            if source is None:
                continue

            config = getattr(source, f"{area}_config", None)

            if config:
                return config

        return DEFAULT_CONFIG[area]

    @classmethod
    def resolve(cls, *, user=None, entity=None, entity_type=None):
        return {
            area: cls.resolve_area(area, user=user, entity=entity, entity_type=entity_type)
            for area in AREAS
        }

    @classmethod
    def resolve_override_only(cls, *, user):
        """Config em bruto que o PRÓPRIO utilizador definiu (para um
        formulário de edição) - None numa área significa "sem
        personalização, a herdar de Entity/EntityType"."""

        override = getattr(user, "theme_override", None) if user else None

        return {
            area: getattr(override, f"{area}_config", None) if override else None
            for area in AREAS
        }
