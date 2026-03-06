apt install libpango-1.0-0 libpangoft2-1.0-0 libffi-dev libxml2 libxslt1.1
pip install weasyprint

## ViewSet Rule

All concrete ViewSets MUST define a base queryset.

The BaseAPIView only applies multi-tenant filters and permissions,
it does not define the base queryset.

Example:
```bash 
    class PessoaViewSet(BaseAPIView):
        queryset = Pessoa.objects.select_related('user', 'endereco')

```

# Translate (Project Rule)

All text returned by the API MUST be translated using the Translate class.

Frontend applications must not translate text.

Example:

```bash
python
from django_saas.classes.Translate import Translate

return Response({
    'alert_error': Translate.tdc(request, 'Permission denied')
}, status=403)
```

# CoreFileMiddleware

This middleware protects access to media files.

Only requests with a valid token are allowed.

## Behavior
- Intercepts requests to MEDIA_URL
- Validates token from querystring
- Returns translated error messages

## Example
/media/document.pdf?token=XYZ

## Unauthorized response
```json
{
  "alert_error": "Nao autorizado"
}
```
# CoreMiddleware

Este middleware controla o acesso às rotas da API.

O acesso é permitido apenas para:
- Frontends autorizados (FEK + FEP)
- Endereços IP autorizados

## Comportamento
- Ignora URLs públicas definidas em `settings.AUTH_URL`
- Valida headers FEK e FEP
- Caso inválido, retorna erro traduzido via `Translate`

## Headers esperados
FEK: Frontend Key  
FEP: Frontend Password  

## Resposta não autorizada
```json
{
  "code": 10001,
  "alert_error": "Não autorizado"
}
```

# File Token Configuration

A biblioteca suporta dois tipos de token para acesso a ficheiros:

- 🔐 Token permanente (não expira)
- ⏱️ Token temporário (com TTL)

## Settings
```python
DJANGO_REST_AUTH = {
    'FILE_TOKEN': {
        'ENABLE_TEMPORARY': True,
        'TEMP_TTL': 300,
        'ENABLE_PERMANENT': True,
    },
    'REQUIRE_FE_CREDENTIALS': True,
    'TENANT_HEADERS': {
        'ENTIDADE': 'E',
        'SUCURSAL': 'S',
        'GRUPO': 'G',
        'TIPO_ENTIDADE': 'ET',
        'LANG': 'L',
    }
}
```

## Email Templates

A biblioteca permite substituir os templates de email via settings.

### Exemplo:

```python
DJANGO_REST_AUTH = {
    'EMAIL_TEMPLATES': {
        'REGISTER_CONFIRM': 'emails/confirmacao.html',
        'PASSWORD_RESET': 'emails/reset.html',
        'GENERIC_RESET': 'emails/generico.html',
    }
}

E no settings.py:

TEMPLATES[0]['DIRS'] += [BASE_DIR / 'templates']

No projeto final:

project/
└── templates/
    └── emails/
        ├── meu_confirmacao.html
        ├── meu_reset.html
        └── meu_generico.html
```


```bash 

📘 PADRÃO DE PERISSÕES – FRAMEWORK MULTI-TENANT

Este projeto implementa um sistema de permissões centralizado, multi-tenant e orientado a APIs, baseado em:

Django Permissions (auth_permission)

Groups (auth_group)

Contexto dinâmico via headers

Validação automática no BaseAPIView

Uma única query por request (alta performance)

🧱 Conceitos Fundamentais
🔹 Tipo de Entidade

Classificação da organização (ex: Clínica, Escola, Empresa).

🔹 Entidade

Organização principal (ex: Clínica ABC).

🔹 Sucursal

Unidade da entidade (ex: Filial Luanda).

🔹 Grupo

Papel do utilizador numa sucursal (ex: Admin, RH, Médico).

🔹 Utilizador

Pode pertencer a:

múltiplas Entidades

múltiplas Sucursais

múltiplos Grupos

🧭 Contexto Obrigatório (Headers)

Todo request autenticado DEVE enviar os headers abaixo:

Header	Descrição
ET	ID do Tipo de Entidade
E	ID da Entidade
S	ID da Sucursal
G	ID do Grupo
L	Idioma 

📌 Sem estes headers, o acesso é negado.

🔐 Modelo de Permissões (Padrão)

O sistema segue o padrão Django com extensão para list.

CRUD padrão
Action (DRF)	Permissão
list	list_<model>
retrieve	view_<model>
create	add_<model>
update	change_<model>
partial_update	change_<model>
destroy	delete_<model>

📌 <model> é o nome do model em minúsculas.

Exemplo (Colaborador)
list_colaborador
view_colaborador
add_colaborador
change_colaborador
delete_colaborador

⚙️ Permissões Automáticas

Após cada migrate, o sistema cria automaticamente:

list_<model>

Apenas para os apps definidos em:

settings.MY_APPS


✔️ Não há risco de duplicação
✔️ Usa get_or_create()
✔️ (codename, content_type) é único no Django

✨ Permissões Customizadas no Model

Models podem definir permissões adicionais:

class Colaborador(models.Model):
    class Meta:
        permissions = (
            ('icon', 'Menu Icon'),
            ('list_contauser', 'Can list Conta User'),
        )


Estas permissões:

são criadas pelo Django

podem ser atribuídas a grupos

podem ser usadas nas views

🧠 Verificação de Permissões

Toda a verificação acontece via:

isPermited(request=request, role=[codename])


Internamente, o sistema valida numa única query:

user ∈ grupo

grupo ∈ sucursal

sucursal ∈ entidade

entidade ∈ tipo_entidade

grupo possui a permissão solicitada

Se qualquer condição falhar → acesso negado.

🧩 BaseAPIView (Automático)

Todas as APIs devem herdar de:

ds.views.BaseAPIView

O que o BaseAPIView faz

✔️ valida permissões automaticamente

✔️ injeta contexto (entidade_id, sucursal_id, etc.)

✔️ filtra queryset por tenant

✔️ implementa soft delete

✔️ não usa decorators

🔁 Mapeamento de Permissões por Action
🔹 Mapa padrão (interno)
permission_action_map = {
    'list': 'list',
    'retrieve': 'view',
    'create': 'add',
    'update': 'change',
    'partial_update': 'change',
    'destroy': 'delete',
}

✍️ method_permission (Override por ViewSet)

Cada ViewSet pode estender ou sobrescrever permissões usando:

method_permission = {}

Prioridade
method_permission  >  permission_action_map

📌 Exemplos Práticos
✔️ ViewSet simples (CRUD padrão)
class ColaboradorViewSet(BaseAPIView):
    queryset = Colaborador.objects.all()
    serializer_class = ColaboradorSerializer


Permissões usadas automaticamente:

list_colaborador
add_colaborador
change_colaborador
delete_colaborador

✔️ Action custom (bulk_create)
class ColaboradorViewSet(BaseAPIView):
    queryset = Colaborador.objects.all()
    serializer_class = ColaboradorSerializer

    method_permission = {
        'bulk_create': 'add',
    }

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        ...


Permissão exigida:

add_colaborador

✔️ Sobrescrever permissão de action padrão
class ColaboradorViewSet(BaseAPIView):
    method_permission = {
        'list': 'view',
    }


Agora o list exige:

view_colaborador

🚫 O que NÃO fazer

❌ Criar views sem herdar de BaseAPIView
❌ Ignorar headers de contexto
❌ Usar decorators de permissão em views
❌ Implementar lógica de tenant fora do core

⚡ Performance

✔️ 1 query por request para permissões

✔️ Usa exists() + JOIN

✔️ Sem carregar objetos em memória

✔️ Escala bem com muitos utilizadores

🏁 Conclusão

Este padrão fornece:

🔒 Segurança forte

⚡ Alta performance

🔁 Reutilização total

🧱 Arquitetura de framework

📦 Preparado para múltiplos domínios (RH, Clínica, Escola, etc.)

Se quiseres, posso:

gerar isto em Markdown final

criar um diagrama de fluxo

documentar BaseRHViewSet

criar exemplos reais do RH

É só dizer 🚀



# MetanoStack Architecture Rules

## Core Principles

1. Every model MUST inherit from BaseModel
2. Every serializer MUST inherit from BaseSerializer
3. Every viewset MUST inherit from BaseAPIView
4. No relative imports allowed
5. One class per file
6. User model must be django_saas User
7. Multi-tenant enforced via middleware
8. No business logic inside ViewSets
9. Serializers define API contract (OpenAPI source of truth)
10. RH must support skills (Especialidades)

## Forbidden Patterns

- class X(models.Model)
- class X(ModelSerializer)
- class X(ModelViewSet)
- from . import something
- Big models.py files

## Structure Standard

module/
 ├─ models/
 ├─ serializers/
 ├─ views/
 ├─ services/
 └─ urls.py

## Enterprise Compliance

- Audit fields required
- UUID primary keys
- Soft delete via estado
- Multi-tenant aware


    INSTALLED_APPS = [
        'corsheaders',
        ...
    ]

    MIDDLEWARE = [
        'corsheaders.middleware.CorsMiddleware',
        'django.middleware.common.CommonMiddleware',
        ...
    ]

    CORS_ALLOWED_ORIGINS = [
        "http://84.247.162.222:9000",
    ]

    CORS_ALLOW_CREDENTIALS = True

    from corsheaders.defaults import default_headers
    CORS_ALLOW_HEADERS = list(default_headers) + [
        "fek",
        "fep",
    ]



```










