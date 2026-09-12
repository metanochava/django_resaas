from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from django_resaas.saas.core.base.models import TimeModel


class Theme(TimeModel):
    name = models.CharField(max_length=100)

    # =========================================================
    # CORE COLORS
    # =========================================================

    primary = models.CharField(max_length=50, default="#1976D2")
    secondary = models.CharField(max_length=50, default="#26A69A")
    accent = models.CharField(max_length=50, default="#9C27B0")

    positive = models.CharField(max_length=50, default="#21BA45")
    negative = models.CharField(max_length=50, default="#C10015")
    warning = models.CharField(max_length=50, default="#F2C037")
    info = models.CharField(max_length=50, default="#31CCEC")

    dark = models.CharField(max_length=50, default="#1D1D1D")
    light = models.CharField(max_length=50, default="#FFFFFF")

    # =========================================================
    # BACKGROUND COLORS
    # =========================================================

    background = models.CharField(max_length=50, default="#F6F8F7")
    background_dark = models.CharField(max_length=50, default="#121212")

    page = models.CharField(max_length=50, default="#FFFFFF")
    card = models.CharField(max_length=50, default="#FFFFFF")

    # =========================================================
    # TEXT COLORS
    # =========================================================

    text_primary = models.CharField(max_length=50, default="#000000")
    text_secondary = models.CharField(max_length=50, default="#666666")
    text_muted = models.CharField(max_length=50, default="#9E9E9E")

    text_light = models.CharField(max_length=50, default="#FFFFFF")
    text_dark = models.CharField(max_length=50, default="#1D1D1D")
    text_link = models.CharField(max_length=50, default="#1976D2")

    # =========================================================
    # HEADER / FOOTER
    # =========================================================

    header = models.CharField(max_length=50, default="#1976D2")
    header_text = models.CharField(max_length=50, default="#FFFFFF")

    footer = models.CharField(max_length=50, default="#1976D2")
    footer_text = models.CharField(max_length=50, default="#FFFFFF")

    # =========================================================
    # SIDEBAR
    # =========================================================

    sidebar = models.CharField(max_length=50, default="#FFFFFF")
    sidebar_text = models.CharField(max_length=50, default="#333333")

    sidebar_active = models.CharField(max_length=50, default="#1976D2")
    sidebar_active_text = models.CharField(max_length=50, default="#FFFFFF")
    sidebar_hover = models.CharField(max_length=50, default="#F5F5F5")

    # =========================================================
    # BUTTONS
    # =========================================================

    button_primary = models.CharField(max_length=50, default="#1976D2")
    button_primary_text = models.CharField(max_length=50, default="#FFFFFF")

    button_secondary = models.CharField(max_length=50, default="#26A69A")
    button_secondary_text = models.CharField(max_length=50, default="#FFFFFF")

    button_outline = models.CharField(max_length=50, default="#1976D2")

    # =========================================================
    # INPUTS
    # =========================================================

    input_background = models.CharField(max_length=50, default="#FFFFFF")
    input_border = models.CharField(max_length=50, default="#CCCCCC")
    input_focus = models.CharField(max_length=50, default="#1976D2")

    # =========================================================
    # BORDER / DIVIDER
    # =========================================================

    border = models.CharField(max_length=50, default="#E0E0E0")
    divider = models.CharField(max_length=50, default="#EEEEEE")

    # =========================================================
    # GREY SCALE
    # =========================================================

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

    class RESAAS:
        label_field = "name"
        search_fields = ["name"]
        crud = True

        routes = {
            'list': "add_theme",
            'view': "view_theme",
            'add': "add_theme",
            'change': "change_theme",
        }

    def to_dict(self):
        return {
            "id": str(self.id),

            "name": self.name,

            "primary": self.primary,
            "secondary": self.secondary,
            "accent": self.accent,

            "positive": self.positive,
            "negative": self.negative,
            "warning": self.warning,
            "info": self.info,

            "dark": self.dark,
            "light": self.light,

            "background": self.background,
            "background_dark": self.background_dark,

            "page": self.page,
            "card": self.card,

            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
            "text_muted": self.text_muted,
            "text_light": self.text_light,
            "text_dark": self.text_dark,
            "text_link": self.text_link,

            "header": self.header,
            "header_text": self.header_text,

            "footer": self.footer,
            "footer_text": self.footer_text,

            "sidebar": self.sidebar,
            "sidebar_text": self.sidebar_text,
            "sidebar_active": self.sidebar_active,
            "sidebar_active_text": self.sidebar_active_text,
            "sidebar_hover": self.sidebar_hover,

            "button_primary": self.button_primary,
            "button_primary_text": self.button_primary_text,
            "button_secondary": self.button_secondary,
            "button_secondary_text": self.button_secondary_text,
            "button_outline": self.button_outline,

            "input_background": self.input_background,
            "input_border": self.input_border,
            "input_focus": self.input_focus,

            "border": self.border,
            "divider": self.divider,

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

            "surfaces": {
                surface.area: surface.to_dict()
                for surface in self.surfaces.all()
            },
        }

    def __str__(self):
        return self.name

