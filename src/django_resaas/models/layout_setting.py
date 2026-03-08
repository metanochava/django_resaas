import uuid
from django.db import models
from django_resaas.core.base.models import TimeModel


class LayoutSetting(TimeModel):

    nome = models.CharField(max_length=100)

    # 🌗 tema
    dark_mode = models.BooleanField(default=False)

    # 📏 densidade UI
    density = models.CharField(
        max_length=20,
        choices=[
            ("dense", "Dense"),
            ("normal", "Normal"),
            ("comfortable", "Comfortable")
        ],
        default="normal"
    )



    # 🌊 animações
    animations = models.BooleanField(default=True)

    # ========================
    # 🔘 BUTTON
    # ========================
    button_style = models.CharField(
        max_length=20,
        choices=[
            ("flat", "Flat"),
            ("outline", "Outline"),
            ("unelevated", "Unelevated"),
            ("push", "Push")
        ],
        default="unelevated"
    )

    button_dense = models.BooleanField(default=False)
    button_round = models.BooleanField(default=False)

    # ========================
    # 📝 INPUT
    # ========================
    input_style = models.CharField(
        max_length=20,
        choices=[
            ("outlined", "Outlined"),
            ("filled", "Filled"),
            ("standout", "Standout"),
        ],
        default="outlined"
    )

    input_dense = models.BooleanField(default=False)

    

    # ========================
    # 📂 SIDEBAR
    # ========================
    sidebar_mini = models.BooleanField(default=False)
    sidebar_width = models.IntegerField(default=260)

    # ========================
    # 📊 TOOLBAR
    # ========================
    toolbar_dense = models.BooleanField(default=False)
    toolbar_elevated = models.BooleanField(default=True)


    nome = models.CharField(max_length=100)

    # 🎨 botão
    button_style = models.CharField(
        max_length=20,
        choices=[
            ("flat", "Flat"),
            ("outline", "Outline"),
            ("unelevated", "Unelevated"),
            ("push", "Push"),
        ],
        default="unelevated"
    )

    # 📏 densidade
    dense = models.BooleanField(default=False)

    # 🔘 bordas
    rounded = models.BooleanField(default=False)
    square = models.BooleanField(default=False)

    # 🌊 ripple
    ripple = models.BooleanField(default=True)

    # 🧱 sombra
    elevated = models.BooleanField(default=True)

    # 📦 card style
    card_flat = models.BooleanField(default=False)
    card_bordered = models.BooleanField(default=False)


    # 📂 sidebar
    sidebar_mini = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'LayoutSetting'
        verbose_name_plural = 'LayoutSettings'
    
    def __str__(self):
        return self.nome

    def to_dict(self):

        return {

            "dark_mode": self.dark_mode,
            "density": self.density,
            "rounded": self.rounded,
            "square": self.square,
            "animations": self.animations,

            "button": {
                "style": self.button_style,
                "dense": self.button_dense,
                "round": self.button_round,
            },

            "input": {
                "style": self.input_style,
                "dense": self.input_dense,
            },

            "card": {
                "flat": self.card_flat,
                "bordered": self.card_bordered
            },

            "sidebar": {
                "mini": self.sidebar_mini,
                "width": self.sidebar_width
            },

            "toolbar": {
                "dense": self.toolbar_dense,
                "elevated": self.toolbar_elevated
            }
        }
      
