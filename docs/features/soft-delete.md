# Soft Delete, Restore e Hard Delete

## Soft delete

Em vez de eliminar imediatamente um registo, o sistema pode marcar
`deleted_at`.

## Listagem

O parâmetro `objects` pode selecionar diferentes managers:

``` text
?objects=all
?objects=deleted
```

Depois da troca de manager, os filtros de entidade e sucursal devem ser
reaplicados.

## Restore

Uma action `restore` recupera uma instância apagada, desde que o
utilizador tenha a permissão correspondente.

## Hard delete

`hard_delete` remove definitivamente a instância. Deve ser protegido por
uma permissão específica.
