# Multi-tenancy

O RESAAS trabalha com contexto de tenant. Uma requisição pode
transportar:

-   `entity_type_id`
-   `entity_id`
-   `branch_id`
-   `group_id`
-   `lang_id`

## Regra principal

Um model que possui `entity_id` deve ser filtrado pela entidade ativa.
Um model que possui `branch_id` deve também ser filtrado pela sucursal
ativa.

Exemplo conceptual:

``` python
if hasattr(Model, "entity_id"):
    qs = qs.filter(entity_id=self.request.entity_id)

if hasattr(Model, "branch_id"):
    qs = qs.filter(branch_id=self.request.branch_id)
```

Quando o manager é trocado, por exemplo para `all_objects` ou
`deleted_objects`, os filtros tenant devem ser reaplicados.

## Objetivo

A finalidade é impedir que uma requisição de uma entidade consulte
acidentalmente dados pertencentes a outra entidade.
