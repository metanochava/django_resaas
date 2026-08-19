# Git Flow e Releases

## Antes de iniciar

Verificar se existe uma release aberta:

``` bash
git branch -a | grep release
```

## Fluxo

``` text
develop
   |
   v
release/x.y.z
   |
   +--> main
   |
   +--> develop
   |
   +--> tag
```

## Regra importante

O bump da versão não deve acontecer antes de verificar se já existe uma
release pendente. Caso contrário, podem surgir commits de versão sem a
respetiva branch de release.

## Diagnóstico

``` bash
git status
git branch -a
git tag --sort=-v:refname | head
grep version pyproject.toml
```
