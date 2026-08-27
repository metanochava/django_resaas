from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from django_resaas.core.base.models import TimeModel


def icon_path(instance, file_name):
    return f'{instance.name}/{file_name}'


def login_background_path(instance, file_name):
    return f'{instance.name}/login/{file_name}'


class EntityType(TimeModel):

    # =========================================================
    # CHOICES
    # =========================================================

    LOGIN_POSITION_CHOICES = [
        ('top-left', 'Top Left'),
        ('top-right', 'Top Right'),
        ('center', 'Center'),
        ('bottom-left', 'Bottom Left'),
        ('bottom-right', 'Bottom Right'),
    ]

    LOGIN_BACKGROUND_TYPE_CHOICES = [
        ('color', 'Color'),
        ('gradient', 'Gradient'),
        ('image', 'Image'),
    ]

    # =========================================================
    # GENERAL
    # =========================================================

    name = models.CharField(
        max_length=100,
        null=True
    )

    icon = models.FileField(
        upload_to=icon_path,
        default='logo.png',
        blank=True
    )

    license = models.TextField(
        default='license'
    )

    label = models.CharField(
        max_length=100,
        null=True
    )

    ordem = models.IntegerField(
        default=2
    )

    crair_entity = models.BooleanField(
        null=True,
        default=True
    )

    # =========================================================
    # LOGIN DEFAULT CONFIG
    #
    # EntityType fornece os valores padrão.
    # =========================================================

    login_position = models.CharField(
        max_length=30,
        choices=LOGIN_POSITION_CHOICES,
        default='center'
    )

    login_background_type = models.CharField(
        max_length=20,
        choices=LOGIN_BACKGROUND_TYPE_CHOICES,
        default='color'
    )

    login_background_color = models.CharField(
        max_length=50,
        default='#ffffff',
        blank=True
    )

    login_background_gradient = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )

    login_background_image = models.FileField(
        upload_to=login_background_path,
        null=True,
        blank=True
    )

    login_background_overlay = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ]
    )

    # =========================================================
    # THEME / UI
    # =========================================================

    theme = models.ForeignKey(
        'django_resaas.Theme',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    layout_settings = models.ForeignKey(
        'django_resaas.LayoutSetting',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    typography = models.ForeignKey(
        'django_resaas.Typography',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    animation_settings = models.ForeignKey(
        'django_resaas.AnimationSetting',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
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
                "accept": ".png,.jpg,.jpeg,.svg",
                "max_size": 2 * 1024 * 1024,
                "multiple": False
            },

            "login_background_image": {
                "accept": ".png,.jpg,.jpeg,.webp",
                "max_size": 5 * 1024 * 1024,
                "multiple": False
            }

        }

    # =========================================================
    # LOGIN BACKGROUND
    # =========================================================

    @property
    def login_background(self):

        if (
            self.login_background_type == 'image'
            and self.login_background_image
        ):
            return {
                "type": "image",
                "value": self.login_background_image.url
            }

        if (
            self.login_background_type == 'gradient'
            and self.login_background_gradient
        ):
            return {
                "type": "gradient",
                "value": self.login_background_gradient
            }

        return {
            "type": "color",
            "value": self.login_background_color or '#ffffff'
        }

    # =========================================================
    # LOGIN CONFIG
    # =========================================================

    @property
    def login_config(self):

        return {
            "position": self.login_position or 'center',
            "background": self.login_background,
            "overlay": self.login_background_overlay
        }

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        return self.name or ''