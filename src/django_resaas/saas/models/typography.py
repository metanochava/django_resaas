from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from django_resaas.saas.core.base.models import TimeModel

# =========================================================
# TYPOGRAPHY
# =========================================================


class Typography(TimeModel):

    FONT_FAMILY_CHOICES = [
        ("Roboto", "Roboto"),
        ("Inter", "Inter"),
        ("Open Sans", "Open Sans"),
        ("Lato", "Lato"),
        ("Poppins", "Poppins"),
        ("Montserrat", "Montserrat"),
        ("Source Sans Pro", "Source Sans Pro"),
        ("Nunito", "Nunito"),
        ("Raleway", "Raleway"),
        ("Ubuntu", "Ubuntu"),
        ("Playfair Display", "Playfair Display"),
        ("Merriweather", "Merriweather"),
    ]

    MONOSPACE_CHOICES = [
        ("monospace", "Default Monospace"),
        ("Fira Code", "Fira Code"),
        ("JetBrains Mono", "JetBrains Mono"),
        ("Source Code Pro", "Source Code Pro"),
        ("Roboto Mono", "Roboto Mono"),
    ]

    name = models.CharField(max_length=100)

    font_family = models.CharField(
        max_length=100,
        choices=FONT_FAMILY_CHOICES,
        default="Roboto",
    )

    font_family_monospace = models.CharField(
        max_length=100,
        choices=MONOSPACE_CHOICES,
        default="monospace",
    )

    font_size_base = models.IntegerField(default=14)

    font_size_h1 = models.IntegerField(default=32)
    font_size_h2 = models.IntegerField(default=28)
    font_size_h3 = models.IntegerField(default=24)
    font_size_h4 = models.IntegerField(default=20)
    font_size_h5 = models.IntegerField(default=18)
    font_size_h6 = models.IntegerField(default=16)

    font_size_body = models.IntegerField(default=14)
    font_size_caption = models.IntegerField(default=12)
    font_size_small = models.IntegerField(default=11)

    font_weight_light = models.IntegerField(default=300)
    font_weight_normal = models.IntegerField(default=400)
    font_weight_medium = models.IntegerField(default=500)
    font_weight_bold = models.IntegerField(default=700)

    line_height = models.FloatField(default=1.5)
    letter_spacing = models.FloatField(default=0)

    uppercase_headings = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Typography"
        verbose_name_plural = "Typography"
        permissions = ()

    class RESAAS:
        label_field = "name"
        search_fields = ["name"]
        crud = True

        routes = {
            'list': "add_typography",
            'view': "view_typography",
            'add': "add_typography",
            'change': "change_typography",
        }

    def to_dict(self):
        return {
            "font_family": self.font_family,
            "font_family_monospace": self.font_family_monospace,

            "font_size_base": self.font_size_base,

            "font_size_h1": self.font_size_h1,
            "font_size_h2": self.font_size_h2,
            "font_size_h3": self.font_size_h3,
            "font_size_h4": self.font_size_h4,
            "font_size_h5": self.font_size_h5,
            "font_size_h6": self.font_size_h6,

            "font_size_body": self.font_size_body,
            "font_size_caption": self.font_size_caption,
            "font_size_small": self.font_size_small,

            "font_weight_light": self.font_weight_light,
            "font_weight_normal": self.font_weight_normal,
            "font_weight_medium": self.font_weight_medium,
            "font_weight_bold": self.font_weight_bold,

            "line_height": self.line_height,
            "letter_spacing": self.letter_spacing,

            "uppercase_headings": self.uppercase_headings,
        }

    def __str__(self):
        return self.name

# const font = typography.font_family

# const link = document.createElement("link")
# link.href = `https://fonts.googleapis.com/css2?family=${font.replace(" ", "+")}:wght@300;400;500;700&display=swap`
# link.rel = "stylesheet"

# document.head.appendChild(link)

# document.body.style.fontFamily = font