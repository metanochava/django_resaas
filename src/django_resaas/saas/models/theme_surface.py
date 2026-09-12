from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from django_resaas.saas.core.base.models import TimeModel
from django_resaas.saas.models.theme import Theme


# =========================================================
# THEME SURFACE
# =========================================================


def theme_background_path(instance, file_name):
    return f'themes/{instance.theme_id}/{instance.area}/{file_name}'


class ThemeSurface(TimeModel):

    AREA_CHOICES = [
        ('login', 'Login'),
        ('layout', 'Layout'),
        ('page', 'Page'),
        ('header', 'Header'),
        ('footer', 'Footer'),
        ('sidebar', 'Sidebar'),
        ('drawer', 'Drawer'),
        ('toolbar', 'Toolbar'),
        ('card', 'Card'),
        ('dialog', 'Dialog'),
    ]

    BACKGROUND_TYPE_CHOICES = [
        ('transparent', 'Transparent'),
        ('color', 'Color'),
        ('gradient', 'Gradient'),
        ('image', 'Image'),
    ]

    BACKGROUND_SIZE_CHOICES = [
        ('auto', 'Auto'),
        ('cover', 'Cover'),
        ('contain', 'Contain'),
        ('100% 100%', 'Stretch'),
    ]

    BACKGROUND_POSITION_CHOICES = [
        ('center', 'Center'),
        ('top', 'Top'),
        ('bottom', 'Bottom'),
        ('left', 'Left'),
        ('right', 'Right'),
        ('top left', 'Top Left'),
        ('top right', 'Top Right'),
        ('bottom left', 'Bottom Left'),
        ('bottom right', 'Bottom Right'),
    ]

    theme = models.ForeignKey(
        Theme,
        on_delete=models.CASCADE,
        related_name='surfaces',
    )

    area = models.CharField(
        max_length=30,
        choices=AREA_CHOICES,
    )

    background_type = models.CharField(
        max_length=20,
        choices=BACKGROUND_TYPE_CHOICES,
        default='transparent',
    )

    background_color = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    background_gradient = models.CharField(
        max_length=500,
        null=True,
        blank=True,
    )

    background_image = models.FileField(
        upload_to=theme_background_path,
        null=True,
        blank=True,
    )

    background_opacity = models.FloatField(
        default=1,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1),
        ],
    )

    background_overlay = models.FloatField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1),
        ],
    )

    background_size = models.CharField(
        max_length=30,
        choices=BACKGROUND_SIZE_CHOICES,
        default='cover',
    )

    background_position = models.CharField(
        max_length=30,
        choices=BACKGROUND_POSITION_CHOICES,
        default='center',
    )

    background_repeat = models.BooleanField(
        default=False,
    )

    backdrop_blur = models.PositiveIntegerField(
        default=0,
        help_text='Backdrop blur in pixels.',
    )

    class Meta:
        verbose_name = 'Theme Surface'
        verbose_name_plural = 'Theme Surfaces'
        permissions = ()

        constraints = [
            models.UniqueConstraint(
                fields=['theme', 'area'],
                name='unique_theme_surface_area',
            )
        ]

    class RESAAS:
        label_field = "area"
        crud = True

        routes = {
            'list': "add_theme_surface",
            'view': "view_theme_surface",
            'add': "add_theme_surface",
            'change': "change_theme_surface",
        }

        fields = {
            "background_image": {
                "accept": ".png,.jpg,.jpeg,.webp",
                "max_size": 5 * 1024 * 1024,
                "multiple": False,
            }
        }

    @property
    def background_value(self):
        if self.background_type == 'transparent':
            return 'transparent'

        if self.background_type == 'image':
            return self.background_image.url if self.background_image else None

        if self.background_type == 'gradient':
            return self.background_gradient

        if self.background_type == 'color':
            return self.background_color

        return None

    def to_dict(self):
        return {
            "id": str(self.id),
            "area": self.area,

            "background_type": self.background_type,
            "background_value": self.background_value,

            "background_color": self.background_color,
            "background_gradient": self.background_gradient,

            "background_image": (
                self.background_image.url
                if self.background_image
                else None
            ),

            "background_opacity": self.background_opacity,
            "background_overlay": self.background_overlay,

            "background_size": self.background_size,
            "background_position": self.background_position,
            "background_repeat": self.background_repeat,

            "backdrop_blur": self.backdrop_blur,
        }

    def __str__(self):
        return f'{self.theme} - {self.get_area_display()}'

