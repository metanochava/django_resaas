# Pesquisa Dinâmica

A API recebe o termo através de:

``` text
?search=metano
```

## Campos configurados

Se o model possuir:

``` python
class RESAAS:
    search_fields = ["name", "surname"]
```

a pesquisa deve produzir condições equivalentes a:

``` python
Q(name__icontains="metano") |
Q(surname__icontains="metano")
```

## Relações

Quando suportado pelo validador de campos, uma configuração pode
utilizar caminhos como:

``` python
search_fields = [
    "codigo",
    "employee__person__full_name",
]
```

## Query vazia

É importante não transformar uma pesquisa inválida num `Q()` vazio
seguido de `qs.filter(Q())`, pois isso não restringe o queryset.

## Exemplo de utilização

``` text
/api/django_resaas/persons?search=m&page=1&page_size=10
```
