# Arquitetura do Backend

## Visão geral

O backend segue uma arquitetura em camadas:

``` text
Cliente / Frontend
       |
       v
REST API / Router
       |
       v
BaseAPIView
       |
       +---- Permissões
       +---- Multi-tenancy
       +---- Pesquisa/Filtros
       |
       v
Serializer
       |
       v
Model
       |
       v
Base de Dados
```

## Responsabilidades

### View

Recebe a requisição, determina a ação, restringe o queryset e coordena
serializer e resposta.

### Serializer

Valida os dados de entrada e transforma instâncias Django em dados
apropriados para a API.

### Model

Representa os dados persistentes e as relações do domínio.

### Componentes base

O framework concentra comportamentos repetidos em classes e utilitários
comuns para evitar que cada aplicação volte a implementar CRUD, tenant,
permissões e representação.
