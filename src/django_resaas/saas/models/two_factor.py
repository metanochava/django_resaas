import uuid

from django.db import models


class UserTwoFactor(models.Model):
    """
    The TOTP second factor of one user.

    `secret_encrypted` is Fernet ciphertext (core/utils/secret_box.py) - the
    TOTP secret is never stored in clear. `confirmed_at` is null while the
    enrolment is only PENDING (secret issued, first code not yet proven); the
    factor counts only once confirmed. Recovery codes are stored as keyed
    hashes and removed when used, so a code works exactly once.
    Plain model (not soft-deleted): disabling the factor really deletes it.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        "django_resaas.User",
        on_delete=models.CASCADE,
        related_name="two_factor",
    )

    secret_encrypted = models.TextField()
    confirmed_at = models.DateTimeField(null=True, blank=True)

    # time step of the last accepted code: a code (and its neighbours) can
    # never be replayed
    last_used_step = models.BigIntegerField(default=0)

    recovery_hashes = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User two-factor"
        verbose_name_plural = "User two-factor"
        permissions = ()

    @property
    def active(self):
        return self.confirmed_at is not None

    def __str__(self):
        return f"two-factor of {self.user_id}"
