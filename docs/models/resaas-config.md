# Configuração RESAAS nos Models

Os models podem declarar metadados específicos do framework através de
`class RESAAS`.

Exemplo:

``` python
class RESAAS:
    label_field = "name surname"
    search_fields = ["name", "surname"]
    crud = True
```

## `label_field`

Define os campos utilizados para construir uma representação legível da
instância.

## `search_fields`

Define explicitamente os campos onde a pesquisa textual deve atuar.

## `crud`

Indica que o recurso participa no mecanismo CRUD do framework, quando
essa opção é utilizada pela aplicação.

## Recomendação

Quando um model precisa de uma pesquisa controlada, declare
`search_fields` explicitamente em vez de depender de um fallback
genérico.
