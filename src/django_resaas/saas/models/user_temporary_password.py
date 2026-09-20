import uuid

from django.conf import settings
from django.db import models


class UserTemporaryPassword(models.Model):
    """
    The TEMPORARY password of a user, while it is still temporary.

    User.password always holds the normal Django hash. This row exists only to
    let an authorised administrator read the temporary password back, and only
    until the user replaces it: it is HARD-deleted (not soft-deleted) the moment
    a definitive password is set, so nothing recoverable remains. A definitive
    password has no row here and can never be recovered.

    `encrypted` is Fernet ciphertext (core/utils/secret_box.py) - never the
    plaintext - and is emptied as soon as the password expires: after expiry it
    is never revealed again, an administrator can only issue a new one.
    The row's existence is what "must change password" means.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        "django_resaas.User",
        on_delete=models.CASCADE,
        related_name="temporary_password",
    )

    # the Entity in whose context it was issued (null: shell/commands) - lets
    # an administrator of THAT entity manage a user who has no membership yet
    entity = models.ForeignKey(
        "django_resaas.Entity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    encrypted = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User temporary password"
        verbose_name_plural = "User temporary passwords"
        permissions = ()

    def __str__(self):
        return f"temporary password of {self.user_id}"
