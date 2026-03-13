import uuid
from django.db import models
from django_resaas.core.base.models import TimeModel


class Theme(TimeModel):

    nome = models.CharField(max_length=100)

    # =========================
    # CORE COLORS (QUASAR)
    # =========================

    primary = models.CharField(max_length=50, default="#1976D2")
    secondary = models.CharField(max_length=50, default="#26A69A")
    accent = models.CharField(max_length=50, default="#9C27B0")

    positive = models.CharField(max_length=50, default="#21BA45")
    negative = models.CharField(max_length=50, default="#C10015")
    warning = models.CharField(max_length=50, default="#F2C037")
    info = models.CharField(max_length=50, default="#31CCEC")

    dark = models.CharField(max_length=50, default="#1D1D1D")
    light = models.CharField(max_length=50, default="#FFFFFF")

    # =========================
    # BACKGROUND COLORS
    # =========================

    background = models.CharField(max_length=50, default="#F6F8F7")
    background_dark = models.CharField(max_length=50, default="#121212")

    page = models.CharField(max_length=50, default="#FFFFFF")
    card = models.CharField(max_length=50, default="#FFFFFF")

    # =========================
    # TEXT COLORS
    # =========================

    text_primary = models.CharField(max_length=50, default="#000000")
    text_secondary = models.CharField(max_length=50, default="#666666")
    text_muted = models.CharField(max_length=50, default="#9E9E9E")

    text_light = models.CharField(max_length=50, default="#FFFFFF")
    text_dark = models.CharField(max_length=50, default="#1D1D1D")

    text_link = models.CharField(max_length=50, default="#1976D2")

    # =========================
    # HEADER / FOOTER
    # =========================

    header = models.CharField(max_length=50, default="#1976D2")
    header_text = models.CharField(max_length=50, default="#FFFFFF")

    footer = models.CharField(max_length=50, default="#1976D2")
    footer_text = models.CharField(max_length=50, default="#FFFFFF")

    # =========================
    # SIDEBAR
    # =========================

    sidebar = models.CharField(max_length=50, default="#FFFFFF")
    sidebar_text = models.CharField(max_length=50, default="#333333")

    sidebar_active = models.CharField(max_length=50, default="#1976D2")
    sidebar_active_text = models.CharField(max_length=50, default="#FFFFFF")

    sidebar_hover = models.CharField(max_length=50, default="#F5F5F5")

    # =========================
    # BUTTON COLORS
    # =========================

    button_primary = models.CharField(max_length=50, default="#1976D2")
    button_primary_text = models.CharField(max_length=50, default="#FFFFFF")

    button_secondary = models.CharField(max_length=50, default="#26A69A")
    button_secondary_text = models.CharField(max_length=50, default="#FFFFFF")

    button_outline = models.CharField(max_length=50, default="#1976D2")

    # =========================
    # INPUTS / FORM
    # =========================

    input_background = models.CharField(max_length=50, default="#FFFFFF")
    input_border = models.CharField(max_length=50, default="#CCCCCC")
    input_focus = models.CharField(max_length=50, default="#1976D2")

    # =========================
    # BORDER / DIVIDER
    # =========================

    border = models.CharField(max_length=50, default="#E0E0E0")
    divider = models.CharField(max_length=50, default="#EEEEEE")

    # =========================
    # GREY SCALE
    # =========================

    grey = models.CharField(max_length=50, default="#CDCDCD")
    grey_1 = models.CharField(max_length=50, default="#FAFAFA")
    grey_2 = models.CharField(max_length=50, default="#F5F5F5")
    grey_3 = models.CharField(max_length=50, default="#EEEEEE")
    grey_4 = models.CharField(max_length=50, default="#E0E0E0")
    grey_5 = models.CharField(max_length=50, default="#BDBDBD")
    grey_6 = models.CharField(max_length=50, default="#9E9E9E")
    grey_7 = models.CharField(max_length=50, default="#757575")
    grey_8 = models.CharField(max_length=50, default="#616161")
    grey_9 = models.CharField(max_length=50, default="#424242")

    class Meta:
        verbose_name = 'Theme'
        verbose_name_plural = 'Themes'
        permissions = ()

    def to_dict(self):
        return {

            # CORE COLORS
            "primary": self.primary,
            "secondary": self.secondary,
            "accent": self.accent,
            "positive": self.positive,
            "negative": self.negative,
            "warning": self.warning,
            "info": self.info,
            "dark": self.dark,
            "light": self.light,

            # BACKGROUNDS
            "background": self.background,
            "background_dark": self.background_dark,
            "page": self.page,
            "card": self.card,

            # TEXT
            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
            "text_muted": self.text_muted,
            "text_light": self.text_light,
            "text_dark": self.text_dark,
            "text_link": self.text_link,

            # HEADER / FOOTER
            "header": self.header,
            "header_text": self.header_text,
            "footer": self.footer,
            "footer_text": self.footer_text,

            # SIDEBAR
            "sidebar": self.sidebar,
            "sidebar_text": self.sidebar_text,
            "sidebar_active": self.sidebar_active,
            "sidebar_active_text": self.sidebar_active_text,
            "sidebar_hover": self.sidebar_hover,

            # BUTTONS
            "button_primary": self.button_primary,
            "button_primary_text": self.button_primary_text,
            "button_secondary": self.button_secondary,
            "button_secondary_text": self.button_secondary_text,
            "button_outline": self.button_outline,

            # INPUT
            "input_background": self.input_background,
            "input_border": self.input_border,
            "input_focus": self.input_focus,

            # BORDERS
            "border": self.border,
            "divider": self.divider,

            # GREY SCALE
            "grey": self.grey,
            "grey_1": self.grey_1,
            "grey_2": self.grey_2,
            "grey_3": self.grey_3,
            "grey_4": self.grey_4,
            "grey_5": self.grey_5,
            "grey_6": self.grey_6,
            "grey_7": self.grey_7,
            "grey_8": self.grey_8,
            "grey_9": self.grey_9,
        }

    def __str__(self):
        return self.nome





class Typography(TimeModel):
    nome = models.CharField(max_length=100)

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

    # FONT FAMILY
    font_family = models.CharField(
        max_length=100,
        choices=FONT_FAMILY_CHOICES,
        default="Roboto"
    )

    font_family_monospace = models.CharField(
        max_length=100,
        choices=MONOSPACE_CHOICES,
        default="monospace"
    )

    # BASE SIZE
    font_size_base = models.IntegerField(default=14)

    # HEADINGS
    font_size_h1 = models.IntegerField(default=32)
    font_size_h2 = models.IntegerField(default=28)
    font_size_h3 = models.IntegerField(default=24)
    font_size_h4 = models.IntegerField(default=20)
    font_size_h5 = models.IntegerField(default=18)
    font_size_h6 = models.IntegerField(default=16)

    # BODY
    font_size_body = models.IntegerField(default=14)
    font_size_caption = models.IntegerField(default=12)
    font_size_small = models.IntegerField(default=11)

    # WEIGHTS
    font_weight_light = models.IntegerField(default=300)
    font_weight_normal = models.IntegerField(default=400)
    font_weight_medium = models.IntegerField(default=500)
    font_weight_bold = models.IntegerField(default=700)

    # SPACING
    line_height = models.FloatField(default=1.5)
    letter_spacing = models.FloatField(default=0)

    # TEXT TRANSFORM
    uppercase_headings = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Typography"
        verbose_name_plural = "Typography"

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

            "uppercase_headings": self.uppercase_headings
        }

    def __str__(self):
        return self.nome



# const font = typography.font_family

# const link = document.createElement("link")
# link.href = `https://fonts.googleapis.com/css2?family=${font.replace(" ", "+")}:wght@300;400;500;700&display=swap`
# link.rel = "stylesheet"

# document.head.appendChild(link)

# document.body.style.fontFamily = font