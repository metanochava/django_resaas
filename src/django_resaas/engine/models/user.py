import uuid

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from rest_framework_simplejwt.tokens import RefreshToken
from django_resaas.engine.models.person import Person
from django_resaas.engine.core.base.models import TimeModel
from django_resaas.engine.models.group import Group
from django.contrib.auth.models import Permission


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, mobile=None):
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            mobile=mobile
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, email, password=None):
        if password is None:
            raise TypeError('Password should not be none')

        user = self.create_user(username, email, password)
        user.is_superuser = True
        user.is_verified = True
        user.is_staff = True
        user.save()
        return user


AUTH_PROVIDERS = (
    ('email', 'email'),
    ('facebook', 'facebook'),
    ('google', 'google'),
    ('twitter', 'twitter'),
    ('mobile', 'maobile')
)


def profile_image_path(instance, file_name):
    return f'images/users/{instance.id}/{file_name}'


class User(AbstractBaseUser, PermissionsMixin, TimeModel):

    # 🔥 remove groups padrão
    groups = None

    # 🔥 remove user_permissions também (opcional)
    user_permissions = None


    profile = models.ImageField(
        default='user.png',
        upload_to=profile_image_path,
        null=True,
        blank=True
    )

    username = models.CharField(max_length=255, unique=False)
    first_name = models.CharField(max_length=255, unique=False, null=True, blank=True)
    last_name = models.CharField(max_length=255, unique=False, null=True, blank=True)

    mobile = models.CharField(
        max_length=55,
        null=True,
        unique=True,
        blank=True,
        default=None
    )
    is_verified_mobile = models.BooleanField(default=False)
    counter = models.IntegerField(default=0)
    email = models.EmailField(
        max_length=255,
        null=True,
        unique=True,
        blank=True,
        default=None
    )

    language = models.ForeignKey(
        "django_resaas.Language",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )



    is_verified_email = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)




    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = UserManager()

    def save(self, *args, **kwargs):
        if self.email == '':
            self.email = None
        if self.mobile == '':
            self.mobile = None
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        permissions = ()


    class RESAAS:
        label_field = "username"
        
        crud = True
        routes={
            'list': "add_user",
            'view': "view_user",
            'add': "add_user",
            'change': "change_user"
        }

    def __str__(self):
        return self.username

    def tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }



