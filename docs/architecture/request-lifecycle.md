# Ciclo de uma Requisição

``` text
HTTP Request
   |
   v
initial()
   |
   +-- verifica módulo
   +-- determina permissão
   +-- verifica autorização
   |
   v
get_queryset()
   |
   +-- entity
   +-- branch
   +-- objects=all/deleted
   +-- pesquisa
   |
   v
DjangoFilterBackend / Ordering
   |
   v
Serializer
   |
   v
Model / Database
   |
   v
HTTP Response
```

## Create

Em criação, `perform_create()` pode preencher automaticamente
`created_by`, `updated_by`, `entity_id` e `branch_id`.

## Update

Em atualização, `perform_update()` deve atualizar o utilizador
responsável pela alteração.

## Delete

Quando o model suporta soft delete, a remoção lógica deve preservar o
registo para posterior recuperação.
