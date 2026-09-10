"""Partilhado por EntityAPIView e EntityTypeAPIView's
themePut/layoutSettingsPut/typographyPut/animationSettingsPut - todos
seguem o mesmo padrão "Get devolve o objecto completo, Put recebe de
volta exactamente o mesmo shape e aplica campo-a-campo à mão" (sem
passar pelo serializer).

RepresentationMixin.to_representation() (engine/core/base/mixins/
serializer/representation.py) representa qualquer campo com
`choices=` como {"id","value","label"}, nunca a string simples que o
CharField subjacente espera. Sem desembrulhar aqui, um "Save" que nem
sequer tocou nesse campo já tenta gravar o dict inteiro na coluna -
numa coluna curta (ex.: Theme.state, varchar(8)) isso é um DataError
imediato; numa coluna mais larga seria uma corrupção silenciosa
(guardava a repr. do dict como string).
"""

# Mesma lista que BaseSerializer.DEFAULT_READ_ONLY_FIELDS - replicada
# aqui porque estes endpoints nunca passam pelo serializer para
# escrever.
SUB_OBJECT_PUT_SKIP_KEYS = ("id", "entity", "branch", "created_at", "updated_at", "deleted_at")


def apply_sub_object_put(instance, data, *, user):
    for key, value in data.items():
        if key in ("created_by", "updated_by"):
            instance.created_by = user
            instance.updated_by = user
            continue

        if key in SUB_OBJECT_PUT_SKIP_KEYS:
            continue

        if not hasattr(instance, key):
            continue

        if isinstance(value, dict) and "value" in value:
            value = value["value"]

        setattr(instance, key, value)
