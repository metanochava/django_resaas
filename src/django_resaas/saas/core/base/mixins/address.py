from django.contrib.contenttypes.fields import GenericRelation
from django.db import models, transaction

from django_resaas.saas.models.address import Address


class AddressMixin(models.Model):

    """
    Adiciona suporte genérico a endereços.

    Qualquer model que herdar deste mixin terá:

        instance.addresses.all()

        instance.address

        instance.get_address()

        instance.set_address()

        instance.delete_address()

        instance.clear_addresses()
    """

    addresses = GenericRelation(
        Address,
        content_type_field="content_type",
        object_id_field="object_id",
    )

    class Meta:
        abstract = True

    # =========================================================
    # GET
    # =========================================================

    def get_address(
        self,
        address_type=Address.AddressType.MAIN,
    ):

        return self.addresses.filter(
            address_type=address_type,
        ).first()

    # =========================================================
    # MAIN ADDRESS
    # =========================================================

    @property
    def address(self):

        return self.get_address(
            Address.AddressType.MAIN
        )

    # =========================================================
    # SET / CREATE / UPDATE
    # =========================================================

    @transaction.atomic
    def set_address(
        self,
        address_type=Address.AddressType.MAIN,
        **data,
    ):

        if not self.pk:
            raise ValueError(
                "O objecto deve ser gravado antes de adicionar um endereço."
            )

        # Não permitimos alterar estes campos através de data.
        protected_fields = {
            "id",
            "content_type",
            "object_id",
            "content_object",
            "address_type",
            "created_at",
            "updated_at",
            "deleted_at",
        }

        for field in protected_fields:
            data.pop(field, None)

        address = self.get_address(
            address_type=address_type,
        )

        # =====================================================
        # UPDATE
        # =====================================================

        if address:

            valid_fields = {
                field.name
                for field in Address._meta.fields
            }

            changed_fields = []

            for field, value in data.items():

                if field not in valid_fields:
                    continue

                setattr(
                    address,
                    field,
                    value,
                )

                changed_fields.append(field)

            if changed_fields:

                address.save(
                    update_fields=list(
                        set(
                            changed_fields
                            + ["updated_at"]
                        )
                    )
                )

            return address

        # =====================================================
        # CREATE
        # =====================================================

        return self.addresses.create(
            address_type=address_type,
            **data,
        )

    # =========================================================
    # DELETE ONE
    # =========================================================

    @transaction.atomic
    def delete_address(
        self,
        address_type=Address.AddressType.MAIN,
    ):

        address = self.get_address(
            address_type=address_type,
        )

        if not address:
            return False

        address.delete()

        return True

    # =========================================================
    # DELETE ALL
    # =========================================================

    @transaction.atomic
    def clear_addresses(self):

        deleted, _ = self.addresses.all().delete()

        return deleted

    # =========================================================
    # CHECK
    # =========================================================

    def has_address(
        self,
        address_type=Address.AddressType.MAIN,
    ):

        return self.addresses.filter(
            address_type=address_type,
        ).exists()

    # =========================================================
    # COUNT
    # =========================================================

    @property
    def address_count(self):

        return self.addresses.count()