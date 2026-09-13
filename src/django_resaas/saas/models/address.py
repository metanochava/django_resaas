from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from django_resaas.saas.core.base.models import TimeModel


class Address(TimeModel):

    # =========================================================
    # TYPES
    # =========================================================

    class AddressType(models.TextChoices):
        MAIN = "main", "Principal"
        HOME = "home", "Casa"
        OFFICE = "office", "Escritório"
        BILLING = "billing", "Facturação"
        SHIPPING = "shipping", "Entrega"
        OTHER = "other", "Outro"

    # =========================================================
    # GENERIC RELATION
    # Pode pertencer a qualquer model Django
    # =========================================================

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="resaas_addresses",
        null=False,
        blank=False,
    )

    object_id = models.CharField(
        max_length=255,
        db_index=True,
    )

    content_object = GenericForeignKey(
        "content_type",
        "object_id",
    )

    # =========================================================
    # ADDRESS TYPE
    # =========================================================

    address_type = models.CharField(
        max_length=30,
        choices=AddressType.choices,
        default=AddressType.MAIN,
        db_index=True,
    )

    # =========================================================
    # GOOGLE MAPS
    # =========================================================

    place_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="Google Maps Place ID",
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(-90),
            MaxValueValidator(90),
        ],
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(-180),
            MaxValueValidator(180),
        ],
    )

    formatted_address = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Endereço formatado pelo Google Maps",
    )

    # =========================================================
    # STREET
    # =========================================================

    street_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Número da porta, casa ou edifício",
    )

    route = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Rua, avenida, estrada, etc.",
    )

    premise = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Edifício, condomínio ou instalação",
    )

    subpremise = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Apartamento, bloco, unidade, sala, etc.",
    )

    # =========================================================
    # LOCATION
    # =========================================================

    neighborhood = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="Bairro ou zona",
    )

    sublocality = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="Sub-localidade",
    )

    locality = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="Cidade ou localidade",
    )

    administrative_area_level_1 = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="Província, estado ou região",
    )

    administrative_area_level_2 = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="Distrito, município, condado, etc.",
    )

    administrative_area_level_3 = models.CharField(
        max_length=150,
        null=True,
        blank=True,
    )

    postal_code = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        db_index=True,
    )

    country = models.CharField(
        max_length=150,
        default="Mozambique",
    )

    country_code = models.CharField(
        max_length=2,
        default="MZ",
        db_index=True,
        help_text="ISO 3166-1 alpha-2. Ex.: MZ, IN, ZA, PT",
    )

    complement = models.TextField(
        null=True,
        blank=True,
        help_text="Informação adicional para localização",
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:

        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"

        permissions = ()

        constraints = [

            # Um objecto só pode ter um endereço de cada tipo.
            models.UniqueConstraint(
                fields=[
                    "content_type",
                    "object_id",
                    "address_type",
                ],
                name="unique_address_type_per_object",
            ),

        ]

        indexes = [

            models.Index(
                fields=[
                    "content_type",
                    "object_id",
                ],
            ),

            models.Index(
                fields=[
                    "content_type",
                    "object_id",
                    "address_type",
                ],
            ),

            models.Index(
                fields=[
                    "country_code",
                    "locality",
                ],
            ),

            models.Index(
                fields=[
                    "latitude",
                    "longitude",
                ],
            ),

        ]

    # =========================================================
    # RESAAS
    # =========================================================

    class RESAAS:

        label_field = "formatted_address"

        crud = True

        routes = {
            "list": "add_address",
            "view": "view_address",
            "add": "add_address",
            "change": "change_address",
        }

    # =========================================================
    # ALIASES
    # =========================================================

    @property
    def rua(self):
        return self.route

    @property
    def numero(self):
        return self.street_number

    @property
    def bairro(self):
        return self.neighborhood or self.sublocality

    @property
    def cidade(self):
        return self.locality

    @property
    def provincia(self):
        return self.administrative_area_level_1

    @property
    def pais(self):
        return self.country

    @property
    def codigo_postal(self):
        return self.postal_code

    @property
    def complemento(self):
        return self.complement

    # =========================================================
    # FULL ADDRESS
    # =========================================================

    @property
    def full_address(self):

        if self.formatted_address:
            return self.formatted_address

        return ", ".join(
            filter(
                None,
                [
                    self.street_number,
                    self.route,
                    self.neighborhood,
                    self.locality,
                    self.administrative_area_level_2,
                    self.administrative_area_level_1,
                    self.postal_code,
                    self.country,
                ],
            )
        )

    # =========================================================
    # COORDINATES
    # =========================================================

    @property
    def coordinates(self):

        if self.latitude is None or self.longitude is None:
            return None

        return {
            "lat": float(self.latitude),
            "lng": float(self.longitude),
        }

    # =========================================================
    # OWNER
    # =========================================================

    @property
    def owner(self):
        return self.content_object

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):

        return (
            self.formatted_address
            or self.full_address
            or str(self.id)
        )