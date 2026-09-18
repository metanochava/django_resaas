import uuid
from django.db import models
from django_resaas.saas.core.base.models import TimeModel

class PersonContact(TimeModel):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    person=models.ForeignKey("django_resaas.Person",on_delete=models.CASCADE,related_name="contacts")
    name=models.CharField(max_length=200)
    relationship=models.CharField(max_length=100,null=True,blank=True)
    phone=models.CharField(max_length=30,null=True,blank=True)
    alternative_phone=models.CharField(max_length=30,null=True,blank=True)
    email=models.EmailField(null=True,blank=True)
    is_primary=models.BooleanField(default=False)
    is_emergency=models.BooleanField(default=False)
    notes=models.TextField(null=True,blank=True)

    def save(self,*args,**kwargs):
        if self.email:self.email=self.email.strip().lower()
        if self.is_primary:PersonContact.objects.filter(person=self.person,is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args,**kwargs)

    def __str__(self):
        return f"{self.name} ({self.relationship})" if self.relationship else self.name

    class Meta:
        verbose_name="Person Contact"
        verbose_name_plural="Person Contacts"
        ordering=["-is_primary","-is_emergency","name"]
        indexes=[models.Index(fields=["person","is_primary"]),models.Index(fields=["person","is_emergency"])]

    class RESAAS:
        label_field="name"
        search_fields=["name","relationship","phone","email"]
        crud=True