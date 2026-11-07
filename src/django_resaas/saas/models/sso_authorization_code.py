import uuid

from django.db import models


class SsoAuthorizationCode(models.Model):
    """
    A single-use code that carries a signed-in session from one frontend
    domain to another (single sign-on between the domains a deployment
    serves). See core/services/sso_service.py.

    Only a keyed hash of the code is stored. The code lives for seconds, is
    bound to the `redirect_uri` it was issued for and to the PKCE
    `code_challenge` (S256) of whoever asked for it, and works once:
    `used_at` is set when it is redeemed.
    Plain model (not soft-deleted): a spent or expired code has no further use.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        "django_resaas.User",
        on_delete=models.CASCADE,
        related_name="sso_codes",
    )

    code_hash = models.CharField(max_length=64, unique=True)
    redirect_uri = models.CharField(max_length=500)
    code_challenge = models.CharField(max_length=128)

    # the session (refresh token jti) the code was issued from
    source_jti = models.CharField(max_length=64, blank=True, default="")

    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "SSO authorization code"
        verbose_name_plural = "SSO authorization codes"
        permissions = ()

    def __str__(self):
        return f"sso code of {self.user_id}"
