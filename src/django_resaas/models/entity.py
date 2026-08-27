from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from django_resaas.models.user import User
from django_resaas.core.base.models import TimeModel


def logo_path(instance, file_name):
    return f'{instance.entity_type.name}/{instance.name}/{file_name}'


def login_background_path(instance, file_name):
    return f'{instance.entity_type.name}/{instance.name}/login/{file_name}'


class Entity(TimeModel):

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
        default='-',
        help_text='Name of the entity.'
    )

    site = models.CharField(
        max_length=300,
        null=True,
        default='-',
        help_text='Website or domain associated with the entity.'
    )

    # =========================================================
    # BRAND
    # =========================================================

    logo = models.FileField(
        upload_to=logo_path,
        default='logo.png',
        blank=True,
        help_text='Logo displayed for this entity.'
    )

    display_logo = models.BooleanField(
        default=True,
        null=True,
        blank=True,
        help_text='Display the entity logo in the application.'
    )

    display_bar = models.BooleanField(
        default=True,
        null=True,
        blank=True,
        help_text='Display the application bar for this entity.'
    )

    display_qr = models.BooleanField(
        default=True,
        null=True,
        blank=True,
        help_text='Display the QR code when available.'
    )

    display_logo_login = models.BooleanField(
        default=True,
        null=True,
        blank=True,
        help_text='Display the entity logo on the login page.'
    )

    # =========================================================
    # LOGIN
    #
    # NULL = herdar configuração do EntityType
    # =========================================================

    login_position = models.CharField(
        max_length=30,
        choices=LOGIN_POSITION_CHOICES,
        null=True,
        blank=True,
        default=None,
        help_text=(
            'Position of the login form. '
            'Leave empty to inherit from the entity type.'
        )
    )

    login_background_type = models.CharField(
        max_length=20,
        choices=LOGIN_BACKGROUND_TYPE_CHOICES,
        null=True,
        blank=True,
        default=None,
        help_text=(
            'Type of background used on the login page. '
            'Leave empty to inherit from the entity type.'
        )
    )

    login_background_color = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default=None,
        help_text=(
            'Background color for the login page, for example #ffffff. '
            'Used when the background type is Color.'
        )
    )

    login_background_gradient = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        default=None,
        help_text=(
            'CSS gradient used as the login background, for example '
            'linear-gradient(135deg, #1976d2, #26a69a).'
        )
    )

    login_background_image = models.FileField(
        upload_to=login_background_path,
        null=True,
        blank=True,
        default=None,
        help_text=(
            'Background image displayed on the login page. '
            'Used when the background type is Image.'
        )
    )

    login_background_overlay = models.FloatField(
        null=True,
        blank=True,
        default=None,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ],
        help_text=(
            'Dark overlay opacity applied to the login background. '
            'Use a value between 0 and 1. '
            'Leave empty to inherit from the entity type.'
        )
    )

    # =========================================================
    # ENTITY TYPE
    # =========================================================

    entity_type = models.ForeignKey(
        'django_resaas.EntityType',
        on_delete=models.CASCADE,
        help_text='Entity type associated with this entity.'
    )

    # =========================================================
    # THEME / UI
    # =========================================================

    theme = models.ForeignKey(
        'django_resaas.Theme',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Visual theme used by this entity.'
    )

    layout_settings = models.ForeignKey(
        'django_resaas.LayoutSetting',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Layout configuration used by this entity.'
    )

    typography = models.ForeignKey(
        'django_resaas.Typography',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Typography configuration used by this entity.'
    )

    animation_settings = models.ForeignKey(
        'django_resaas.AnimationSetting',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Animation configuration used by this entity.'
    )

    # =========================================================
    # ADMINS
    # =========================================================

    admins = models.ManyToManyField(
        User,
        help_text='Users with administrative access to this entity.'
    )

    # =========================================================
    # FOOTER
    # =========================================================

    rodape = models.CharField(
        max_length=2000,
        null=True,
        help_text='Footer text displayed for this entity.'
    )

    # =========================================================
    # STORAGE
    # =========================================================

    disc_space = models.FloatField(
        default=1048576.0,
        null=True,
        help_text='Maximum disk space allocated to this entity.'
    )

    disc_used_space = models.FloatField(
        default=0.0,
        null=True,
        help_text='Disk space currently used by this entity.'
    )

    disc_free_space = models.FloatField(
        default=1048576.0,
        null=True,
        help_text='Remaining disk space available to this entity.'
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
            'change': "change_entity"
        }

        fields = {

            "logo": {
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
    # LOGIN BACKGROUND OVERRIDE
    # =========================================================

    @property
    def login_background(self):

        if self.login_background_type == 'image':

            if self.login_background_image:
                return {
                    "type": "image",
                    "value": self.login_background_image.url
                }

            return None

        if self.login_background_type == 'gradient':

            if self.login_background_gradient:
                return {
                    "type": "gradient",
                    "value": self.login_background_gradient
                }

            return None

        if self.login_background_type == 'color':

            if self.login_background_color:
                return {
                    "type": "color",
                    "value": self.login_background_color
                }

            return None

        return None

    # =========================================================
    # LOGIN CONFIG OVERRIDE
    # =========================================================

    @property
    def login_config(self):

        return {
            "position": self.login_position,
            "background": self.login_background,
            "overlay": self.login_background_overlay
        }

    # =========================================================
    # SAVE
    # =========================================================

    def save(self, *args, **kwargs):

        if (
            self.disc_free_space is None
            or self.disc_free_space > self.disc_space
        ):
            self.disc_free_space = (
                self.disc_space
                -
                self.disc_used_space
            )

        super().save(*args, **kwargs)

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        return self.name or ''