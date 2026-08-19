# Filtros, Ordenação e Paginação

## Filtros

O `DjangoFilterBackend` permite filtros por query parameters para campos
elegíveis.

Exemplo:

``` text
?state=Active
```

## Combinação

Pesquisa e filtros podem ser combinados:

``` text
?search=dias&state=Active&page=1&page_size=10
```

## Ordenação

Quando `ordering_fields = "__all__"` está ativo, os campos permitidos
podem ser utilizados pelo mecanismo de ordenação do DRF.

## Paginação

Parâmetros usuais:

-   `page`
-   `page_size`

A resposta paginada deve manter a estrutura definida pela configuração
global do projeto.
