from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)

from rest_framework_simplejwt.tokens import RefreshToken

from django_resaas.saas.core.base.models import TimeModel


# =========================================================
# USER MANAGER
# =========================================================


class UserManager(BaseUserManager):

    def create_user(
        self,
        username,
        email,
        password=None,
        mobile=None
    ):
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            mobile=mobile
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(
        self,
        username,
        email,
        password=None
    ):
        if password is None:
            raise TypeError(
                'Password should not be none'
            )

        user = self.create_user(
            username=username,
            email=email,
            password=password
        )

        user.is_superuser = True
        user.is_verified_email = True
        user.is_staff = True
        user.is_active = True

        user.save(using=self._db)

        return user


# =========================================================
# AUTH PROVIDERS
# =========================================================


AUTH_PROVIDERS = (
    ('email', 'email'),
    ('facebook', 'facebook'),
    ('google', 'google'),
    ('twitter', 'twitter'),
    ('mobile', 'mobile'),
)


# =========================================================
# UPLOAD PATH
# =========================================================


def profile_image_path(instance, file_name):
    return f'images/users/{instance.id}/{file_name}'


# =========================================================
# USER
# =========================================================


class User(
    AbstractBaseUser,
    PermissionsMixin,
    TimeModel
):

    # =====================================================
    # REMOVE DEFAULT DJANGO GROUPS / PERMISSIONS
    # =====================================================

    groups = None
    user_permissions = None

    # =====================================================
    # PROFILE
    # =====================================================

    profile = models.ImageField(
        default='user.png',
        upload_to=profile_image_path,
        null=True,
        blank=True
    )

    username = models.CharField(
        max_length=255
    )

    first_name = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    last_name = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    # =====================================================
    # CONTACT
    # =====================================================

    mobile = models.CharField(
        max_length=55,
        null=True,
        unique=True,
        blank=True,
        default=None
    )

    email = models.EmailField(
        max_length=255,
        null=True,
        unique=True,
        blank=True,
        default=None
    )

    # =====================================================
    # VERIFICATION
    # =====================================================

    is_verified_mobile = models.BooleanField(
        default=False
    )

    is_verified_email = models.BooleanField(
        default=False
    )

    counter = models.IntegerField(
        default=0
    )

    # =====================================================
    # LANGUAGE
    # =====================================================

    language = models.ForeignKey(
        'django_resaas.Language',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # =====================================================
    # PERSONAL UI OVERRIDES
    #
    # NULL = herdar da Entity.
    # Se a Entity também não definir, herdar do EntityType.
    #
    # Prioridade:
    #
    # User > Entity > EntityType
    #
    # =====================================================

    theme = models.ForeignKey(
        'django_resaas.Theme',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text=(
            'Personal theme override. '
            'Leave empty to inherit from the entity.'
        )
    )

    layout_settings = models.ForeignKey(
        'django_resaas.LayoutSetting',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text=(
            'Personal layout configuration override. '
            'Leave empty to inherit from the entity.'
        )
    )

    typography = models.ForeignKey(
        'django_resaas.Typography',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text=(
            'Personal typography override. '
            'Leave empty to inherit from the entity.'
        )
    )

    animation_settings = models.ForeignKey(
        'django_resaas.AnimationSetting',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text=(
            'Personal animation configuration override. '
            'Leave empty to inherit from the entity.'
        )
    )

    # =====================================================
    # STATUS
    # =====================================================

    is_active = models.BooleanField(
        default=True
    )

    is_staff = models.BooleanField(
        default=False
    )

    # =====================================================
    # AUTHENTICATION
    # =====================================================

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = [
        'username'
    ]

    objects = UserManager()

    # =====================================================
    # META
    # =====================================================

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        permissions = ()

    # =====================================================
    # RESAAS
    # =====================================================

    class RESAAS:

        label_field = 'username'

        crud = True

        routes = {
            'list': 'add_user',
            'view': 'view_user',
            'add': 'add_user',
            'change': 'change_user'
        }

        fields = {

            'profile': {
                'accept': '.png,.jpg,.jpeg,.webp',
                'max_size': 2 * 1024 * 1024,
                'multiple': False
            }

        }

    # =====================================================
    # SAVE
    # =====================================================

    def save(self, *args, **kwargs):

        if self.email == '':
            self.email = None

        if self.mobile == '':
            self.mobile = None

        super().save(*args, **kwargs)

    # =====================================================
    # EFFECTIVE THEME
    #
    # User
    #   ↓
    # Entity
    #   ↓
    # EntityType
    # =====================================================

    def get_effective_theme(
        self,
        entity=None
    ):

        if self.theme:
            return self.theme

        if entity:

            if getattr(
                entity,
                'theme',
                None
            ):
                return entity.theme

            entity_type = getattr(
                entity,
                'entity_type',
                None
            )

            if (
                entity_type
                and getattr(
                    entity_type,
                    'theme',
                    None
                )
            ):
                return entity_type.theme

        return None

    # =====================================================
    # EFFECTIVE LAYOUT
    # =====================================================

    def get_effective_layout(
        self,
        entity=None
    ):

        if self.layout_settings:
            return self.layout_settings

        if entity:

            if getattr(
                entity,
                'layout_settings',
                None
            ):
                return entity.layout_settings

            entity_type = getattr(
                entity,
                'entity_type',
                None
            )

            if (
                entity_type
                and getattr(
                    entity_type,
                    'layout_settings',
                    None
                )
            ):
                return entity_type.layout_settings

        return None

    # =====================================================
    # EFFECTIVE TYPOGRAPHY
    # =====================================================

    def get_effective_typography(
        self,
        entity=None
    ):

        if self.typography:
            return self.typography

        if entity:

            if getattr(
                entity,
                'typography',
                None
            ):
                return entity.typography

            entity_type = getattr(
                entity,
                'entity_type',
                None
            )

            if (
                entity_type
                and getattr(
                    entity_type,
                    'typography',
                    None
                )
            ):
                return entity_type.typography

        return None

    # =====================================================
    # EFFECTIVE ANIMATION
    # =====================================================

    def get_effective_animation(
        self,
        entity=None
    ):

        if self.animation_settings:
            return self.animation_settings

        if entity:

            if getattr(
                entity,
                'animation_settings',
                None
            ):
                return entity.animation_settings

            entity_type = getattr(
                entity,
                'entity_type',
                None
            )

            if (
                entity_type
                and getattr(
                    entity_type,
                    'animation_settings',
                    None
                )
            ):
                return entity_type.animation_settings

        return None

    # =====================================================
    # EFFECTIVE UI CONFIG
    # =====================================================

    def get_ui_config(
        self,
        entity=None
    ):

        theme = self.get_effective_theme(
            entity
        )

        layout = self.get_effective_layout(
            entity
        )

        typography = (
            self.get_effective_typography(
                entity
            )
        )

        animation = (
            self.get_effective_animation(
                entity
            )
        )

        return {

            'theme': (
                theme.to_dict()
                if (
                    theme
                    and hasattr(
                        theme,
                        'to_dict'
                    )
                )
                else None
            ),

            'layout': (
                layout.to_dict()
                if (
                    layout
                    and hasattr(
                        layout,
                        'to_dict'
                    )
                )
                else None
            ),

            'typography': (
                typography.to_dict()
                if (
                    typography
                    and hasattr(
                        typography,
                        'to_dict'
                    )
                )
                else None
            ),

            'animation': (
                animation.to_dict()
                if (
                    animation
                    and hasattr(
                        animation,
                        'to_dict'
                    )
                )
                else None
            )

        }

    # =====================================================
    # UI SOURCES
    #
    # Útil para o frontend saber de onde veio cada
    # configuração efectiva.
    # =====================================================

    def get_ui_sources(
        self,
        entity=None
    ):

        entity_type = (
            getattr(
                entity,
                'entity_type',
                None
            )
            if entity
            else None
        )

        def source(
            user_value,
            entity_field
        ):

            if user_value:
                return 'user'

            if (
                entity
                and getattr(
                    entity,
                    entity_field,
                    None
                )
            ):
                return 'entity'

            if (
                entity_type
                and getattr(
                    entity_type,
                    entity_field,
                    None
                )
            ):
                return 'entity_type'

            return None

        return {

            'theme': source(
                self.theme,
                'theme'
            ),

            'layout': source(
                self.layout_settings,
                'layout_settings'
            ),

            'typography': source(
                self.typography,
                'typography'
            ),

            'animation': source(
                self.animation_settings,
                'animation_settings'
            )

        }

    # =====================================================
    # COMPLETE UI
    # =====================================================

    def get_complete_ui_config(
        self,
        entity=None
    ):

        return {
            'config': self.get_ui_config(
                entity
            ),

            'sources': self.get_ui_sources(
                entity
            )
        }

    # =====================================================
    # TOKENS
    # =====================================================

    def tokens(self):

        refresh = RefreshToken.for_user(
            self
        )

        return {
            'refresh': str(refresh),
            'access': str(
                refresh.access_token
            )
        }

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):

        return (
            self.username
            or self.email
            or str(self.pk)
        )