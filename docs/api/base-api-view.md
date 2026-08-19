# BaseAPIView

`BaseAPIView` é a base comum das APIs REST.

## Principais responsabilidades

-   CRUD através de `ModelViewSet`;
-   filtros;
-   ordenação;
-   pesquisa dinâmica;
-   permissões;
-   multi-tenancy;
-   auditoria;
-   soft delete;
-   restore;
-   hard delete;
-   select mode.

## Mapeamento de permissões

Exemplo:

``` python
permission_action_map = {
    "list": "list",
    "retrieve": "view",
    "create": "add",
    "update": "change",
    "partial_update": "change",
    "destroy": "delete",
    "restore": "restore",
    "hard_delete": "hard_delete",
}
```

Para um model `Paciente`, a criação pode exigir `add_paciente`, a
alteração `change_paciente` e a remoção `delete_paciente`.

## Queryset

O `get_queryset()` deve ser o ponto central para garantir isolamento
tenant antes da listagem e pesquisa.
