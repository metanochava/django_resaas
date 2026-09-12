"""Resolução em cascata da aparência de header/footer:

    Entity -> EntityType -> default RESAAS

O nível mais específico que tiver algo definido (background != None)
vence por completo para essa área - não há merge campo-a-campo entre
níveis (mesma regra já usada por login_config no frontend: um nível
"tem" ou "não tem" configuração de fundo).

Usado por MeSerializer (config resolvida, pronta a aplicar).

Já não existe um nível de personalização por-utilizador aqui: essa
responsabilidade passou para User.theme (+ ThemeSurface, área
header/footer) - ver django_resaas.saas.models.user.User e
django_resaas.saas.models.theme_surface.ThemeSurface. O antigo modelo
`UserThemeOverride` foi removido; a personalização pessoal do
utilizador deixa agora de ser um objecto próprio por área
(header/footer) e passa a ser "o utilizador escolheu/personalizou um
Theme", cujas superfícies cobrem qualquer área visual (não só
header/footer).
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
    def _sources(*, entity, entity_type):
        # Ordem = prioridade: o primeiro que tiver config para a área
        # vence.
        return (entity, entity_type)

    @classmethod
    def resolve_area(cls, area, *, entity=None, entity_type=None):
        if area not in AREAS:
            raise ValueError(f"Área de interface desconhecida: '{area}'.")

        for source in cls._sources(entity=entity, entity_type=entity_type):
            if source is None:
                continue

            config = getattr(source, f"{area}_config", None)

            if config:
                return config

        return DEFAULT_CONFIG[area]

    @classmethod
    def resolve(cls, *, entity=None, entity_type=None):
        return {
            area: cls.resolve_area(area, entity=entity, entity_type=entity_type)
            for area in AREAS
        }
