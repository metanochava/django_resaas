from django.db import models

from django_resaas.saas.models.user import User
from django_resaas.saas.core.base.models import TimeModel
from django_resaas.saas.models.mixins.visual_area import (
    FooterVisualFields,
    HeaderVisualFields,
)


def logo_path(instance, file_name):
    entity_type = getattr(instance.entity_type, 'name', 'entity')
    entity = instance.name or str(instance.id)

    return f'{entity_type}/{entity}/{file_name}'


class Entity(HeaderVisualFields, FooterVisualFields, TimeModel):

    # =========================================================
    # GENERAL
    # =========================================================

    name = models.CharField(
        max_length=100,
        default='-',
        help_text='Name of the entity.',
    )

    site = models.URLField(
        max_length=300,
        null=True,
        blank=True,
        help_text='Website associated with the entity.',
    )

    # =========================================================
    # BRAND
    # =========================================================

    logo = models.FileField(
        upload_to=logo_path,
        default='logo.png',
        blank=True,
        help_text='Official logo of the entity.',
    )

    # =========================================================
    # ADDRESS
    # =========================================================

    address = models.OneToOneField(
        'django_resaas.Address',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entity',
        help_text='Main address of the entity.',
    )

    # =========================================================
    # ENTITY TYPE
    # =========================================================

    entity_type = models.ForeignKey(
        'django_resaas.EntityType',
        on_delete=models.CASCADE,
        help_text='Entity type associated with this entity.',
    )

    # =========================================================
    # UI CONFIGURATION
    # =========================================================

    theme = models.ForeignKey(
        'django_resaas.Theme',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Visual theme used by this entity.',
    )

    layout_settings = models.ForeignKey(
        'django_resaas.LayoutSetting',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Layout configuration used by this entity.',
    )

    typography = models.ForeignKey(
        'django_resaas.Typography',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Typography configuration used by this entity.',
    )

    animation_settings = models.ForeignKey(
        'django_resaas.AnimationSetting',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Animation configuration used by this entity.',
    )

    # =========================================================
    # ADMINS
    # =========================================================

    admins = models.ManyToManyField(
        User,
        blank=True,
        help_text='Users with administrative access to this entity.',
    )

    # =========================================================
    # CONTENT
    # =========================================================

    rodape = models.CharField(
        max_length=2000,
        null=True,
        blank=True,
        help_text='Footer text displayed for this entity.',
    )

    # =========================================================
    # STORAGE
    # =========================================================

    disc_space = models.FloatField(
        default=1048576.0,
        help_text='Maximum disk space allocated to this entity.',
    )

    disc_used_space = models.FloatField(
        default=0.0,
        help_text='Disk space currently used by this entity.',
    )

    disc_free_space = models.FloatField(
        default=1048576.0,
        help_text='Remaining disk space available to this entity.',
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
        crud = True

        routes = {
            'list': "add_entity",
            'view': "view_entity",
            'add': "add_entity",
            'change': "change_entity",
        }

        fields = {
            "logo": {
                "accept": ".png,.jpg,.jpeg,.svg,.webp",
                "max_size": 2 * 1024 * 1024,
                "multiple": False,
            }
        }

    # =========================================================
    # CONFIGURATION
    # =========================================================

    @property
    def ui_config(self):
        return {
            "theme": (
                self.theme.to_dict()
                if self.theme
                else None
            ),

            "layout": (
                self.layout_settings.to_dict()
                if self.layout_settings
                else None
            ),

            "typography": (
                self.typography.to_dict()
                if self.typography
                else None
            ),

            "animation": (
                self.animation_settings.to_dict()
                if self.animation_settings
                and hasattr(self.animation_settings, 'to_dict')
                else None
            ),
        }

    # =========================================================
    # STORAGE
    # =========================================================

    def save(self, *args, **kwargs):
        self.disc_used_space = self.disc_used_space or 0
        self.disc_space = self.disc_space or 0

        self.disc_free_space = max(
            self.disc_space - self.disc_used_space,
            0,
        )

        super().save(*args, **kwargs)

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        return self.name or ''