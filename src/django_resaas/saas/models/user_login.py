import uuid
from django.db import models
from django_resaas.saas.models.user import User
from django_resaas.saas.core.base.models import TimeModel

class UserLogin(TimeModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    dispositivo = models.TextField(null=True)
    mobile = models.CharField(max_length=100, null=True)
    info = models.TextField(null=True)
    local_lat = models.CharField(max_length=100, null=True)
    local_lon = models.CharField(max_length=100, null=True)
    local_name = models.CharField(max_length=100, null=True)
   
    is_blocked = models.BooleanField(default=False)

    # jti of the refresh token issued by this sign-in: the session's id (the
    # tokens' "sid" claim). It never changes, even when the refresh rotates.
    token_jti = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    # jti of the session's CURRENT refresh token: each refresh rotates it
    # (core/services/session_service.rotated). The session is active while
    # this token is outstanding, not blacklisted and not expired. Null on
    # sessions from before rotation: their current token is token_jti.
    current_jti = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    # sessions started from one another by single sign-on, across the domains
    # of one browser (core/services/sso_service.py): signing out ends them
    # together. Null for a session no single sign-on touched.
    sso_family = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        permissions = ()

    class RESAAS:
        label_field = "user.username"
        route="view_entity"

    def __str__(self):
        return self.dispositivo or ''
