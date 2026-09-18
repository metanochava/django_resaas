import uuid
from datetime import date
from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django_resaas.saas.core.base.models import TimeModel
from django_resaas.saas.core.base.mixins.address import AddressMixin

def person_photo_path(instance,file_name):
    return f"images/persons/{instance.id}/{file_name}"

class Person(AddressMixin,TimeModel):
    GENDER_CHOICES=[("M","Masculine"),("F","Feminine"),("O","Others")]
    MARITAL_STATUS_CHOICES=[("single","Single"),("married","Married"),("divorced","Divorced"),("widowed","Widowed"),("other","Other")]

    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user=models.OneToOneField("django_resaas.User",on_delete=models.CASCADE,related_name="person",null=True,blank=True)

    name=models.CharField(max_length=100,null=True)
    middle_name=models.CharField(max_length=100,null=True,blank=True)
    surname=models.CharField(max_length=100,null=True)
    full_name=models.CharField(max_length=300,null=True,blank=True,editable=False)
    preferred_name=models.CharField(max_length=150,null=True,blank=True)

    gender=models.CharField(max_length=1,choices=GENDER_CHOICES,null=True,blank=True)
    date_of_birth=models.DateField(null=True,blank=True)
    marital_status=models.CharField(max_length=20,choices=MARITAL_STATUS_CHOICES,null=True,blank=True)

    nationality=models.CharField(max_length=100,null=True,blank=True)
    country_of_birth=models.CharField(max_length=100,null=True,blank=True)
    place_of_birth=models.CharField(max_length=150,null=True,blank=True)

    photo=models.ImageField(upload_to=person_photo_path,null=True,blank=True)

    email=models.EmailField(null=True,blank=True,unique=True)
    secondary_email=models.EmailField(null=True,blank=True)
    phone=models.CharField(max_length=30,null=True,blank=True)
    alternative_phone=models.CharField(max_length=30,null=True,blank=True)

    occupation=models.CharField(max_length=150,null=True,blank=True)
    preferred_language=models.CharField(max_length=10,null=True,blank=True)
    timezone=models.CharField(max_length=50,null=True,blank=True)

    documents=GenericRelation("django_resaas.Document")

    def save(self,*args,**kwargs):
        self.full_name=" ".join(x.strip() for x in (self.name,self.middle_name,self.surname) if x and x.strip()) or None
        if self.email:self.email=self.email.strip().lower()
        if self.secondary_email:self.secondary_email=self.secondary_email.strip().lower()
        super().save(*args,**kwargs)

    @property
    def age(self):
        if not self.date_of_birth:return None
        today=date.today()
        return today.year-self.date_of_birth.year-((today.month,today.day)<(self.date_of_birth.month,self.date_of_birth.day))

    def __str__(self):
        return self.preferred_name or self.full_name or self.name or ""

    class Meta:
        verbose_name="Person"
        verbose_name_plural="Persons"
        ordering=["name"]
        indexes=[models.Index(fields=["name"]),models.Index(fields=["surname"]),models.Index(fields=["email"]),models.Index(fields=["phone"])]

    class RESAAS:
        label_field="full_name"
        search_fields=["name","middle_name","surname","full_name","preferred_name","email","phone"]
        crud=True
        routes={"list":"list_person","view":"view_person","add":"add_person","change":"change_person"}