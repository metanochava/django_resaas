import uuid
from django.db import models
from django_resaas.core.base.models import TimeModel


class LayoutSetting(TimeModel):

    nome = models.CharField(max_length=100)

    # 🌗 tema
    dark_mode = models.BooleanField(default=False)

    # BOTÕES
    buttonDense = models.BooleanField(default=False)
    buttonRounded = models.BooleanField(default=False)
    buttonSquare = models.BooleanField(default=False)

    # INPUTS
    inputDense = models.BooleanField(default=False)
    inputRounded = models.BooleanField(default=False)
    inputSquare = models.BooleanField(default=False)


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


   # BORDER RADIUS GLOBAL
    border_radius = models.IntegerField(default=8)
    

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
      


class AnimationSetting(TimeModel):

    # =========================
    # GLOBAL
    # =========================

    nome = models.CharField(max_length=100)

    enable_animations = models.BooleanField(default=True)

    animation_speed = models.CharField(
        max_length=20,
        default="normal",
        choices=[
            ("slow", "Slow"),
            ("normal", "Normal"),
            ("fast", "Fast"),
        ]
    )

    # =========================
    # PAGE TRANSITIONS
    # =========================

    page_transition = models.CharField(
        max_length=50,
        default="fade",
        choices=[
            ("none", "None"),
            ("fade", "Fade"),
            ("slide-left", "Slide Left"),
            ("slide-right", "Slide Right"),
            ("slide-up", "Slide Up"),
            ("slide-down", "Slide Down"),
            ("scale", "Scale"),
            ("zoom", "Zoom"),
        ]
    )

    # =========================
    # BUTTON EFFECTS
    # =========================

    button_animation = models.CharField(
        max_length=50,
        default="ripple",
        choices=[
            ("none", "None"),
            ("ripple", "Ripple"),
            ("pulse", "Pulse"),
            ("bounce", "Bounce"),
            ("scale", "Scale"),
        ]
    )

    # =========================
    # HOVER EFFECTS
    # =========================

    hover_effect = models.BooleanField(default=True)

    hover_style = models.CharField(
        max_length=50,
        default="lift",
        choices=[
            ("none", "None"),
            ("lift", "Lift"),
            ("shadow", "Shadow"),
            ("grow", "Grow"),
            ("glow", "Glow"),
        ]
    )

    # =========================
    # CARD ANIMATIONS
    # =========================

    card_animation = models.CharField(
        max_length=50,
        default="fade",
        choices=[
            ("none", "None"),
            ("fade", "Fade"),
            ("slide-up", "Slide Up"),
            ("zoom", "Zoom"),
        ]
    )

    # =========================
    # MODAL ANIMATION
    # =========================

    modal_animation = models.CharField(
        max_length=50,
        default="scale",
        choices=[
            ("none", "None"),
            ("scale", "Scale"),
            ("fade", "Fade"),
            ("slide-up", "Slide Up"),
        ]
    )

    def to_dict(self):
        return {
            "enable_animations": self.enable_animations,
            "animation_speed": self.animation_speed,
            "page_transition": self.page_transition,
            "button_animation": self.button_animation,
            "hover_effect": self.hover_effect,
            "hover_style": self.hover_style,
            "card_animation": self.card_animation,
            "modal_animation": self.modal_animation,
        }

    class Meta:
        verbose_name = "Animation Setting"
        verbose_name_plural = "Animation Settings"

    def __str__(self):
        return self.nome