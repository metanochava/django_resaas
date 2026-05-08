# 🚀 django_resaas

**django_resaas** é um framework modular para construção de aplicações SaaS multi-tenant em Django, com:

* 🔐 Controle de permissões (RBAC)
* 🏢 Multi-tenant (Entity / Branch)
* 🧩 Módulos ativáveis por cliente
* 💰 Billing por plano (SaaS ready)
* ♻️ Soft delete + restore
* 🔎 Busca dinâmica automática
* ⚡ BaseAPIView inteligente (DRF)

---

# 🧠 Arquitetura

```text
User
 ↓
Person
 ↓
Funcionario (RH)
 ↓
Entity (tenant)
 ↓
Branch
 ↓
Groups + Permissões
```

---

# 🧩 Conceitos principais

## 🏢 Entity (Tenant)

Representa o cliente (empresa)

## 🏬 Branch

Unidade da entity

## 👤 Person

Dados humanos (name, email, etc.)

## 🔐 User

Autenticação

## 👥 BranchUserGroup

Relaciona:

* User
* Branch
* Group (Django)

👉 Permite múltiplos groups por branch

---

# 🔐 Sistema de Permissões (RBAC)

Baseado em:

```text
User + Group + Permission (Django)
+ contexto (Entity + Branch)
```

Headers obrigatórios:

```http
ET → entity_type
E  → entity
S  → branch
G  → group
L  → language
```

---

# 🧱 BaseModel

Todos os models herdam:

```python
from django_resaas import BaseModel
```

Inclui:

* entity
* branch
* created_at / updated_at
* soft delete
* created_by / updated_by

---

# 🔁 Soft Delete

```python
obj.delete()        # soft delete
obj.restore()       # restore
obj.hard_delete()   # delete real
```

Managers disponíveis:

```python
Model.objects          # ativos
Model.deleted_objects  # apagados
Model.all_objects      # todos
```

---

# ⚡ BaseAPIView

CRUD automático com:

* multi-tenant automático
* permissões automáticas
* search dinâmica
* soft delete
* restore
* hard delete

## Uso:

```python
from django_resaas import BaseAPIView, register_view

@register_view(module="rh")
class FuncionarioView(BaseAPIView):
    queryset = Funcionario.objects.all()
    serializer_class = FuncionarioSerializer
```

---

# 🔍 Busca dinâmica

```http
GET /api/funcionarios/?search=joao
```

Busca automaticamente em:

* name
* email
* código
* relações (FK)

---

# 🧩 Sistema de Módulos

Permite ativar/desativar funcionalidades por cliente.

## Models:

* App
* EntityApp

## Exemplo:

| Entity  | Módulo | Estado |
| --------- | ------ | ------ |
| Empresa A | RH     | ✅      |
| Empresa A | CRM    | ❌      |

---

# 🔐 Proteção automática por módulo

```python
@register_view(module="rh")
class FuncionarioView(BaseAPIView):
    ...
```

👉 Se módulo não estiver ativo → acesso bloqueado

---

# 💰 Billing (SaaS)

## Models:

* Plano
* PlanoApp
* EntityPlano

## Fluxo:

```text
Plano → módulos → EntityPlano → ativa módulos automaticamente
```

---

# 🔄 Sync automático de módulos

Ao mudar plano:

```python
sync_apps_entity(entity)
```

---

# 📦 BaseSerializer

Proteção automática de arquivos:

```python
{
  "file": {
    "url": "...",
    "name": "...",
    "ext": "pdf",
    "size": 12345
  }
}
```

---

# 🌐 Middleware

## TenantContextMiddleware

Captura headers:

```python
request.entity_id
request.branch_id
request.group_id
```

---

## FrontEndMiddleware

Protege acesso por:

* chave frontend (FEK/FEP)
* permissões por URL
* permissões por método HTTP

---

# 🧪 Exemplo completo

## Model

```python
from django_resaas import BaseModel

class Funcionario(BaseModel):
    person = models.ForeignKey('django_resaas.Person', on_delete=models.CASCADE)
    cargo = models.CharField(max_length=100)
```

---

## Serializer

```python
from django_resaas import BaseSerializer

class FuncionarioSerializer(BaseSerializer):
    class Meta:
        model = Funcionario
        fields = "__all__"
```

---

## View

```python
from django_resaas import BaseAPIView, register_view

@register_view(module="rh")
class FuncionarioView(BaseAPIView):
    queryset = Funcionario.objects.all()
    serializer_class = FuncionarioSerializer
```

---

# ⚙️ Instalação

```bash
pip install django_resaas
```

ou local:

```bash
pip install -e .
```

---

# 🔧 Configuração

## INSTALLED_APPS

```python
INSTALLED_APPS = [
    "django_resaas",
    "rh",
]
```

---

## Middleware

```python
MIDDLEWARE = [
    "django_resaas.core.middleware.tenant.TenantContextMiddleware",
    "django_resaas.core.middleware.frontend.FrontEndMiddleware",
]
```

---

# 🚀 Roadmap

* [ ] Integração com Stripe
* [ ] Dashboard de billing
* [ ] Auto-router
* [ ] Auditoria de ações
* [ ] Logs multi-tenant
* [ ] Cache de permissões (Redis)

---

# 🧠 Filosofia

> "Construir SaaS não deve ser repetitivo."

django_resaas resolve:

* multi-tenant
* permissões
* módulos
* billing

👉 para você focar no negócio

---

# 🤝 Contribuição

PRs são bem-vindos 🚀

---

# 📄 Licença

MIT License

---

# 👨‍💻 Autor

**Metano Chavana**
