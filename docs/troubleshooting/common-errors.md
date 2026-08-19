# Troubleshooting Backend

## Pesquisa devolve todos os registos

Verificar:

1.  se `search` chega em `request.query_params`;
2.  se `RESAAS.search_fields` está a ser lido;
3.  se o `Q` contém condições;
4.  se outro backend não está a substituir o comportamento;
5.  o SQL final através de `print(qs.query)`.

## Release já existente

Mensagem:

``` text
Fatal: There is an existing release branch
```

Resolver a release existente antes de iniciar outra.

## Permissão negada

Confirmar: - módulo ativo; - entidade correta; - codename; - associação
do utilizador/grupo; - resultado de `isPermited()`.
