from django.db import models

from django_resaas.saas.core.base.models import TimeModel

# =========================================================
# ANIMATION SETTING
# =========================================================
#
# Modelo em falta: era importado (e usado) a partir de
# models/layout_setting.py por admin.py, os views de entity/entity_type
# e o signal que cria as settings por omissão de uma EntityType/Entity
# nova (core/signals/permissions.py), mas a classe nunca chegou a
# existir aqui nem em lado nenhum (nenhuma migration a referencia) -
# qualquer arranque da app rebentava em
# "ImportError: cannot import name 'AnimationSetting'". Criado agora
# num ficheiro próprio (um modelo por ficheiro, como Theme/
# ThemeSurface/Typography/LayoutSetting) em vez de dentro de
# layout_setting.py, de onde nunca devia ter sido importado.
#
# Os campos (e os seus choices) seguem exactamente o que
# quasar_resaas/components/engine/{BtnComponent,CardComponent}.vue já
# liam de `animation.button_animation`/`hover_style`/`card_animation`
# (comparações como `=== 'ripple'`/`=== 'pulse'`) - button_animation/
# hover_style/card_animation/modal_animation são por isso CharField
# com choices, não BooleanField.


class AnimationSetting(TimeModel):

    ANIMATION_SPEED_CHOICES = [
        ('slow', 'Slow'),
        ('normal', 'Normal'),
        ('fast', 'Fast'),
    ]

    PAGE_TRANSITION_CHOICES = [
        ('none', 'None'),
        ('fade', 'Fade'),
        ('slide-left', 'Slide Left'),
        ('slide-right', 'Slide Right'),
        ('slide-up', 'Slide Up'),
        ('slide-down', 'Slide Down'),
        ('scale', 'Scale'),
        ('zoom', 'Zoom'),
    ]

    BUTTON_ANIMATION_CHOICES = [
        ('none', 'None'),
        ('ripple', 'Ripple'),
        ('pulse', 'Pulse'),
        ('bounce', 'Bounce'),
        ('scale', 'Scale'),
    ]

    HOVER_STYLE_CHOICES = [
        ('none', 'None'),
        ('lift', 'Lift'),
        ('shadow', 'Shadow'),
        ('grow', 'Grow'),
        ('glow', 'Glow'),
    ]

    CARD_ANIMATION_CHOICES = [
        ('none', 'None'),
        ('fade', 'Fade'),
        ('slide-up', 'Slide Up'),
        ('zoom', 'Zoom'),
    ]

    MODAL_ANIMATION_CHOICES = [
        ('none', 'None'),
        ('scale', 'Scale'),
        ('fade', 'Fade'),
        ('slide-up', 'Slide Up'),
    ]

    name = models.CharField(
        max_length=100,
    )

    enable_animations = models.BooleanField(
        default=True,
    )

    animation_speed = models.CharField(
        max_length=20,
        choices=ANIMATION_SPEED_CHOICES,
        default='normal',
    )

    page_transition = models.CharField(
        max_length=20,
        choices=PAGE_TRANSITION_CHOICES,
        default='fade',
    )

    button_animation = models.CharField(
        max_length=20,
        choices=BUTTON_ANIMATION_CHOICES,
        default='ripple',
    )

    hover_effect = models.BooleanField(
        default=True,
    )

    hover_style = models.CharField(
        max_length=20,
        choices=HOVER_STYLE_CHOICES,
        default='lift',
    )

    card_animation = models.CharField(
        max_length=20,
        choices=CARD_ANIMATION_CHOICES,
        default='fade',
    )

    modal_animation = models.CharField(
        max_length=20,
        choices=MODAL_ANIMATION_CHOICES,
        default='scale',
    )

    class Meta:
        verbose_name = 'Animation Setting'
        verbose_name_plural = 'Animation Settings'
        permissions = ()

    class RESAAS:
        label_field = "name"
        search_fields = ["name"]
        crud = True

        routes = {
            'list': "add_animation_setting",
            'view': "view_animation_setting",
            'add': "add_animation_setting",
            'change': "change_animation_setting",
        }

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

    def __str__(self):
        return self.name
