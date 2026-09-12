from django.db import models

from django_resaas.saas.core.base.models import TimeModel


class LayoutSetting(TimeModel):

    LOGIN_POSITION_CHOICES = [
        ('top-left', 'Top Left'),
        ('top-right', 'Top Right'),
        ('center', 'Center'),
        ('bottom-left', 'Bottom Left'),
        ('bottom-right', 'Bottom Right'),
    ]

    SIDEBAR_POSITION_CHOICES = [
        ('left', 'Left'),
        ('right', 'Right'),
    ]

    CONTENT_WIDTH_CHOICES = [
        ('fluid', 'Fluid'),
        ('boxed', 'Boxed'),
    ]

    HEADER_POSITION_CHOICES = [
        ('static', 'Static'),
        ('fixed', 'Fixed'),
        ('sticky', 'Sticky'),
    ]

    FOOTER_POSITION_CHOICES = [
        ('static', 'Static'),
        ('fixed', 'Fixed'),
    ]

    name = models.CharField(
        max_length=100,
    )

    # =========================================================
    # DIRECTION
    # =========================================================

    menu_rtl = models.BooleanField(
        default=False,
    )

    # =========================================================
    # GENERAL DISPLAY
    # =========================================================

    display_logo = models.BooleanField(
        default=True,
    )

    display_logo_login = models.BooleanField(
        default=True,
    )

    display_bar = models.BooleanField(
        default=True,
    )

    display_qr = models.BooleanField(
        default=True,
    )

    # =========================================================
    # LOGIN
    # =========================================================

    login_position = models.CharField(
        max_length=30,
        choices=LOGIN_POSITION_CHOICES,
        default='center',
    )

    # =========================================================
    # SIDEBAR
    # =========================================================

    sidebar_position = models.CharField(
        max_length=10,
        choices=SIDEBAR_POSITION_CHOICES,
        default='left',
    )

    sidebar_width = models.PositiveIntegerField(
        default=260,
    )

    sidebar_mini_width = models.PositiveIntegerField(
        default=70,
    )

    sidebar_mini = models.BooleanField(
        default=False,
    )

    sidebar_overlay = models.BooleanField(
        default=False,
    )

    sidebar_persistent = models.BooleanField(
        default=True,
    )

    # =========================================================
    # HEADER
    # =========================================================

    display_header = models.BooleanField(
        default=True,
    )

    header_position = models.CharField(
        max_length=20,
        choices=HEADER_POSITION_CHOICES,
        default='fixed',
    )

    header_height = models.PositiveIntegerField(
        default=50,
    )

    # =========================================================
    # FOOTER
    # =========================================================

    display_footer = models.BooleanField(
        default=True,
    )

    footer_position = models.CharField(
        max_length=20,
        choices=FOOTER_POSITION_CHOICES,
        default='static',
    )

    footer_height = models.PositiveIntegerField(
        default=50,
    )

    # =========================================================
    # CONTENT
    # =========================================================

    content_width = models.CharField(
        max_length=20,
        choices=CONTENT_WIDTH_CHOICES,
        default='fluid',
    )

    content_max_width = models.PositiveIntegerField(
        default=1440,
    )

    page_padding = models.PositiveIntegerField(
        default=16,
    )

    # =========================================================
    # COMPONENTS
    # =========================================================

    rounded = models.BooleanField(
        default=True,
    )

    dense = models.BooleanField(
        default=False,
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:
        verbose_name = 'Layout Setting'
        verbose_name_plural = 'Layout Settings'
        permissions = ()

    class RESAAS:
        label_field = "name"
        search_fields = ["name"]
        crud = True

        routes = {
            'list': "add_layout_setting",
            'view': "view_layout_setting",
            'add': "add_layout_setting",
            'change': "change_layout_setting",
        }

    def to_dict(self):
        return {
            "menu_rtl": self.menu_rtl,

            "display_logo": self.display_logo,
            "display_logo_login": self.display_logo_login,
            "display_bar": self.display_bar,
            "display_qr": self.display_qr,

            "login_position": self.login_position,

            "sidebar": {
                "position": self.sidebar_position,
                "width": self.sidebar_width,
                "mini_width": self.sidebar_mini_width,
                "mini": self.sidebar_mini,
                "overlay": self.sidebar_overlay,
                "persistent": self.sidebar_persistent,
            },

            "header": {
                "display": self.display_header,
                "position": self.header_position,
                "height": self.header_height,
            },

            "footer": {
                "display": self.display_footer,
                "position": self.footer_position,
                "height": self.footer_height,
            },

            "content": {
                "width": self.content_width,
                "max_width": self.content_max_width,
                "padding": self.page_padding,
            },

            "rounded": self.rounded,
            "dense": self.dense,
        }

    def __str__(self):
        return self.name