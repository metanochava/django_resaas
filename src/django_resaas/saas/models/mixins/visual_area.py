"""Mixins reutilizáveis para áreas visuais (header/footer) com fundo
cor/gradiente/imagem/transparente + cor de texto - mesmo formato já
usado por `login_background_*` em Entity/EntityType
(saas/models/entity.py / entity_type.py).

Diferença deliberada face a login_*: aqui TODOS os campos ficam
sempre `null=True` (mesmo em EntityType) - a cascata de resolução
(User -> Entity -> EntityType -> default) vive inteiramente em
saas/core/services/interface_config_service.py, não em defaults do
modelo. Login_* não é tocado (mantém o seu próprio padrão, já em
produção).

Campos escritos por extenso em cada mixin (sem geração dinâmica) para
seguir a convenção do resto do projeto - a duplicação entre
HeaderVisualFields/FooterVisualFields é deliberada.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

BACKGROUND_TYPE_CHOICES = [
    ("color", "Color"),
    ("gradient", "Gradient"),
    ("image", "Image"),
    ("transparent", "Transparent"),
]


def visual_area_upload_path(instance, file_name):
    return f"{instance._meta.model_name}/{instance.pk or 'new'}/{file_name}"


class HeaderVisualFields(models.Model):

    header_background_type = models.CharField(
        max_length=20,
        choices=BACKGROUND_TYPE_CHOICES,
        null=True,
        blank=True,
        default=None,
        help_text="Background type for the header. Null = inherit."
    )

    header_background_color = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default=None,
        help_text="Used when the background type is Color."
    )

    header_background_gradient = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        default=None,
        help_text=(
            "CSS gradient, e.g. linear-gradient(135deg, #1976d2, #26a69a). "
            "Used when the background type is Gradient."
        )
    )

    header_background_image = models.FileField(
        upload_to=visual_area_upload_path,
        null=True,
        blank=True,
        default=None,
        help_text="Used when the background type is Image."
    )

    header_background_overlay = models.FloatField(
        null=True,
        blank=True,
        default=None,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Dark overlay opacity (0-1), applied over image/gradient."
    )

    header_text_color = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default=None,
        help_text="Text color used over the header."
    )

    class Meta:
        abstract = True

    @property
    def header_background(self):
        if self.header_background_type == "transparent":
            return {"type": "transparent", "value": None}

        if self.header_background_type == "image":
            return (
                {"type": "image", "value": self.header_background_image.url}
                if self.header_background_image else None
            )

        if self.header_background_type == "gradient":
            return (
                {"type": "gradient", "value": self.header_background_gradient}
                if self.header_background_gradient else None
            )

        if self.header_background_type == "color":
            return (
                {"type": "color", "value": self.header_background_color}
                if self.header_background_color else None
            )

        return None

    @property
    def header_config(self):
        background = self.header_background

        if background is None:
            return None

        return {
            "background": background,
            "overlay": self.header_background_overlay,
            "text_color": self.header_text_color,
        }


class FooterVisualFields(models.Model):

    footer_background_type = models.CharField(
        max_length=20,
        choices=BACKGROUND_TYPE_CHOICES,
        null=True,
        blank=True,
        default=None,
        help_text="Background type for the footer. Null = inherit."
    )

    footer_background_color = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default=None,
        help_text="Used when the background type is Color."
    )

    footer_background_gradient = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        default=None,
        help_text=(
            "CSS gradient, e.g. linear-gradient(135deg, #1976d2, #26a69a). "
            "Used when the background type is Gradient."
        )
    )

    footer_background_image = models.FileField(
        upload_to=visual_area_upload_path,
        null=True,
        blank=True,
        default=None,
        help_text="Used when the background type is Image."
    )

    footer_background_overlay = models.FloatField(
        null=True,
        blank=True,
        default=None,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Dark overlay opacity (0-1), applied over image/gradient."
    )

    footer_text_color = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default=None,
        help_text="Text color used over the footer."
    )

    class Meta:
        abstract = True

    @property
    def footer_background(self):
        if self.footer_background_type == "transparent":
            return {"type": "transparent", "value": None}

        if self.footer_background_type == "image":
            return (
                {"type": "image", "value": self.footer_background_image.url}
                if self.footer_background_image else None
            )

        if self.footer_background_type == "gradient":
            return (
                {"type": "gradient", "value": self.footer_background_gradient}
                if self.footer_background_gradient else None
            )

        if self.footer_background_type == "color":
            return (
                {"type": "color", "value": self.footer_background_color}
                if self.footer_background_color else None
            )

        return None

    @property
    def footer_config(self):
        background = self.footer_background

        if background is None:
            return None

        return {
            "background": background,
            "overlay": self.footer_background_overlay,
            "text_color": self.footer_text_color,
        }
