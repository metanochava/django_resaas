# Permissões

O backend é a autoridade final para autorização.

## Processo

1.  Identificar a ação da view.
2.  Converter a ação num prefixo de permissão.
3.  Obter o nome técnico do model.
4.  Construir o codename.
5.  Verificar com `isPermited()`.

Exemplo:

``` text
create + paciente -> add_paciente
update + paciente -> change_paciente
destroy + paciente -> delete_paciente
```

## Cache

Uma cache por request pode evitar verificações repetidas do mesmo
codename durante a mesma requisição.

## Módulo

Além da permissão, a aplicação pode verificar se o módulo correspondente
está ativo para a entidade.
