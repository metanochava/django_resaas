from django.db import models

from django_resaas.saas.core.base.models import BaseModel


class Product(BaseModel):
    """
    Deliberately tiny - the point of this app is to demonstrate the
    framework's own conventions (multi-tenancy, soft delete, RESAAS schema),
    not to be a realistic product catalog.
    """

    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["-created_at"]

    class RESAAS:
        label_field = "name"
        search_fields = ["name", "sku"]
        crud = True
        icon = "mdi-package-variant"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# The framework's own test domain. Neutral models with the shapes the core's
# tests need (a relation to Person, a self relation, a relation previewed
# through another model, every common field type). The framework must not
# depend on a business module (e.g. HR) to test its own mechanisms.
# ---------------------------------------------------------------------------


class Category(BaseModel):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "categories"

    class RESAAS:
        label_field = "name"
        search_fields = ["name", "code"]
        crud = True

    def __str__(self):
        return self.name


class Member(BaseModel):
    KIND_CHOICES = [("staff", "Staff"), ("volunteer", "Volunteer")]

    person = models.ForeignKey("django_resaas.Person", on_delete=models.CASCADE, related_name="demo_members")
    manager = models.ForeignKey("demo.Member", null=True, blank=True, on_delete=models.SET_NULL, related_name="team")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="members")
    code = models.CharField(max_length=50, blank=True, db_index=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, null=True, blank=True)
    work_email = models.EmailField(null=True, blank=True)
    joined_on = models.DateField()

    class Meta:
        ordering = ["code"]

    class RESAAS:
        label_field = "code"
        # relation pickers show a Member as a card, through its Person
        preview = {
            "title": "person__full_name",
            "subtitle": ["code", "work_email"],
            "avatar": "person__photo",
            "meta": ["category__name"],
        }
        search_fields = ["code", "person__name", "person__surname", "person__full_name"]
        crud = True
        routes = {"list": "list_member", "view": "view_member", "add": "add_member", "change": "change_member"}

    def __str__(self):
        return self.code or str(self.person)


class Rate(BaseModel):
    TYPE_CHOICES = [("earning", "Earning"), ("deduction", "Deduction")]
    CALCULATION_CHOICES = [("fixed", "Fixed"), ("percentage", "Percentage")]

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50)
    rate_type = models.CharField(max_length=25, choices=TYPE_CHOICES)
    calculation_type = models.CharField(max_length=20, choices=CALCULATION_CHOICES, default="fixed")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_taxable = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class RESAAS:
        label_field = "name"
        search_fields = ["name", "code"]
        crud = True

    def __str__(self):
        return self.name


class Visit(BaseModel):
    SOURCE_CHOICES = [("manual", "Manual"), ("device", "Device")]
    STATUS_CHOICES = [("present", "Present"), ("late", "Late"), ("absent", "Absent")]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="visits")
    date = models.DateField()
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="manual")
    minutes = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="present")

    class RESAAS:
        label_field = "date"
        crud = True

    def __str__(self):
        return f"{self.member} {self.date}"


class Agreement(BaseModel):
    """A record with a field that needs its own permission: seeing an
    agreement (view_agreement) does not reveal its amount
    (view_agreement_amount / change_agreement_amount) - field-level
    authorization, saas/core/base/field_access.py. (Not "value": the
    serializers already output a record's value/label pair.)"""

    STATUS_CHOICES = [("draft", "Draft"), ("active", "Active")]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="agreements")
    number = models.CharField(max_length=50, null=True, blank=True)
    start_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    class Meta:
        ordering = ["-start_date"]
        unique_together = ("entity", "number")

    class RESAAS:
        label_field = "number"
        crud = True
        fields = {
            "amount": {
                "permissions": {
                    "view": "view_agreement_amount",
                    "change": "change_agreement_amount",
                },
            },
        }

    def __str__(self):
        return self.number or str(self.pk)
