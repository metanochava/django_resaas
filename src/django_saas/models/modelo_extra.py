from django.db import models
from django_saas.core.base.models import TimeModel
from django_saas.core.utils import guess_name


class ModeloExtra(TimeModel):
    modelo = models.CharField(max_length=100, null=True)
    icon = models.CharField(max_length=100, null=True)
    method = models.CharField(max_length=50, null=True)
    permission = models.CharField(max_length=100, null=True)
    details = models.BooleanField(default=False)
    url = models.CharField(max_length=300, null=True)

    class Meta:
        permissions = ()

    def __str__(self):
        # return guess_name(self)
        return self.modelo


# class ModeloExtra(TimeModel):
#     modelo = models.CharField(max_length=100, null=True)

#     method = models.CharField(max_length=50, null=True)
#     url = models.CharField(max_length=300, null=True)

#     # 🔥 UI
#     details = models.CharField(max_length=200, null=True, blank=True)
#     icon = models.CharField(max_length=100, null=True, blank=True)
#     color = models.CharField(max_length=50, null=True, blank=True)

#     # 🔐 segurança
#     permission = models.CharField(max_length=100, null=True, blank=True)

#     # ⚠️ UX
#     confirm = models.BooleanField(default=False)
#     confirm_message = models.CharField(max_length=200, null=True, blank=True)

#     success_message = models.CharField(max_length=200, null=True, blank=True)
#     error_message = models.CharField(max_length=200, null=True, blank=True)

#     class Meta:
#         permissions = ()

#     def __str__(self):
#         return guess_name(self)

