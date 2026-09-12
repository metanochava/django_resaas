from django.db import models

from django_resaas.saas.core.base.models import TimeModel
from django_resaas.saas.models.mixins.visual_area import (
    FooterVisualFields,
    HeaderVisualFields,
)


def icon_path(instance, file_name):
    return f'{instance.name}/{file_name}'


class EntityType(HeaderVisualFields, FooterVisualFields, TimeModel):

    # =========================================================
    # GENERAL
    # =========================================================

    name = models.CharField(
        max_length=100,
        null=True,
        help_text='Name of the entity type.'
    )

    label = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Display label used to identify this entity type.'
    )

    icon = models.FileField(
        upload_to=icon_path,
        default='logo.png',
        blank=True,
        help_text='Default icon used by this entity type.'
    )

    license = models.TextField(
        default='license',
        help_text='License information associated with this entity type.'
    )

    ordem = models.IntegerField(
        default=2,
        help_text='Display order of this entity type.'
    )

    crair_entity = models.BooleanField(
        default=True,
        help_text='Allow entities to be created for this entity type.'
    )

    # =========================================================
    # DEFAULT UI CONFIGURATION
    # =========================================================

    theme = models.ForeignKey(
        'django_resaas.Theme',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='entity_types',
        help_text='Default visual theme used by this entity type.'
    )

    layout_settings = models.ForeignKey(
        'django_resaas.LayoutSetting',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='entity_types',
        help_text='Default layout configuration used by this entity type.'
    )

    typography = models.ForeignKey(
        'django_resaas.Typography',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='entity_types',
        help_text='Default typography configuration used by this entity type.'
    )

    animation_settings = models.ForeignKey(
        'django_resaas.AnimationSetting',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='entity_types',
        help_text='Default animation configuration used by this entity type.'
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:
        permissions = ()

    # =========================================================
    # RESAAS
    # =========================================================

    class RESAAS:
        label_field = "name"

        fields = {
            "icon": {
                "accept": ".png,.jpg,.jpeg,.svg,.webp",
                "max_size": 2 * 1024 * 1024,
                "multiple": False
            }
        }

    # =========================================================
    # UI CONFIGURATION
    # =========================================================

    @property
    def ui_config(self):

        theme = self.theme
        layout = self.layout_settings
        typography = self.typography
        animation = self.animation_settings

        return {
            "theme": (
                theme.to_dict()
                if theme
                and hasattr(theme, 'to_dict')
                else None
            ),

            "layout": (
                layout.to_dict()
                if layout
                and hasattr(layout, 'to_dict')
                else None
            ),

            "typography": (
                typography.to_dict()
                if typography
                and hasattr(typography, 'to_dict')
                else None
            ),

            "animation": (
                animation.to_dict()
                if animation
                and hasattr(animation, 'to_dict')
                else None
            ),
        }

    # =========================================================
    # HELPERS
    # =========================================================

    @property
    def theme_config(self):
        if not self.theme:
            return None

        if hasattr(self.theme, 'to_dict'):
            return self.theme.to_dict()

        return None

    @property
    def layout_config(self):
        if not self.layout_settings:
            return None

        if hasattr(self.layout_settings, 'to_dict'):
            return self.layout_settings.to_dict()

        return None

    @property
    def typography_config(self):
        if not self.typography:
            return None

        if hasattr(self.typography, 'to_dict'):
            return self.typography.to_dict()

        return None

    @property
    def animation_config(self):
        if not self.animation_settings:
            return None

        if hasattr(self.animation_settings, 'to_dict'):
            return self.animation_settings.to_dict()

        return None

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        return self.name or ''