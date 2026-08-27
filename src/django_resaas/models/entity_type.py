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
        null=True,
        help_text='Name of the entity type.'
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

    label = models.CharField(
        max_length=100,
        null=True,
        help_text='Display label used to identify this entity type.'
    )

    ordem = models.IntegerField(
        default=2,
        help_text='Display order of this entity type.'
    )

    crair_entity = models.BooleanField(
        null=True,
        default=True,
        help_text='Allow entities to be created for this entity type.'
    )

    # =========================================================
    # LOGIN DEFAULT CONFIG
    #
    # EntityType fornece os valores padrão.
    # Entity pode sobrescrever estes valores.
    # =========================================================

    login_position = models.CharField(
        max_length=30,
        choices=LOGIN_POSITION_CHOICES,
        default='center',
        help_text=(
            'Default position of the login form. '
            'Entities may override this setting.'
        )
    )

    login_background_type = models.CharField(
        max_length=20,
        choices=LOGIN_BACKGROUND_TYPE_CHOICES,
        default='color',
        help_text=(
            'Default background type used on the login page. '
            'Entities may override this setting.'
        )
    )

    login_background_color = models.CharField(
        max_length=50,
        default='#ffffff',
        blank=True,
        help_text=(
            'Default login background color, for example #ffffff. '
            'Used when the background type is Color.'
        )
    )

    login_background_gradient = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text=(
            'Default CSS gradient used on the login page, for example '
            'linear-gradient(135deg, #1976d2, #26a69a). '
            'Used when the background type is Gradient.'
        )
    )

    login_background_image = models.FileField(
        upload_to=login_background_path,
        null=True,
        blank=True,
        help_text=(
            'Default background image displayed on the login page. '
            'Used when the background type is Image.'
        )
    )

    login_background_overlay = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        help_text=(
            'Default dark overlay opacity applied to the login background. '
            'Use a value between 0 and 1.'
        )
    )

    # =========================================================
    # THEME / UI
    # =========================================================

    theme = models.ForeignKey(
        'django_resaas.Theme',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Default visual theme used by this entity type.'
    )

    layout_settings = models.ForeignKey(
        'django_resaas.LayoutSetting',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Default layout configuration used by this entity type.'
    )

    typography = models.ForeignKey(
        'django_resaas.Typography',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Default typography configuration used by this entity type.'
    )

    animation_settings = models.ForeignKey(
        'django_resaas.AnimationSetting',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
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