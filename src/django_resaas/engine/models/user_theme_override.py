from django.conf import settings
from django.db import models

from django_resaas.engine.core.base.models import TimeModel
from django_resaas.engine.models.mixins.visual_area import (
    FooterVisualFields,
    HeaderVisualFields,
)


class UserThemeOverride(HeaderVisualFields, FooterVisualFields, TimeModel):
    """Personalização visual do próprio utilizador para header/footer -
    o nível mais específico da cascata de resolução (User > Entity >
    EntityType > default), ver
    engine/core/services/interface_config_service.py.

    Uma linha por User, criada só quando o utilizador personaliza pela
    primeira vez (nunca criada automaticamente para todos os
    utilizadores) - "reset" é simplesmente apagar esta linha (ou pôr
    os campos da área a None), voltando a herdar de Entity/EntityType.

    Não vive em User directamente (CLAUDE.md: não misturar
    autenticação com preferências de UI) nem em Person (identidade,
    não preferência de interface).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="theme_override",
    )

    class Meta:
        verbose_name = "User Theme Override"
        verbose_name_plural = "User Theme Overrides"

    def __str__(self):
        return f"Theme override - {self.user_id}"
